import argparse
from contextlib import closing
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from .adapters import CSVSource, ODBCSource, publish_to_azure
from .core import ValidationError, encode_json, load_sources, write_costs


def run(source, output, rows_per_file=50000, closed_through=None, expectation=None):
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex
    root = Path(output)
    run_dir = root / 'runs' / run_id
    run_dir.mkdir(parents=True)
    started = time.monotonic()
    try:
        with closing(sqlite3.connect(run_dir / 'working.sqlite')) as db, db:
            db.execute('PRAGMA temp_store=FILE')
            db.execute('PRAGMA cache_size=-32768')
            step = time.monotonic()
            inputs = load_sources(db, source, run_dir)
            extraction_seconds = time.monotonic() - step
            print('Extraction complete; preparing cost data.', flush=True)
            step = time.monotonic()
            costs = write_costs(db, run_dir, rows_per_file, closed_through)
            transform_seconds = time.monotonic() - step
        if expectation:
            check_expectations(costs, expectation)
        for item in costs['files']:
            item['blob_path'] = f'processed/{run_id}/' + Path(item['path']).name
        manifest = {'format_version':1,'run_id':run_id,'completed_at':datetime.now(timezone.utc).isoformat(),'status':'complete','closed_through':closed_through,'input_tables':inputs,'project_cost_details':costs,'timings_seconds':{'extract':extraction_seconds,'transform':transform_seconds,'total':time.monotonic()-started},'validation':'structural and optional control totals; business reconciliation still required'}
        (run_dir / 'processed' / 'manifest.json').write_text(encode_json(manifest)+'\n', encoding='utf-8')
        # One local pointer is atomically replaced only after successful validation.
        temporary = root / ('.latest-' + run_id + '.json')
        temporary.write_text(json.dumps({'run_id':run_id,'manifest':f'runs/{run_id}/processed/manifest.json'})+'\n', encoding='utf-8')
        os.replace(temporary, root / 'latest.json')
        print(f'Prepared {costs["rows"]} rows. Run: {run_id}', flush=True)
        return run_dir, run_id
    except Exception:
        (run_dir / 'FAILED.txt').write_text('Run failed. Last completed-run pointer was not changed. Diagnose using non-sensitive stage information.\n', encoding='utf-8')
        raise
    finally:
        source.close()


def check_expectations(costs, path):
    from .core import decimal_value
    expected = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(expected.get('rows'), int) or expected['rows'] != costs['rows']:
        raise ValidationError('Expected output row count does not match')
    totals = expected.get('cost_totals_by_source')
    if not isinstance(totals, dict) or set(totals) != set(costs['by_source']):
        raise ValidationError('Expected cost sources do not match')
    for source, amount in totals.items():
        if decimal_value(amount) != costs['by_source'][source]['cost_total']:
            raise ValidationError('Expected cost total does not match')


def main():
    parser = argparse.ArgumentParser(description='Unanet Project Cost Details extraction and preparation')
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--csv-dir', type=Path)
    inputs.add_argument('--odbc', action='store_true')
    parser.add_argument('--schema', default='dngspt')
    parser.add_argument('--output-dir', type=Path, default=Path('data'))
    parser.add_argument('--rows-per-file', type=int, default=50000)
    parser.add_argument('--query-timeout', type=int, default=600)
    parser.add_argument('--closed-through', type=date.fromisoformat)
    parser.add_argument('--expectations', type=Path)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--container', default=os.environ.get('AZURE_STORAGE_CONTAINER', 'unanet'))
    args = parser.parse_args()
    if args.publish and not args.expectations:
        parser.error('--publish requires --expectations from a reconciled baseline')
    if args.rows_per_file < 1 or args.query_timeout < 1:
        parser.error('rows-per-file and query-timeout must be positive')
    try:
        source = CSVSource(args.csv_dir) if args.csv_dir else ODBCSource(args.schema, query_timeout=args.query_timeout)
        run_dir, run_id = run(source, args.output_dir, args.rows_per_file, args.closed_through.isoformat() if args.closed_through else None, args.expectations)
        if args.publish:
            publish_to_azure(run_dir, run_id, args.container)
            print('Azure publication complete.', flush=True)
        return 0
    except Exception as error:
        # Driver/SDK errors can contain hostnames, SQL text, and credentials.
        # Do not print their raw messages or tracebacks into shared job logs.
        message = str(error) if isinstance(error, ValidationError) else 'Connection or file operation failed; check local configuration and access.'
        print(f'ERROR ({type(error).__name__}): {message}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
