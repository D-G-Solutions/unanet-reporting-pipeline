"""Compare a current Power BI Project Cost Details CSV against prepared JSON.
Use underlying full rows, not a summarized visual or a truncated export.
"""
import argparse,csv,json,sys
from collections import Counter
from decimal import Decimal,localcontext
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from unanet_pipeline.core import decimal_value

def aggregate(rows):
    count=Counter();totals=Counter();nulls=Counter()
    with localcontext() as ctx:
        ctx.prec=100
        for row in rows:
            label=row['Cost Source'];count[label]+=1
            value=row['Cost Amount']
            if value is None or value=='':nulls[label]+=1
            else:totals[label]+=decimal_value(value)
    return {'rows':dict(count),'totals':dict(totals),'null_amounts':dict(nulls)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--power-bi-csv',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--delimiter',default=',');args=parser.parse_args()
    with args.power_bi_csv.open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle,delimiter=args.delimiter)
        if not {'Cost Source','Cost Amount'}<=set(reader.fieldnames or []):parser.error('CSV needs Cost Source and Cost Amount columns')
        expected=aggregate(reader)
    manifest=json.loads(args.manifest.read_text());table=manifest['tables']['Project Cost Details']
    def rows():
        for file in table['files']:
            # Manifest paths are relative to its run directory.
            yield from json.loads((args.manifest.parent.parent/file['path']).read_text(),parse_float=Decimal)
    actual=aggregate(rows())
    print('Power BI:',expected);print('Python:',actual)
    if expected!=actual:print('FAIL: row counts, totals or null amounts differ.');return 1
    print('PASS: row counts, cost totals and null amounts agree by source. Still compare dates, keys and report measures.');return 0
if __name__=='__main__':raise SystemExit(main())
