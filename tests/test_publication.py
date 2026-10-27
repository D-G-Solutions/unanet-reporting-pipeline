"""Publication ordering tested with a fake Azure SDK, not a live Azure account."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from unanet_pipeline.adapters import publish_to_azure

class NotFound(Exception):
    pass

class Context:
    def __enter__(self):return self
    def __exit__(self, *args):pass

class FakeAzure:
    def __init__(self, fail_upload=False, exists=True):
        self.events=[];self.fail_upload=fail_upload;self.exists=exists

    def modules(self):
        outer=self
        class Credential(Context):
            pass
        class ContentSettings:
            def __init__(self, **kwargs):pass
        class Pointer:
            def download_blob(self):
                if not outer.exists:raise NotFound()
                return types.SimpleNamespace(properties=types.SimpleNamespace(etag='baseline-etag'), readall=lambda:b'{"run_id":"older-run"}')
            def upload_blob(self, payload, **kwargs):
                outer.events.append(('pointer',kwargs))
        class Client:
            def get_blob_client(self, name):return Pointer()
            def upload_blob(self, name, handle, **kwargs):
                outer.events.append(('file',name))
                if outer.fail_upload:raise RuntimeError('simulated upload failure')
                self.assert_payload=handle.read()
        class Service(Context):
            def __init__(self,*args,**kwargs):pass
            def get_container_client(self,name):return Client()
        modules={name:types.ModuleType(name) for name in ['azure','azure.identity','azure.storage','azure.storage.blob','azure.core','azure.core.exceptions']}
        modules['azure.identity'].DefaultAzureCredential=Credential
        modules['azure.storage.blob'].BlobServiceClient=Service
        modules['azure.storage.blob'].ContentSettings=ContentSettings
        modules['azure.core'].MatchConditions=types.SimpleNamespace(IfNotModified='match')
        modules['azure.core.exceptions'].ResourceNotFoundError=NotFound
        return modules

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        for name in ['raw','processed']:(self.folder/name).mkdir()
        (self.folder/'raw'/'source.jsonl').write_text('{}\n')
        (self.folder/'processed'/'cost.json').write_text('[]')
        (self.folder/'processed'/'manifest.json').write_text('{}')

    def publish(self, fake):
        with patch.dict(sys.modules,fake.modules()), patch.dict('os.environ',{'AZURE_STORAGE_ACCOUNT_URL':'https://example.blob.core.windows.net'}):
            publish_to_azure(self.folder,'synthetic-run','unanet')

    def test_latest_changed_after_every_file_with_etag_guard(self):
        fake=FakeAzure();self.publish(fake)
        self.assertEqual(['file','file','file','pointer'],[e[0] for e in fake.events])
        self.assertEqual('baseline-etag',fake.events[-1][1]['etag'])
        self.assertEqual('match',fake.events[-1][1]['match_condition'])

    def test_failed_upload_does_not_change_previous_pointer(self):
        fake=FakeAzure(fail_upload=True)
        with self.assertRaises(RuntimeError):self.publish(fake)
        self.assertFalse(any(e[0]=='pointer' for e in fake.events))

    def test_first_publication_refuses_to_overwrite_competing_pointer(self):
        fake=FakeAzure(exists=False);self.publish(fake)
        self.assertFalse(fake.events[-1][1]['overwrite'])

    def test_older_run_cannot_replace_newer_run(self):
        fake=FakeAzure()
        with patch.dict(sys.modules,fake.modules()), patch.dict('os.environ',{'AZURE_STORAGE_ACCOUNT_URL':'https://example.blob.core.windows.net'}):
            with self.assertRaises(ValueError):publish_to_azure(self.folder,'aaa-older-run','unanet')
        self.assertEqual([],fake.events)
