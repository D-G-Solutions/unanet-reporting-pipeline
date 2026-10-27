"""Complete Unanet refresh based on the October 8 semantic model.

Each source is read once, joined on local scratch SQLite, and published as an
immutable run. SQLite is local working storage, not an Azure SQL service.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from .adapters import CSVSource, ODBCSource, publish_to_azure
from .core import ValidationError, decimal_value, encode_json, quoted, project_cost_rows, normalize


def typed(value, kind):
    if value is None:
        return None
    if kind == 'string':
        return str(value)
    if value == '':
        return None
    if kind in ('double', 'decimal'):
        return decimal_value(value)
    if kind == 'int64':
        number = decimal_value(value)
        if number != number.to_integral_value() or not -(2**63) <= number < 2**63:
            raise ValidationError('Expected signed 64-bit integer')
        return int(number)
    if kind == 'boolean':
        if value in (True, 1, 'true', 'True', '1'):
            return True
        if value in (False, 0, 'false', 'False', '0'):
            return False
        raise ValidationError('Expected boolean')
    if kind in ('date', 'dateTime'):
        try:
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            return parsed.date().isoformat() if kind == 'date' else parsed.isoformat()
        except ValueError:
            raise ValidationError('Expected ISO date or timestamp') from None
    raise ValidationError('Unsupported configured data type')


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    if cfg.get('version') != 2 or not cfg.get('sources') or not cfg.get('outputs'):
        raise ValidationError('Invalid refresh configuration')
    for name, spec in cfg['sources'].items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) or not spec['columns']:
            raise ValidationError('Invalid source table configuration')
        for c in spec['columns']:
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', c):
                raise ValidationError('Invalid source column configuration')
    return cfg


def load(db, source, cfg, run_dir):
    (run_dir / 'raw').mkdir()
    stats = {}
    for table, spec in cfg['sources'].items():
        started = time.monotonic()
        columns = spec['columns']
        db.execute(f'CREATE TABLE {quoted(table)} ({",".join(quoted(c)+" TEXT" for c in columns)})')
        insert = f'INSERT INTO {quoted(table)} VALUES ({",".join("?" for _ in columns)})'
        count, batch = 0, []
        with (run_dir / 'raw' / (table+'.jsonl')).open('w', encoding='utf-8') as raw:
            for row in source.rows(table, list(columns)):
                if set(columns) - row.keys():
                    raise ValidationError(table+': missing source columns')
                original = {c:v.isoformat() if isinstance(v, (date, datetime)) else v for c,v in row.items() if c in columns}
                raw.write(encode_json(original)+'\n')
                values = []
                for c,kind in columns.items():
                    try:
                        values.append(typed(row[c], 'int64' if c.endswith('_key') else kind))
                    except ValidationError as error:
                        raise ValidationError(f'{table}.{c}, row {count+1}: {error}') from None
                batch.append([None if v is None else 'true' if v is True else 'false' if v is False else str(v) for v in values])
                count += 1
                if len(batch) >= 2000:
                    db.executemany(insert, batch); batch.clear()
            if batch:
                db.executemany(insert, batch)
        for c in columns:
            if c.endswith('_key'):
                db.execute(f'CREATE INDEX {quoted(table+"_"+c)} ON {quoted(table)}({quoted(c)})')
        db.commit()
        stats[table] = {'rows':count,'seconds':round(time.monotonic()-started,3),'columns':columns}
        print(f'Extracted {table}: {count} rows', flush=True)
    return stats


def sql_rows(db, columns, mapping, joins):
    selection = ','.join(mapping[c]+' AS '+quoted(c) for c in columns)
    for values in db.execute('SELECT '+selection+' FROM '+joins):
        yield {c:typed(v, columns[c]) for c,v in zip(columns, values)}


def planned_rows(db, spec):
    keys = ['planned_time_key','plan_set_key','person_key','project_key','task_key','labor_category_key','begin_date','end_date']
    fields = keys+['planned_hours']
    for values in db.execute('SELECT '+','.join(quoted(c) for c in fields)+' FROM planned_time'):
        source = dict(zip(fields,values))
        if not source['begin_date'] or not source['end_date']:
            continue
        start = date.fromisoformat(normalize('work_date', source['begin_date']))
        end = date.fromisoformat(normalize('work_date', source['end_date']))
        if end < start:
            continue
        days = (end-start).days+1
        # No holiday exclusions: the model uses Monday-Friday only.
        count = sum((start+timedelta(days=i)).weekday()<5 for i in range(days))
        if not count:
            continue
        hours = typed(source['planned_hours'], 'double')
        with localcontext() as ctx:
            ctx.prec = 50
            daily = None if hours is None else hours/Decimal(count)
        row = {c:typed(source[c], 'date' if c in ('begin_date','end_date') else spec['columns'][c]) for c in keys}
        for i in range(days):
            day = start+timedelta(days=i)
            if day.weekday()<5:
                yield {**row,'Plan Date':day.isoformat(),'Workday Count':count,'Daily Planned Hours':daily}


def rows_for(db, name, spec):
    columns = spec['columns']
    if spec['kind'] == 'direct':
        direct_types = {c:('date' if spec['source']=='planned_time' and c in ('begin_date','end_date') else t) for c,t in columns.items()}
        yield from sql_rows(db, direct_types, {c:quoted(v) for c,v in spec['mapping'].items()}, quoted(spec['source']))
    elif name in ('Project Cost Details','Financial Document Cost Detail'):
        for row in project_cost_rows(db):
            if name == 'Financial Document Cost Detail' and not row['Cost Source'].startswith('Financial Document'):
                continue
            row['Cost Date'] = normalize('Cost Date', row['Cost Date'])
            yield {c:typed(row[c], 'date' if c=='Cost Date' else kind) for c,kind in columns.items()}
    elif name == 'planned_time_daily_Table':
        yield from planned_rows(db, spec)
    elif name == 'Cost Pool Rules':
        extras = {'code':'e.code','account_number':'e.account_number','cost_element.description':'e.description','cost_element.cost_element_type':'e.cost_element_type',**{c:'r.'+quoted(c) for c in ['target_rate','provisional_rate','actual_rate','fiscal_year_key']}}
        mapping = {c:extras.get(c,'p.'+quoted(c)) for c in columns}
        yield from sql_rows(db, columns, mapping, 'cost_struct_pool p LEFT JOIN cost_element e ON p.cost_element_key IS e.cost_element_key LEFT JOIN cost_struct_pool_rate r ON p.cost_struct_pool_key IS r.cost_struct_pool_key')
    elif name == 'Cost Report Rules':
        mapping = {c:('r.' if c in ('cost_report','description') else 'e.')+quoted(c) for c in columns}
        yield from sql_rows(db, columns, mapping, 'cost_report_element e LEFT JOIN cost_report r ON e.cost_report_key IS r.cost_report_key')
    elif name == 'Fiscal Period Close':
        mapping = {c:('m.' if c in ('fiscal_year_key','begin_date','end_date','period_number') else 'f.')+quoted(c) for c in columns}
        date_columns = {c:('date' if c in ('closed_timestamp','begin_date','end_date') else t) for c,t in columns.items()}
        yield from sql_rows(db, date_columns, mapping, 'fiscal_month_org_feature_close f LEFT JOIN fiscal_month m ON f.fiscal_month_key IS m.fiscal_month_key')
    else:
        raise ValidationError('Unsupported output transformation')


def write_output(rows, name, spec, folder, chunk_size):
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    files, total, writer, in_file = [],0,None,0
    sums = {}
    try:
        for row in rows:
            if writer is None or in_file>=chunk_size:
                if writer:
                    writer.write(']\n');writer.close()
                path = folder / f'{slug}_{len(files)+1:05d}.json'
                files.append({'path':'processed/'+path.name,'rows':0})
                writer = path.open('w',encoding='utf-8');writer.write('[');in_file=0
            if in_file:
                writer.write(',\n')
            writer.write(encode_json(row));in_file+=1;total+=1;files[-1]['rows']+=1
            if 'Cost Amount' in row and row['Cost Amount'] is not None:
                with localcontext() as ctx:
                    ctx.prec=100
                    label=row['Cost Source'];sums[label]=sums.get(label,Decimal(0))+row['Cost Amount']
        if writer:
            writer.write(']\n');writer.close();writer=None
        else:
            path=folder/(slug+'_00001.json');path.write_text('[]\n',encoding='utf-8');files=[{'path':'processed/'+path.name,'rows':0}]
    finally:
        if writer:
            writer.close()
    if total < spec.get('min_rows',0):
        raise ValidationError(name+': output below minimum row count')
    for f in files:
        with (folder/Path(f['path']).name).open('rb') as handle:
            f['sha256']=hashlib.file_digest(handle,'sha256').hexdigest()
    return {'rows':total,'columns':spec['columns'],'files':files,'cost_totals_by_source':sums}


def check_controls(tables, path):
    expected = json.loads(Path(path).read_text(encoding='utf-8'),parse_float=Decimal)
    if set(expected) != set(tables):
        raise ValidationError('Control file must include all output tables')
    for name, control in expected.items():
        if control['rows'] != tables[name]['rows']:
            raise ValidationError(name+': control row count differs')
        if {k:decimal_value(v) for k,v in control.get('cost_totals_by_source',{}).items()} != tables[name]['cost_totals_by_source']:
            raise ValidationError(name+': control cost total differs')


def run_refresh(source, cfg, output, chunk_size=50000, controls=None):
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex
    root=Path(output);run_dir=root/'runs'/run_id;run_dir.mkdir(parents=True)
    start=time.monotonic()
    try:
        with closing(sqlite3.connect(run_dir/'working.sqlite')) as db:
            db.execute('PRAGMA temp_store=FILE');db.execute('PRAGMA cache_size=-32768')
            inputs=load(db,source,cfg,run_dir)
            (run_dir/'processed').mkdir()
            tables={}
            for name,spec in cfg['outputs'].items():
                step=time.monotonic();tables[name]=write_output(rows_for(db,name,spec),name,spec,run_dir/'processed',chunk_size)
                tables[name]['seconds']=round(time.monotonic()-step,3)
                print(f'Prepared {name}: {tables[name]["rows"]} rows',flush=True)
        if controls:
            check_controls(tables,controls)
        for table in tables.values():
            for f in table['files']:
                f['blob_path']=f'processed/{run_id}/'+Path(f['path']).name
        manifest={'format_version':2,'status':'complete','run_id':run_id,'completed_at':datetime.now(timezone.utc).isoformat(),'model_snapshot':cfg['model_snapshot'],'config_sha256':hashlib.sha256(encode_json(cfg).encode()).hexdigest(),'input_tables':inputs,'tables':tables,'total_seconds':round(time.monotonic()-start,3),'validation':'schema, conversions, minimum row counts and optional control totals; business reconciliation required','source_consistency':'Sequential queries; not a transactional cross-table snapshot. Schedule during a source quiet window.'}
        (run_dir/'processed'/'manifest.json').write_text(encode_json(manifest)+'\n',encoding='utf-8')
        (run_dir/'controls.json').write_text(encode_json({n:{'rows':s['rows'],'cost_totals_by_source':s['cost_totals_by_source']} for n,s in tables.items()})+'\n',encoding='utf-8')
        return run_dir,run_id
    except Exception:
        (run_dir/'FAILED.txt').write_text('Incomplete run; completed-run pointer not changed.\n',encoding='utf-8')
        raise
    finally:
        source.close()
        (run_dir/'working.sqlite').unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description='Extract and prepare all Unanet reporting tables')
    parser.add_argument('--config',type=Path,default=Path('config/refresh.json'))
    choice=parser.add_mutually_exclusive_group(required=True);choice.add_argument('--csv-dir',type=Path);choice.add_argument('--odbc',action='store_true')
    parser.add_argument('--output-dir',type=Path,default=Path('data'))
    parser.add_argument('--rows-per-file',type=int,default=50000);parser.add_argument('--query-timeout',type=int,default=1800)
    parser.add_argument('--controls',type=Path);parser.add_argument('--publish',action='store_true')
    parser.add_argument('--container',default=os.environ.get('AZURE_STORAGE_CONTAINER','unanet'))
    args=parser.parse_args()
    if args.rows_per_file<1 or args.query_timeout<1:
        parser.error('Chunk size and query timeout must be positive')
    try:
        cfg=load_config(args.config)
        if args.publish and not cfg.get('approved_for_production'):
            raise ValidationError('Reconcile real data and set approved_for_production before publication')
        source=CSVSource(args.csv_dir) if args.csv_dir else ODBCSource(cfg['schema'],query_timeout=args.query_timeout)
        run_dir,run_id=run_refresh(source,cfg,args.output_dir,args.rows_per_file,args.controls)
        if args.publish:
            publish_to_azure(run_dir,run_id,args.container)
        # Update local pointer after cloud publication, if requested, succeeds.
        temp=args.output_dir/('.latest-'+run_id+'.json')
        temp.write_text(json.dumps({'run_id':run_id,'manifest':f'runs/{run_id}/processed/manifest.json'})+'\n',encoding='utf-8')
        os.replace(temp,args.output_dir/'latest.json')
        print('Complete. Manifest: '+str(run_dir/'processed'/'manifest.json'),flush=True)
        return 0
    except Exception as error:
        message=str(error) if isinstance(error,ValidationError) else 'File, driver, query or Azure operation failed; check configuration and permissions.'
        print(f'ERROR ({type(error).__name__}): {message}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
