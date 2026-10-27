"""Disk-backed joins, exact decimal arithmetic, and streamed JSON outputs."""
import csv
import hashlib
import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from .schema import TABLES, OUTPUT, NUMBERS, DATES

class ValidationError(ValueError):
    pass


def decimal_value(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError('Invalid numeric value') from None
    if not result.is_finite():
        raise ValidationError('Non-finite numeric value')
    return result


def normalize(column, value):
    if value is None or value == '':
        return None
    if column.endswith('_key'):
        number = decimal_value(value)
        if number != number.to_integral_value() or not -(2**63) <= number < 2**63:
            raise ValidationError(f'{column} must be a signed 64-bit integer')
        return str(int(number))
    if column in NUMBERS:
        return str(decimal_value(value))
    if column in DATES:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        try:
            # ISO dates or ISO timestamps only; ambiguous local date strings fail.
            return datetime.fromisoformat(str(value).replace('Z', '+00:00')).date().isoformat()
        except ValueError:
            raise ValidationError(f'{column} must be an ISO date or timestamp') from None
    return str(value)


def encode_json(value):
    """Decimal values are JSON numbers, never converted through binary float."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValidationError('Non-finite output')
        return format(value, 'f')
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + ':' + encode_json(v) for k,v in value.items()) + '}'
    if isinstance(value, (list, tuple)):
        return '[' + ','.join(encode_json(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def csv_rows(folder, table, columns):
    with (Path(folder) / f'{table}.csv').open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValidationError(f'{table}: missing or duplicate CSV headers')
        if set(columns) - set(reader.fieldnames):
            raise ValidationError(f'{table}: required columns missing')
        for row in reader:
            if None in row or any(row[c] is None for c in columns):
                raise ValidationError(f'{table}: malformed CSV record')
            yield {c: row[c] for c in columns}


def load_sources(connection, source, run_dir):
    """Read each source once into raw JSONL and an indexed temporary SQLite file."""
    raw_dir = run_dir / 'raw'
    raw_dir.mkdir()
    stats = {}
    for table, columns in TABLES.items():
        connection.execute(f'CREATE TABLE {quoted(table)} ({",".join(quoted(c)+" TEXT" for c in columns)})')
        insert = f'INSERT INTO {quoted(table)} VALUES ({",".join("?" for _ in columns)})'
        count = 0
        with (raw_dir / f'{table}.jsonl').open('w', encoding='utf-8') as raw:
            batch = []
            for row in source.rows(table, columns):
                if set(columns) - row.keys():
                    raise ValidationError(f'{table}: required columns missing')
                # Raw capture preserves original strings, dates, and numeric precision.
                original = {c: row[c].isoformat() if isinstance(row[c], (date, datetime)) else row[c] for c in columns}
                raw.write(encode_json(original) + '\n')
                batch.append(tuple(normalize(c, row[c]) for c in columns))
                count += 1
                if len(batch) >= 2000:
                    connection.executemany(insert, batch)
                    batch.clear()
            if batch:
                connection.executemany(insert, batch)
        for column in columns:
            if column.endswith('_key'):
                connection.execute(f'CREATE INDEX {quoted(table+"_"+column)} ON {quoted(table)} ({quoted(column)})')
        stats[table] = {'rows': count}
    connection.commit()
    return stats

# IS provides null-safe equality for Power Query join semantics. Duplicate
# matches intentionally expand rows, as Table.NestedJoin + Expand does.
BRANCHES = [
 ('Labor', 'person_time_data p LEFT JOIN cost_struct_labor l ON p.cost_struct_labor_key IS l.cost_struct_labor_key', {
  'project_key':'p.project_key','task_key':'p.task_key','eff_quantity':'p.eff_quantity','eff_cost_rate':'p.eff_cost_rate','quantity':'p.quantity','cost_struct_key':'l.cost_struct_key','cost_element_key':'l.cost_element_key','Cost Date':'p.work_date',
 }),
 ('Expense', 'expense_data_allocation a LEFT JOIN expense_data d ON a.expense_data_key IS d.expense_data_key LEFT JOIN cost_struct_odc o ON a.cost_struct_odc_key IS o.cost_struct_odc_key LEFT JOIN cost_element e ON o.cost_element_key IS e.cost_element_key', {
  'project_key':'a.project_key','task_key':'a.task_key','Cost Amount':'a.amount','billable':'a.billable','Cost Date':'d.expense_date','cost_element_key':'o.cost_element_key','code':'e.code',
 }),
 ('Financial Document Expense', 'fin_document_det_proj_expense p LEFT JOIN fin_document_detail d ON p.fin_document_detail_key IS d.fin_document_detail_key LEFT JOIN fin_document_detail_expense e ON p.fin_document_detail_key IS e.fin_document_detail_key LEFT JOIN cost_struct_odc o ON e.cost_struct_odc_key IS o.cost_struct_odc_key', {
  'fin_document_detail_key':'p.fin_document_detail_key','project_key':'p.project_key','task_key':'p.task_key','expense_type_key':'p.expense_type_key','project_type_key':'p.project_type_key','fin_document_key':'d.fin_document_key','account_key':'d.account_key','Cost Date':'d.transaction_date','debit_amount':'d.debit_amount','credit_amount':'d.credit_amount','Cost Amount':'e.amount','bill_amount':'e.bill_amount','cost_struct_odc_key':'e.cost_struct_odc_key','cost_element_key':'o.cost_element_key',
 }),
 ('Financial Document Labor', 'fin_document_det_proj_labor p LEFT JOIN fin_document_detail d ON p.fin_document_detail_key IS d.fin_document_detail_key LEFT JOIN fin_document_detail_labor l ON p.fin_document_detail_key IS l.fin_document_detail_key LEFT JOIN cost_struct_labor s ON l.cost_struct_labor_key IS s.cost_struct_labor_key', {
  'fin_document_detail_key':'p.fin_document_detail_key','project_key':'p.project_key','task_key':'p.task_key','project_type_key':'p.project_type_key','labor_category_key':'p.labor_category_key','hours':'p.hours','cost_rate':'p.cost_rate','fin_document_key':'d.fin_document_key','account_key':'d.account_key','Cost Date':'d.transaction_date','debit_amount':'d.debit_amount','credit_amount':'d.credit_amount','Cost Amount':'l.amount','cost_struct_labor_key':'l.cost_struct_labor_key','cost_element_key':'s.cost_element_key',
 }),
]


def project_cost_rows(connection):
    for name, joins, mapping in BRANCHES:
        selected = ','.join(mapping.get(c, 'NULL') + ' AS ' + quoted(c) for c in OUTPUT)
        for values in connection.execute('SELECT ' + selected + ' FROM ' + joins):
            row = dict(zip(OUTPUT, values))
            for column, value in row.items():
                if value is not None and column.endswith('_key'):
                    row[column] = int(value)
                elif value is not None and column in NUMBERS:
                    row[column] = decimal_value(value)
            row['Cost Source'] = name
            if name == 'Labor':
                q, rate = row['quantity'], row['eff_cost_rate']
                if q is not None and rate is not None:
                    with localcontext() as context:
                        context.prec = max(50, len(q.as_tuple().digits) + len(rate.as_tuple().digits) + 2)
                        row['Cost Amount'] = q * rate
            yield row


def write_costs(connection, run_dir, rows_per_file=50000, closed_through=None):
    if rows_per_file < 1:
        raise ValidationError('rows_per_file must be positive')
    folder = run_dir / 'processed'
    folder.mkdir()
    files, stats = [], {}
    writer = None
    in_file, total, excluded = 0, 0, 0
    try:
        for row in project_cost_rows(connection):
            if closed_through and row['Cost Date'] and row['Cost Date'] > closed_through:
                excluded += 1
                continue
            # Missing dates cannot be silently treated as within a closed period.
            if closed_through and row['Cost Date'] is None:
                raise ValidationError('Missing Cost Date with closed-period filtering enabled')
            if writer is None or in_file >= rows_per_file:
                if writer:
                    writer.write(']\n'); writer.close()
                path = folder / f'project_cost_details_{len(files)+1:05d}.json'
                files.append({'path': 'processed/' + path.name, 'rows': 0})
                writer = path.open('w', encoding='utf-8')
                writer.write('[')
                in_file = 0
            if in_file:
                writer.write(',\n')
            writer.write(encode_json(row))
            in_file += 1; total += 1; files[-1]['rows'] += 1
            entry = stats.setdefault(row['Cost Source'], {'rows':0,'cost_total':Decimal(0),'null_costs':0,'null_dates':0,'null_cost_elements':0})
            entry['rows'] += 1
            if row['Cost Amount'] is None:
                entry['null_costs'] += 1
            else:
                # Exact decimal accumulation without the default 28-digit rounding.
                with localcontext() as context:
                    context.prec = 100
                    entry['cost_total'] += row['Cost Amount']
            entry['null_dates'] += row['Cost Date'] is None
            entry['null_cost_elements'] += row['cost_element_key'] is None
        if total == 0:
            raise ValidationError('No reporting rows produced; refusing to publish empty output')
        writer.write(']\n'); writer.close(); writer = None
    finally:
        if writer:
            writer.close()
    for item in files:
        with (run_dir / item['path']).open('rb') as handle:
            item['sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest()
    return {'rows':total,'excluded_after_cutoff':excluded,'by_source':stats,'files':files,'columns':OUTPUT}
