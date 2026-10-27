"""Driver compatibility tested with fake pyodbc, not a live source."""
import contextlib,io,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from unanet_pipeline.adapters import ODBCSource
class DriverError(Exception):pass
class Connection:
    def __init__(self,message=None):self.message=message;self.closed=False;self._timeout=0
    @property
    def timeout(self):return self._timeout
    @timeout.setter
    def timeout(self,value):
        if self.message:raise DriverError(self.message)
        self._timeout=value
    def close(self):self.closed=True
class ODBCCompatibilityTests(unittest.TestCase):
    def construct(self,connection):
        fake=types.SimpleNamespace(Error=DriverError,connect=lambda *a,**k:connection)
        with patch.dict(sys.modules,{'pyodbc':fake}),patch.dict('os.environ',{'UNANET_ODBC_CONNECTION_STRING':'DSN=synthetic;'}):return ODBCSource(query_timeout=60)
    def test_specific_unsupported_attribute_continues(self):
        c=Connection("HY000 Couldn't set unsupported connect attribute 113 (216) (SQLSetConnectAttr)")
        with contextlib.redirect_stderr(io.StringIO()) as output:source=self.construct(c)
        self.assertFalse(c.closed);self.assertIn('not enforced',output.getvalue());source.close();self.assertTrue(c.closed)
    def test_supported_timeout_is_applied(self):
        c=Connection();self.construct(c);self.assertEqual(60,c.timeout)
    def test_other_driver_failure_propagates_and_closes(self):
        c=Connection('HY000 network failure')
        with self.assertRaises(DriverError):self.construct(c)
        self.assertTrue(c.closed)
