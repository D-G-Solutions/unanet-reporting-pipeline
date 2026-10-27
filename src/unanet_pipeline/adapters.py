"""Local CSV input, ODBC extraction, and optional Azure Blob publication."""
import os
import re
import sys
from pathlib import Path
from .core import csv_rows, ValidationError

class CSVSource:
    def __init__(self, folder):
        self.folder = Path(folder)

    def rows(self, table, columns):
        for row in csv_rows(self.folder, table, columns):
            yield {c:None if v=='' else v for c,v in row.items()}

    def close(self):
        pass

class ODBCSource:
    def __init__(self, schema='dngspt', batch_size=2000, query_timeout=600):
        import pyodbc
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', schema):
            raise ValidationError('Invalid source schema')
        connection_string = os.environ.get('UNANET_ODBC_CONNECTION_STRING')
        if not connection_string:
            raise ValidationError('UNANET_ODBC_CONNECTION_STRING is required')
        self.schema, self.batch_size = schema, batch_size
        self.connection = pyodbc.connect(connection_string, timeout=30, autocommit=True)
        try:
            self.connection.timeout = query_timeout
        except pyodbc.Error as error:
            # The Data Virtuality driver can reject SQL_ATTR_CONNECTION_TIMEOUT
            # (113). Continue only for that specific unsupported-attribute error;
            # authentication, network and other driver failures still propagate.
            message = str(error).lower()
            if '113' in message and 'unsupported connect attribute' in message and 'sqlsetconnectattr' in message:
                print('WARNING: Driver rejects timeout attribute 113. Using driver default; the requested query timeout is not enforced. Use the job execution timeout as the outer limit.', file=sys.stderr)
            else:
                self.connection.close()
                raise

    def rows(self, table, columns):
        # Table and column names come exclusively from the reviewed static schema.
        cursor = self.connection.cursor()
        try:
            selection = ','.join('"'+c+'"' for c in columns)
            cursor.execute(f'SELECT {selection} FROM "{self.schema}"."{table}"')
            while True:
                batch = cursor.fetchmany(self.batch_size)
                if not batch:
                    break
                for values in batch:
                    yield dict(zip(columns, values))
        finally:
            cursor.close()

    def close(self):
        self.connection.close()


def publish_to_azure(run_dir, run_id, container):
    """Upload immutable files, then change the latest pointer using an ETag guard.

    A competing publication causes failure instead of silently overwriting it.
    A partial upload never changes the previous completed-run pointer.
    """
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings
    from azure.core import MatchConditions
    from azure.core.exceptions import ResourceNotFoundError
    account_url = os.environ.get('AZURE_STORAGE_ACCOUNT_URL', '')
    if not account_url.startswith('https://') or '?' in account_url:
        raise ValidationError('Set AZURE_STORAGE_ACCOUNT_URL to the HTTPS account URL without a SAS token')
    with DefaultAzureCredential() as credential:
        with BlobServiceClient(account_url, credential=credential) as service:
            client = service.get_container_client(container)
            pointer = client.get_blob_client('processed/latest.json')
            try:
                previous = pointer.download_blob()
                old_etag = previous.properties.etag
                import json
                previous_id = json.loads(previous.readall())['run_id']
                if run_id < previous_id:
                    raise ValidationError('A newer run is already published; older run will not replace it')
            except ResourceNotFoundError:
                old_etag = None
            for folder in ['raw','processed']:
                for path in sorted((run_dir / folder).iterdir()):
                    if not path.is_file():
                        continue
                    blob_name = f'{folder}/{run_id}/{path.name}'
                    with path.open('rb') as handle:
                        client.upload_blob(blob_name, handle, overwrite=False, content_settings=ContentSettings(content_type='application/json' if path.suffix=='.json' else 'application/x-ndjson'))
            payload = ('{"run_id":"'+run_id+'","manifest":"processed/'+run_id+'/manifest.json"}').encode()
            options = {'content_settings':ContentSettings(content_type='application/json')}
            if old_etag is None:
                pointer.upload_blob(payload, overwrite=False, **options)
            else:
                pointer.upload_blob(payload, overwrite=True, etag=old_etag, match_condition=MatchConditions.IfNotModified, **options)
