import io, os, tempfile, unittest
from pathlib import Path
TMP=tempfile.TemporaryDirectory()
os.environ['VENDOR_BUDDY_DATA_DIR']=TMP.name
from fastapi.testclient import TestClient
from app.main import app
ROOT=Path(__file__).resolve().parents[1]
class ApiTests(unittest.TestCase):
 def setUp(self): self.client=TestClient(app)
 def test_complete_review_report_delete_workflow(self):
  r=self.client.post('/api/demo/suspicious'); self.assertEqual(r.status_code,200); c=r.json(); self.assertEqual(len(c['findings']),4); cid=c['id']
  ev=c['findings'][0]['evidence'][0]; d=next(d for d in c['documents'] if d['id']==ev['document_id'])
  self.assertEqual(self.client.get(f"/api/investigations/{cid}/pages/{d['pages'][0]['image']}").status_code,200)
  r=self.client.patch(f'/api/investigations/{cid}/findings/F001',json={'status':'needs clarification'}); self.assertEqual(r.status_code,200); self.assertGreater(len(r.json()['audit']),len(c['audit'])); self.assertIn('reviewer status changed',r.json()['audit'][-1]['event'])
  report=self.client.get(f'/api/investigations/{cid}/report.pdf'); self.assertEqual(report.status_code,200); self.assertTrue(report.content.startswith(b'%PDF'))
  self.assertEqual(self.client.get(f'/api/investigations/{cid}/export.json').status_code,200)
  self.assertEqual(self.client.delete(f'/api/investigations/{cid}').status_code,200); self.assertEqual(self.client.get(f'/api/investigations/{cid}').status_code,404)
 def test_upload_really_processes_supplied_bytes(self):
  files=[]
  for p in sorted((ROOT/'data/samples/clean').iterdir()): files.append(('files',(p.name,p.read_bytes(),'application/pdf')))
  r=self.client.post('/api/investigations',files=files); self.assertEqual(r.status_code,200); self.assertEqual(r.json()['findings'],[])
 def test_unsupported_upload_rejected(self): self.assertEqual(self.client.post('/api/investigations',files={'files':('test.exe',b'bad','application/octet-stream')}).status_code,400)
 def test_invalid_case_id_rejected(self): self.assertEqual(self.client.get('/api/investigations/invalid').status_code,404)
 def test_invalid_review_status_rejected(self):
  c=self.client.post('/api/demo/clean').json(); self.assertEqual(self.client.patch(f"/api/investigations/{c['id']}/findings/F001",json={'status':'approve payment'}).status_code,400)
if __name__=='__main__': unittest.main()
