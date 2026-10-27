import csv
import json
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from unanet_pipeline.schema import TABLES, OUTPUT
from unanet_pipeline.core import ValidationError
from unanet_pipeline.adapters import CSVSource
from unanet_pipeline.__main__ import run

ROOT = Path(__file__).resolve().parents[1]

class CostPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        shutil.copytree(ROOT / 'examples' / 'source', self.source)
        self.output = self.root / 'data'

    def execute(self, **kwargs):
        directory, _ = run(CSVSource(self.source), self.output, **kwargs)
        manifest = json.loads((directory / 'processed' / 'manifest.json').read_text(), parse_float=Decimal)
        rows = []
        for entry in manifest['project_cost_details']['files']:
            rows.extend(json.loads((directory / entry['path']).read_text(), parse_float=Decimal))
        return manifest, rows

    def edit(self, name, action):
        path = self.source / (name + '.csv')
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
        rows = action(rows)
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=TABLES[name])
            writer.writeheader(); writer.writerows(rows)

    def test_four_branches_schema_and_original_amount_rules(self):
        manifest, rows = self.execute(rows_per_file=2)
        self.assertEqual(4, len(rows))
        self.assertEqual(2, len(manifest['project_cost_details']['files']))
        for row in rows:
            self.assertEqual(OUTPUT, list(row))
        by_source = {r['Cost Source']: r for r in rows}
        self.assertEqual(Decimal('200'), by_source['Labor']['Cost Amount'])
        # eff_quantity is deliberately 9; quantity is 8. Preserve quantity * rate.
        self.assertEqual(9, by_source['Labor']['eff_quantity'])
        self.assertEqual(50, by_source['Expense']['Cost Amount'])
        self.assertEqual('Y', by_source['Expense']['billable'])
        self.assertEqual('Travel', by_source['Expense']['code'])
        self.assertEqual(125, by_source['Financial Document Expense']['Cost Amount'])
        self.assertEqual(80, by_source['Financial Document Labor']['Cost Amount'])
        self.assertIsNone(by_source['Financial Document Labor']['billable'])
        self.assertIsNone(by_source['Labor']['cost_struct_labor_key'])
        self.assertEqual('2026-07-15', by_source['Labor']['Cost Date'])
        self.assertEqual(4, manifest['project_cost_details']['rows'])

    def test_unmatched_join_keeps_original_row(self):
        self.edit('cost_struct_labor', lambda rows: [r for r in rows if r['cost_struct_labor_key'] != '101'])
        manifest, rows = self.execute()
        labor = next(r for r in rows if r['Cost Source'] == 'Labor')
        self.assertIsNone(labor['cost_element_key'])
        self.assertEqual(200, labor['Cost Amount'])
        self.assertEqual(1, manifest['project_cost_details']['by_source']['Labor']['null_cost_elements'])

    def test_duplicate_lookup_matches_expand_like_power_query(self):
        self.edit('cost_struct_labor', lambda rows: rows + [rows[0]])
        manifest, rows = self.execute()
        self.assertEqual(5, len(rows))
        self.assertEqual(400, manifest['project_cost_details']['by_source']['Labor']['cost_total'])

    def test_decimal_precision_and_negative_values(self):
        def change(rows):
            rows[0]['quantity'] = '0.123456789012345678'
            rows[0]['eff_cost_rate'] = '-0.123456789012345678'
            return rows
        self.edit('person_time_data', change)
        _, rows = self.execute()
        labor = next(r for r in rows if r['Cost Source'] == 'Labor')
        self.assertEqual(Decimal('-0.015241578753238836527968299765279684'), labor['Cost Amount'])

    def test_null_amount_stays_null(self):
        self.edit('person_time_data', lambda rows: [dict(rows[0], quantity='')])
        manifest, rows = self.execute()
        self.assertIsNone(next(r for r in rows if r['Cost Source']=='Labor')['Cost Amount'])
        self.assertEqual(1, manifest['project_cost_details']['by_source']['Labor']['null_costs'])

    def test_null_safe_lookup_join(self):
        self.edit('person_time_data', lambda rows: [dict(rows[0], cost_struct_labor_key='')])
        self.edit('cost_struct_labor', lambda rows: [dict(rows[0], cost_struct_labor_key='')] + rows[1:])
        _, rows = self.execute()
        self.assertEqual(1, next(r for r in rows if r['Cost Source']=='Labor')['cost_element_key'])

    def test_failed_reconciliation_preserves_latest(self):
        self.execute()
        previous = (self.output / 'latest.json').read_bytes()
        expected = self.root / 'incorrect.json'
        expected.write_text('{"rows":999,"cost_totals_by_source":{}}')
        with self.assertRaises(ValidationError):
            self.execute(expectation=expected)
        self.assertEqual(previous, (self.output / 'latest.json').read_bytes())

    def test_missing_column_fails_instead_of_silently_dropping_costs(self):
        path = self.source / 'person_time_data.csv'
        path.write_text('project_key,quantity\n1,8\n')
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse((self.output / 'latest.json').exists())

    def test_explicit_closed_period_filter(self):
        self.edit('person_time_data', lambda rows: [dict(rows[0], work_date='2026-08-01')])
        manifest, rows = self.execute(closed_through='2026-07-31')
        self.assertEqual(3, len(rows))
        self.assertEqual(1, manifest['project_cost_details']['excluded_after_cutoff'])

    def test_control_totals_match(self):
        manifest, _ = self.execute(expectation=ROOT / 'examples' / 'expected_totals.json')
        self.assertEqual(4, manifest['project_cost_details']['rows'])

    def test_bad_key_or_nonfinite_amount_fails(self):
        self.edit('person_time_data', lambda rows: [dict(rows[0], project_key='1.5')])
        with self.assertRaises(ValidationError):
            self.execute()
        self.edit('person_time_data', lambda rows: [dict(rows[0], project_key='1', eff_cost_rate='NaN')])
        with self.assertRaises(ValidationError):
            self.execute()

if __name__ == '__main__':
    unittest.main()
