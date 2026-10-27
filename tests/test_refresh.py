import contextlib,io,json,sqlite3,tempfile,unittest,sys
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from unanet_pipeline.refresh import load_config,run_refresh,planned_rows,typed,check_controls
from unanet_pipeline.adapters import CSVSource
from unanet_pipeline.core import ValidationError
ROOT=Path(__file__).resolve().parents[1]
class RefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.cfg=load_config(ROOT/'config/refresh.json')
        class CountingSource(CSVSource):
            def __init__(self):super().__init__(ROOT/'examples/full_source');self.calls=[]
            def rows(self,table,columns):self.calls.append(table);yield from super().rows(table,columns)
        cls.source=CountingSource()
        with contextlib.redirect_stdout(io.StringIO()):cls.run_dir,cls.id=run_refresh(cls.source,cls.cfg,cls.tmp.name,chunk_size=2)
        cls.manifest=json.loads((cls.run_dir/'processed/manifest.json').read_text(),parse_float=Decimal)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def rows(self,name):
        return [r for f in self.manifest['tables'][name]['files'] for r in json.loads((self.run_dir/f['path']).read_text(),parse_float=Decimal)]
    def test_scope_and_one_read_per_source(self):
        self.assertEqual(34,len(self.source.calls));self.assertEqual(34,len(set(self.source.calls)));self.assertEqual(26,len(self.manifest['tables']))
        self.assertFalse({'password','ssn','verification_code'} & set(self.cfg['sources']['person']['columns']))
    def test_cost_golden_totals_and_financial_subset(self):
        expected=json.loads((ROOT/'examples/expected_totals.json').read_text())
        got=self.manifest['tables']['Project Cost Details']
        self.assertEqual(expected['rows'],got['rows']);self.assertEqual({k:Decimal(v) for k,v in expected['cost_totals_by_source'].items()},got['cost_totals_by_source'])
        self.assertEqual(2,len(self.rows('Financial Document Cost Detail')))
        self.assertEqual(2,len(got['files']))
    def test_renames_and_date_conversion(self):
        self.assertEqual('Synthetic Account',self.rows('account_Table')[0]['Account Title'])
        self.assertEqual('Synthetic Type',self.rows('project_Table')[0]['Type'])
        self.assertEqual('2026-09-01',self.rows('Fiscal Period Close')[0]['closed_timestamp'])
    def test_planned_weekend_excluded_inclusive(self):
        rows=self.rows('planned_time_daily_Table')
        self.assertEqual(['2026-09-04','2026-09-07'],[r['Plan Date'] for r in rows]);self.assertEqual([8,8],[r['Daily Planned Hours'] for r in rows])
    def test_rules_join(self):
        self.assertEqual(Decimal('0.25'),self.rows('Cost Pool Rules')[0]['actual_rate'])
        self.assertEqual('Synthetic',self.rows('Cost Report Rules')[0]['cost_report'])
    def test_control_mismatch_rejected(self):
        controls=json.loads((self.run_dir/'controls.json').read_text());controls['Project Cost Details']['rows']=999
        p=self.run_dir/'bad-controls.json';p.write_text(json.dumps(controls))
        with self.assertRaises(ValidationError):check_controls(self.manifest['tables'],p)
    def test_integer_keys_and_bad_types(self):
        self.assertEqual(1,typed('1.0','int64'))
        with self.assertRaises(ValidationError):typed('1.5','int64')
        with self.assertRaises(ValidationError):typed('NaN','double')
    def test_planned_invalid_ranges_and_null_hours(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE planned_time(planned_time_key,plan_set_key,person_key,project_key,task_key,labor_category_key,begin_date,end_date,planned_hours)')
            for start,end,h in [('2026-09-05','2026-09-06','5'),('2026-09-07','2026-09-04','5'),(None,'2026-09-07','5'),('2024-02-29','2024-03-01',None)]:
                db.execute('INSERT INTO planned_time VALUES(1,1,1,1,1,1,?,?,?)',(start,end,h))
            rows=list(planned_rows(db,self.cfg['outputs']['planned_time_daily_Table']))
            self.assertEqual(2,len(rows));self.assertTrue(all(r['Daily Planned Hours'] is None for r in rows))
    def test_empty_optional_output_keeps_schema(self):
        from unanet_pipeline.refresh import write_output
        folder=self.run_dir/'empty';folder.mkdir(exist_ok=True)
        result=write_output(iter([]),'empty',{'columns':{'key':'int64'},'min_rows':0},folder,2)
        self.assertEqual(0,result['rows']);self.assertEqual({'key':'int64'},result['columns']);self.assertEqual('[]\n',(folder/'empty_00001.json').read_text())
    def test_failed_full_refresh_preserves_local_pointer(self):
        from unittest.mock import patch
        from unanet_pipeline.refresh import main
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder);(target/'latest.json').write_text('previous completed run')
            argv=['run_refresh.py','--config',str(ROOT/'config/refresh.json'),'--csv-dir',str(target/'missing'),'--output-dir',str(target)]
            with patch.object(sys,'argv',argv),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(1,main())
            self.assertEqual('previous completed run',(target/'latest.json').read_text())
