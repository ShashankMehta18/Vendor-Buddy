"""Reproducible fictional documents. Ground truth never enters the runtime engine."""
from pathlib import Path
import json, shutil
import pymupdf
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/'data/samples'

def make(path,kind,price=500,qty=100,account='001122334455',vendor='Aster Industrial Supplies',po='PO-2026-1042',font_outlier=False):
 path.parent.mkdir(parents=True,exist_ok=True)
 c=canvas.Canvas(str(path),pagesize=(595,842)); c.setTitle(kind+' | fictional demonstration')
 c.setFillColor(HexColor('#15352f')); c.rect(0,760,595,82,fill=1,stroke=0)
 c.setFillColor(HexColor('#ffffff')); c.setFont('Helvetica-Bold',23); c.drawString(42,797,kind)
 c.setFont('Helvetica',10); c.drawString(42,777,'ASTER INDUSTRIAL SUPPLIES / FICTIONAL DEMONSTRATION')
 c.setFillColor(HexColor('#203632')); y=724
 def row(text):
  nonlocal y
  c.setFont('Helvetica',11); c.drawString(42,y,text); y-=25
 row('Vendor: '+vendor)
 if kind=='APPROVED VENDOR RECORD':
  row('Vendor ID: VEN-1042'); row('Approved on: 2026-10-01'); row('Bank name: Example Commercial Bank'); row('Bank account: '+account); row('Status: Approved'); row('Currency: INR')
 else:
  row('PO number: '+po)
  if kind=='TAX INVOICE': row('Invoice number: INV-2026-071')
  row('Date: 2026-11-08'); row('Currency: INR')
  if kind=='DELIVERY RECEIPT': row('Delivery status: Complete'); row('Receipt number: GRN-2026-088')
  if kind=='TAX INVOICE': row('Bank name: Example Commercial Bank'); row('Bank account: '+account)
  row('Billing terms: Payment after recorded receipt')
  y-=15; c.setFillColor(HexColor('#edf3ef')); c.rect(38,y-10,519,32,fill=1,stroke=0); c.setFillColor(HexColor('#203632')); c.setFont('Helvetica-Bold',10)
  for x,label in [(42,'SKU / description'),(312,'Qty'),(372,'Unit price'),(485,'Amount')]: c.drawString(x,y,label)
  y-=42; c.setFont('Helvetica',11); c.drawString(42,y,'CAB-01  Industrial cable'); c.drawString(312,y,str(qty))
  c.drawString(372,y,f'{price:,.2f}')
  if font_outlier:
   c.setFillColor(HexColor('#fff3d6')); c.rect(478,y-4,80,23,fill=1,stroke=0); c.setFillColor(HexColor('#203632')); c.setFont('Courier-Bold',16)
  c.drawString(478,y,f'{qty*price:,.2f}'); c.setFont('Helvetica',11)
  y-=32; c.drawString(42,y,'ADP-02  Power adapter'); c.drawString(312,y,'10'); c.drawString(372,y,'200.00'); c.drawString(478,y,'2,000.00')
  y-=56; subtotal=qty*price+2000
  row('Subtotal: '+f'{subtotal:,.2f}'); row('Tax: 0.00'); row('Total: '+f'{subtotal:,.2f}')
  if kind=='TAX INVOICE': row('Payment terms: Within 30 days')
 c.setStrokeColor(HexColor('#d8e2dc')); c.line(42,90,553,90); c.setFont('Helvetica',9); c.setFillColor(HexColor('#687973')); c.drawString(42,72,'Fictional sample. No real vendor, bank account or transaction.'); c.drawString(42,55,'Tax amount is illustrative. This prototype does not validate tax law.'); c.save()

def generate():
 for scenario in ('clean','suspicious','scanned','duplicate'):
  d=BASE/scenario; d.mkdir(parents=True,exist_ok=True)
  make(d/'01-purchase-order.pdf','PURCHASE ORDER')
  make(d/'02-delivery-receipt.pdf','DELIVERY RECEIPT',qty=80 if scenario!='clean' else 100)
  make(d/'03-vendor-record.pdf','APPROVED VENDOR RECORD')
  make(d/'04-invoice.pdf','TAX INVOICE',price=650 if scenario!='clean' else 500,account='009988776655' if scenario!='clean' else '001122334455',font_outlier=scenario in ('suspicious','duplicate'))
  if scenario=='scanned':
   p=pymupdf.open(d/'04-invoice.pdf'); p[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(d/'04-invoice.png'); p.close(); (d/'04-invoice.pdf').unlink()
  if scenario=='duplicate': shutil.copyfile(d/'04-invoice.pdf',d/'05-invoice-copy.pdf')
 truth={'clean':[], 'suspicious':['price_mismatch','quantity_mismatch','bank_change','visual_outlier'], 'scanned':['price_mismatch','quantity_mismatch','bank_change'], 'duplicate':['price_mismatch','quantity_mismatch','bank_change','visual_outlier','duplicate']}
 (BASE/'ground_truth.json').write_text(json.dumps(truth,indent=2))
if __name__=='__main__': generate()
