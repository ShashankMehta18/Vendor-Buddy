import copy, json, tempfile, unittest
from pathlib import Path
from app.engine import run_case, investigate
from app.report import dossier
from scripts.generate_samples import make
ROOT=Path(__file__).resolve().parents[1]
class InvestigationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(); cls.root=Path(cls.tmp.name); cls.cases={}
  for s in ('clean','suspicious','scanned','duplicate'):
   cls.cases[s]=run_case(sorted((ROOT/'data/samples'/s).iterdir()),cls.root/s)
 @classmethod
 def tearDownClass(cls): cls.tmp.cleanup()
 def codes(self,s): return {f['code'] for f in self.cases[s]['findings']}
 def test_clean_bundle_has_no_findings(self): self.assertEqual(self.codes('clean'),set())
 def test_suspicious_bundle_detects_four_expected_categories(self):
  self.assertEqual(self.codes('suspicious'),{'visual_outlier','price_mismatch','quantity_mismatch','bank_change'}); self.assertIn('F002',self.cases['suspicious']['findings'][0]['related_findings'])
 def test_scanned_invoice_uses_real_ocr(self):
  inv=next(d for d in self.cases['scanned']['documents'] if d['type']=='invoice')
  self.assertEqual(inv['pages'][0]['method'],'Tesseract OCR'); self.assertEqual(inv['fields']['account']['value'],'009988776655')
 def test_scanned_bundle_compares_correctly(self): self.assertEqual(self.codes('scanned'),{'price_mismatch','quantity_mismatch','bank_change'})
 def test_duplicate_uses_hash(self): self.assertIn('duplicate',self.codes('duplicate'))
 def test_every_finding_has_valid_source_coordinates(self):
  for c in self.cases.values():
   docs={d['id']:d for d in c['documents']}
   for f in c['findings']:
    self.assertTrue(f['evidence'])
    for e in f['evidence']:
     p=docs[e['document_id']]['pages'][e['page']-1]; x,y,x2,y2=e['bbox']; self.assertTrue(0<=x<x2<=p['width'] and 0<=y<y2<=p['height'])
 def test_unrelated_vendor_is_not_compared(self):
  docs=copy.deepcopy(self.cases['suspicious']['documents']); inv=next(d for d in docs if d['type']=='invoice'); inv['fields']['vendor']['value']='Unrelated vendor'
  fs,_=investigate(docs); self.assertFalse({'price_mismatch','bank_change','quantity_mismatch'} & {f['code'] for f in fs})
 def test_unrelated_po_is_not_compared(self):
  docs=copy.deepcopy(self.cases['suspicious']['documents']); inv=next(d for d in docs if d['type']=='invoice'); inv['fields']['po_number']['value']='DIFFERENT-PO'
  fs,_=investigate(docs); self.assertFalse({'price_mismatch','quantity_mismatch'} & {f['code'] for f in fs})
 def test_missing_documents_produce_coverage_warning(self):
  _,w=investigate([self.cases['clean']['documents'][0]]); self.assertEqual(len(w),3)
 def test_currency_mismatch_skips_price_comparison(self):
  docs=copy.deepcopy(self.cases['suspicious']['documents']); inv=next(d for d in docs if d['type']=='invoice'); inv['fields']['currency']['value']='USD'
  fs,_=investigate(docs); self.assertNotIn('price_mismatch',{f['code'] for f in fs})
 def test_line_arithmetic_is_calculated(self):
  docs=copy.deepcopy(self.cases['clean']['documents']); docs[0]['items'][0]['amount']+=123
  fs,_=investigate(docs); self.assertIn('line_arithmetic',{f['code'] for f in fs}); self.assertIn('subtotal_arithmetic',{f['code'] for f in fs})
 def test_total_arithmetic_is_calculated(self):
  docs=copy.deepcopy(self.cases['clean']['documents']); docs[0]['fields']['total']['value']='999.00'
  fs,_=investigate(docs); self.assertIn('total_arithmetic',{f['code'] for f in fs})
 def test_renamed_files_keep_detections(self):
  paths=sorted((ROOT/'data/samples/suspicious').iterdir()); c=run_case(paths,self.root/'renamed',[f'arbitrary-{i}.pdf' for i in range(len(paths))]); self.assertEqual({f['code'] for f in c['findings']},self.codes('suspicious'))
 def test_unseen_values_are_not_hardcoded(self):
  d=self.root/'unseen-input'; d.mkdir()
  for name,kind,kw in [('a','PURCHASE ORDER',{'price':230}),('b','DELIVERY RECEIPT',{'price':230,'qty':42}),('c','TAX INVOICE',{'price':310,'qty':70})]: make(d/f'{name}.pdf',kind,vendor='Meridian Components',po='PO-7788',**kw)
  c=run_case(sorted(d.iterdir()),self.root/'unseen-output'); codes={f['code'] for f in c['findings']}; self.assertIn('price_mismatch',codes); self.assertIn('quantity_mismatch',codes)
 def test_corrupt_file_is_reported(self):
  p=self.root/'broken.pdf'; p.write_bytes(b'not a pdf'); c=run_case([p],self.root/'broken'); self.assertEqual(len(c['failures']),1)
 def test_pdf_report_contains_evidence(self):
  raw=dossier(self.cases['suspicious'],self.root/'suspicious'); self.assertTrue(raw.startswith(b'%PDF'))
  import pymupdf
  pdf=pymupdf.open(stream=raw,filetype='pdf'); text=' '.join(p.get_text() for p in pdf); self.assertIn('Payment account differs',text); self.assertIn('Evidence:',text); self.assertIn('Line items and document structure',text); self.assertIn('Detection confidence: uncalibrated',text); self.assertIn('Document submitted:',text)
if __name__=='__main__': unittest.main()
