"""Document extraction and evidence-based vendor investigation. No fixture lookup."""
from __future__ import annotations
import csv, hashlib, io, os, re, shutil, statistics, subprocess, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

LABELS = {
 'invoice': ['tax invoice invoice number amount due bill to payment details subtotal unit price', 'commercial invoice invoice no vendor line amount bank account total due', 'supplier invoice billing invoice date purchase order total payable'],
 'purchase_order': ['purchase order purchase order number ordered quantity approved unit price buyer supplier', 'purchase order order date po number authorized procurement order total', 'procurement order purchase order vendor items ordered quantity'],
 'delivery_receipt': ['delivery receipt goods received receipt number received quantity delivery date', 'goods receipt note delivery note po number received by delivered quantity', 'delivery acknowledgement delivery receipt items received supplier'],
 'vendor_record': ['approved vendor record registered bank account vendor id approved on bank name', 'vendor master record approved bank details account number supplier beneficiary', 'supplier registration approved payment details vendor record registered account']
}
# Deliberately small prototype classifier. Scores are model scores, not calibrated probabilities.
_train, _targets = [], []
for label, examples in LABELS.items():
 for ex in examples:
  _train.append(ex); _targets.append(label)
CLASSIFIER = make_pipeline(TfidfVectorizer(ngram_range=(1,2)), LogisticRegression(C=8,max_iter=500)).fit(_train, _targets)
FIELD_LABELS = {
 'vendor': r'(?:vendor name|supplier name|vendor|supplier)',
 'po_number': r'(?:purchase order number|purchase order no\.?|po number|po no\.?)',
 'invoice_number': r'(?:invoice number|invoice no\.?)',
 'date': r'(?:invoice date|order date|delivery date|approved on|date)',
 'account': r'(?:bank account|account number|account no\.?|registered account)',
 'bank': r'(?:bank name|bank)',
 'currency': r'(?:currency)',
 'subtotal': r'(?:subtotal|sub total)',
 'tax': r'(?:tax amount|tax)',
 'total': r'(?:grand total|total due|amount due|order total|total payable|total)',
 'status': r'(?:delivery status|status)',
 'terms': r'(?:billing terms|payment terms|terms)',
}

def num(value):
 try: return float(re.sub(r'[^0-9.\-]','',str(value)))
 except (ValueError, TypeError): return None

def bbox(words):
 return [round(min(w['bbox'][0] for w in words),2),round(min(w['bbox'][1] for w in words),2),round(max(w['bbox'][2] for w in words),2),round(max(w['bbox'][3] for w in words),2)]

def ocr_image(image: Image.Image):
 if not shutil.which('tesseract'): raise RuntimeError('Scanned documents require Tesseract. Install it and restart the application.')
 image = image.convert('RGB')
 if image.width*image.height > 30_000_000: raise ValueError('Image exceeds 30 megapixels.')
 with tempfile.TemporaryDirectory() as temp:
  src = Path(temp)/'page.png'; image.save(src)
  p = subprocess.run(['tesseract',str(src),'stdout','-l','eng','--psm','6','tsv'],capture_output=True,text=True,timeout=45)
  if p.returncode: raise RuntimeError('OCR failed. Check the image and English Tesseract language pack.')
  lines=defaultdict(list)
  for row in csv.DictReader(io.StringIO(p.stdout),delimiter='\t'):
   if not row.get('text','').strip(): continue
   conf=float(row['conf'])
   if conf < 0: continue
   x,y,w,h = [int(row[k]) for k in ('left','top','width','height')]
   lines[(row['block_num'],row['par_num'],row['line_num'])].append({'text':row['text'],'bbox':[x,y,x+w,y+h],'confidence':round(conf/100,3),'size':h,'font':'OCR'})
  return list(lines.values())

def extract_document(path: Path, dest: Path, display_name=None):
 raw = path.read_bytes(); did=uuid.uuid4().hex[:12]
 doc={'id':did,'name':display_name or path.name,'sha256':hashlib.sha256(raw).hexdigest(),'pages':[],'fields':{},'items':[],'warnings':[],'visual':[]}
 suffix=path.suffix.lower()
 if suffix=='.pdf':
  pdf=pymupdf.open(path)
  if pdf.is_encrypted: raise ValueError('Encrypted PDFs are unsupported.')
  if len(pdf)>12: raise ValueError('Maximum 12 pages per document.')
  source_pages=list(pdf)
 else:
  im=Image.open(path); im.load(); source_pages=[im]
 all_lines=[]
 for index, page in enumerate(source_pages):
  page_num=index+1
  if suffix=='.pdf':
   pix=page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6),alpha=False)
   image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
   width,height=page.rect.width,page.rect.height
   # Merge words sharing a baseline even when the PDF stores columns in separate blocks.
   groups=[]
   for w in sorted(page.get_text('words'),key=lambda w:(round(w[3]/5),w[0])):
    target=next((g for g in groups if abs(g[0]['bbox'][3]-w[3])<5),None)
    word={'text':w[4],'bbox':list(w[:4]),'confidence':None,'size':w[3]-w[1],'font':'embedded'}
    if target is None: groups.append([word])
    else: target.append(word)
   lines=[sorted(ws,key=lambda x:x['bbox'][0]) for ws in groups]
   method='PDF text'
   if sum(len(w['text']) for line in lines for w in line)<35:
    lines=ocr_image(image); width,height=image.size; method='Tesseract OCR'
   else:
    # Font metadata is useful for born-digital PDFs, never a proof of manipulation.
    spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
    numeric=[s for s in spans if re.fullmatch(r'[\d,]+\.\d{2}',s['text'].strip())]
    if len(numeric)>=4:
     med=statistics.median(s['size'] for s in numeric)
     fonts=[s['font'] for s in numeric]; common=max(set(fonts),key=fonts.count)
     for s in numeric:
      if s['size']>med*1.35 and s['font']!=common:
       doc['visual'].append({'page':page_num,'bbox':list(s['bbox']),'text':s['text'],'method':'PDF numeric typography outlier','detail':f"Numeric span uses {s['font']} at {s['size']:.1f} pt; median monetary span is {med:.1f} pt. Legitimate emphasis is an alternative explanation."})
  else:
   image=page.convert('RGB'); lines=ocr_image(image); width,height=image.size; method='Tesseract OCR'
  image_path=dest/f'{did}-{page_num}.png'; image.save(image_path)
  pinfo={'number':page_num,'width':width,'height':height,'image':image_path.name,'method':method,'lines':[]}
  for words in lines:
   if not words: continue
   line={'text':' '.join(w['text'] for w in words),'bbox':bbox(words),'page':page_num,'words':words}
   pinfo['lines'].append(line); all_lines.append(line)
  # Raster observation: size of numeric OCR token relative to nearby monetary tokens.
  if method=='Tesseract OCR':
   numbers=[w for line in pinfo['lines'] for w in line['words'] if re.fullmatch(r'[\d,]+\.\d{2}',w['text'])]
   if len(numbers)>=5:
    med=statistics.median(w['size'] for w in numbers)
    for w in numbers:
     if w['size']>med*1.6:
      doc['visual'].append({'page':page_num,'bbox':w['bbox'],'text':w['text'],'method':'Raster numeric height outlier','detail':f"OCR numeric region is {w['size']:.0f} px tall versus median {med:.0f} px. Scan quality or intentional emphasis may explain the difference."})
  doc['pages'].append(pinfo)
 text='\n'.join(l['text'] for l in all_lines)
 probs=CLASSIFIER.predict_proba([text])[0]; best=int(probs.argmax())
 doc['type']=str(CLASSIFIER.classes_[best]) if probs[best]>=.4 else 'unknown'
 doc['classification']={'method':'TF-IDF + logistic regression','score':round(float(probs[best]),3),'calibrated':False}
 # Explicit headings resolve familiar types. Classifier handles less explicit documents.
 head=' '.join(l['text'] for l in all_lines[:5]).lower()
 for title, label in [('approved vendor','vendor_record'),('purchase order','purchase_order'),('delivery receipt','delivery_receipt'),('goods receipt','delivery_receipt'),('tax invoice','invoice'),('commercial invoice','invoice')]:
  if title in head: doc['type']=label; doc['classification']['method']='Document heading + TF-IDF classifier'; break
 for line in all_lines:
  for key, label in FIELD_LABELS.items():
   m=re.match(r'^\s*'+label+r'\s*[:#]\s*(.+?)\s*$',line['text'],re.I)
   if m and key not in doc['fields']:
    value=m.group(1).strip(); ws=line['words']; val_words=[]
    # Search a suffix so label coordinates do not replace the actual value region.
    for j in range(len(ws)):
     if ' '.join(w['text'] for w in ws[j:])==value: val_words=ws[j:]; break
    confs=[w['confidence'] for w in (val_words or ws) if w['confidence'] is not None]
    doc['fields'][key]={'value':value,'page':line['page'],'bbox':bbox(val_words or ws),'confidence':round(sum(confs)/len(confs),3) if confs else None,'method':'Tesseract OCR' if confs else 'PDF text; confidence unavailable'}
  # A supported table row ends in quantity, unit price and amount, preceded by SKU and description.
  m=re.match(r'^([A-Z][A-Z0-9-]{1,20})\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$',line['text'])
  if m:
   doc['items'].append({'sku':m[1],'description':m[2],'quantity':num(m[3]),'unit_price':num(m[4]),'amount':num(m[5]),'page':line['page'],'bbox':line['bbox']})
 if not doc['fields']: doc['warnings'].append('No supported labelled fields found. Review the document layout manually.')
 if doc['type']=='unknown': doc['warnings'].append('Document type uncertain; automated comparison coverage is limited.')
 if not text.strip(): doc['warnings'].append('No readable text extracted.')
 if 'pdf' in locals(): pdf.close()
 return doc

def field(doc,key): return doc['fields'].get(key,{}).get('value')
def norm(s): return re.sub(r'[^a-z0-9]','',str(s or '').lower())
def evidence(doc, item, label):
 return {'document_id':doc['id'],'document_name':doc['name'],'page':item['page'],'bbox':item['bbox'],'label':label,'value':str(item.get('value',item.get('text',item.get('amount',''))))}

def investigate(docs):
 findings=[]
 def add(code,title,detail,refs,severity='medium',status='Detected inconsistency',action='Check the source documents and obtain clarification from the vendor.'):
  findings.append({'id':f'F{len(findings)+1:03}','code':code,'title':title,'explanation':detail,'severity':severity,'status':status,'evidence':refs,'next_action':action,'review_status':'open'})
 for d in docs:
  for obs in d['visual']:
   add('visual_outlier','Unusual numeric typography',obs['detail'],[evidence(d,obs,obs['method'])],status='Visual observation',action='Inspect the original and request the vendor-issued version. Typography alone does not prove alteration.')
  for item in d['items']:
   expected=round(item['quantity']*item['unit_price'],2)
   if abs(expected-item['amount'])>.02:
    add('line_arithmetic','Line amount does not reconcile',f"{item['sku']}: {item['quantity']:g} x {item['unit_price']:,.2f} = {expected:,.2f}, but the document lists {item['amount']:,.2f}.",[evidence(d,item,item['sku'])])
  if d['items'] and num(field(d,'subtotal')) is not None:
   total=round(sum(i['amount'] for i in d['items']),2)
   if abs(total-num(field(d,'subtotal')))>.02:
    add('subtotal_arithmetic','Subtotal differs from line amounts',f"Line amounts sum to {total:,.2f}; stated subtotal is {field(d,'subtotal')}.",[evidence(d,i,i['sku']) for i in d['items']]+[evidence(d,d['fields']['subtotal'],'Subtotal')])
  subtotal,tax,total=[num(field(d,k)) for k in ('subtotal','tax','total')]
  if all(v is not None for v in (subtotal,tax,total)) and abs(subtotal+tax-total)>.02:
   add('total_arithmetic','Total does not reconcile',f"Subtotal {subtotal:,.2f} plus stated tax {tax:,.2f} differs from total {total:,.2f}.",[evidence(d,d['fields'][k],k) for k in ('subtotal','tax','total')])
 # Compare only documents with an exact normalized vendor and PO. No cross-vendor pairing.
 for inv in [d for d in docs if d['type']=='invoice']:
  if not field(inv,'vendor') or not field(inv,'po_number'):
   inv['warnings'].append('Vendor and PO number are required to link an invoice to order/delivery records.')
  related=[d for d in docs if d['id']!=inv['id'] and norm(field(d,'vendor')) and norm(field(d,'vendor'))==norm(field(inv,'vendor')) and norm(field(d,'po_number')) and norm(field(d,'po_number'))==norm(field(inv,'po_number'))]
  for other in related:
   if field(inv,'currency') and field(other,'currency') and norm(field(inv,'currency'))!=norm(field(other,'currency')):
    inv['warnings'].append(f"Currency differs from {other['name']}; monetary comparisons skipped."); continue
   if other['type'] not in ('purchase_order','delivery_receipt'): continue
   for item in inv['items']:
    matches=[x for x in other['items'] if norm(x['sku'])==norm(item['sku'])]
    if len(matches)!=1: continue
    ref=matches[0]; refs=[evidence(inv,item,f"Invoice {item['sku']}"),evidence(other,ref,f"{other['type'].replace('_',' ')} {item['sku']}")]
    if other['type']=='purchase_order' and abs(item['unit_price']-ref['unit_price'])>.02:
     add('price_mismatch','Invoice price differs from purchase order',f"{item['sku']}: invoiced unit price {item['unit_price']:,.2f}; purchase order price {ref['unit_price']:,.2f}. Difference on {item['quantity']:g} invoiced units: {item['quantity']*(item['unit_price']-ref['unit_price']):,.2f}.",refs,'high',action='Verify an approved price amendment before releasing payment.')
    if other['type']=='delivery_receipt' and item['quantity']>ref['quantity']:
     add('quantity_mismatch','Invoice quantity exceeds recorded receipt',f"{item['sku']}: {item['quantity']:g} units invoiced and {ref['quantity']:g} received in this receipt. Difference: {item['quantity']-ref['quantity']:g}. Other receipts or advance-billing terms may explain this.",refs,'high',action='Check other delivery receipts and approved billing terms. This comparison covers only the uploaded receipt.')
  vendors=[d for d in docs if d['type']=='vendor_record' and norm(field(d,'vendor')) and norm(field(d,'vendor'))==norm(field(inv,'vendor'))]
  for master in vendors:
   a,b=field(inv,'account'),field(master,'account')
   if a and b and norm(a)!=norm(b):
    add('bank_change','Payment account differs from vendor record',f"Invoice account ending {a[-4:]} differs from the uploaded vendor record ending {b[-4:]}. A legitimate bank change is possible.",[evidence(inv,inv['fields']['account'],'Invoice account'),evidence(master,master['fields']['account'],'Approved vendor account')],'high',action='Confirm the account change using a previously trusted vendor contact and approval process.')
 for i,d in enumerate(docs):
  for prior in docs[:i]:
   if d['sha256']==prior['sha256']:
    a=d['pages'][0]; b=prior['pages'][0]
    add('duplicate','Identical document uploaded twice','SHA-256 hashes match byte for byte. Duplicate upload does not establish duplicate payment.',[{'document_id':x['id'],'document_name':x['name'],'page':1,'bbox':[0,0,x['pages'][0]['width'],80],'label':'Identical bytes','value':x['sha256']} for x in (prior,d)],status='Confirmed observation'); break
   elif d['type']==prior['type']=='invoice' and field(d,'invoice_number') and norm(field(d,'invoice_number'))==norm(field(prior,'invoice_number')) and norm(field(d,'vendor'))==norm(field(prior,'vendor')):
    add('invoice_collision','Invoice number appears on different files','Same vendor and invoice number, but different file hashes. This may be a revision. Compare versions before deciding.',[evidence(x,x['fields']['invoice_number'],'Invoice number') for x in (prior,d)])
 # Connect findings that cite overlapping regions in the same source page.
 for finding in findings:
  related=[]
  for other in findings:
   if other is finding: continue
   shared=False
   for a in finding['evidence']:
    for b in other['evidence']:
     if (a['document_id'],a['page'])!=(b['document_id'],b['page']): continue
     x,y,x2,y2=a['bbox']; u,v,u2,v2=b['bbox']
     inter=max(0,min(x2,u2)-max(x,u))*max(0,min(y2,v2)-max(y,v))
     area=min((x2-x)*(y2-y),(u2-u)*(v2-v))
     if area>0 and inter/area>.4: shared=True
   if shared: related.append(other['id'])
  finding['related_findings']=related
 coverage=[]
 for typ,label in [('invoice','Invoice'),('purchase_order','Purchase order'),('delivery_receipt','Delivery receipt'),('vendor_record','Vendor record')]:
  if not any(d['type']==typ for d in docs): coverage.append(label+' missing: related checks cannot run.')
 return findings,coverage

def run_case(paths, dest:Path, names=None):
 dest.mkdir(parents=True,exist_ok=True)
 docs=[]; failures=[]; audit=[]
 def log(event): audit.append({'at':datetime.now(timezone.utc).isoformat(),'event':event})
 log(f'Investigation started with {len(paths)} submitted files.')
 for index,p in enumerate(paths):
  name=(names or [Path(x).name for x in paths])[index]
  log(f'Document submitted: {name}.')
  try:
   doc=extract_document(Path(p),dest,(names or [None]*len(paths))[index]); docs.append(doc)
   log(f"Extracted {doc['id']} ({name}): {len(doc['pages'])} pages, {len(doc['fields'])} fields, {len(doc['items'])} item rows; type {doc['type']}; SHA-256 {doc['sha256']}.")
  except Exception as exc:
   failures.append({'name':name,'error':str(exc)}); log(f'Processing failed for {name}: {exc}')
 findings,coverage=investigate(docs)
 log(f'Contextual and visual analysis completed: {len(findings)} findings; {len(coverage)} missing-document coverage warnings.')
 for finding in findings:
  log(f"Recorded {finding['id']} ({finding['code']}): {len(finding['evidence'])} evidence references; status {finding['status']}.")
 return {'id':dest.name,'created_at':audit[0]['at'],'documents':docs,'failures':failures,'findings':findings,'coverage_warnings':coverage,'engine':'Local OCR + document classifier + evidence rules','audit':audit}
