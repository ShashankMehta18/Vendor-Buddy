"""Evidence-backed PDF dossier. Generated from the investigation JSON."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from PIL import Image as PILImage, ImageDraw

def dossier(case, folder:Path):
 output=BytesIO(); styles=getSampleStyleSheet()
 styles.add(ParagraphStyle(name='SmallNote',parent=styles['BodyText'],fontSize=8,leading=11,textColor=colors.HexColor('#52616b')))
 styles['Title'].textColor=colors.HexColor('#142b32'); styles['Heading2'].textColor=colors.HexColor('#0a7460')
 def p(s,style='BodyText'): return Paragraph(escape(str(s)),styles[style])
 brand_header=Table([[Image(str(Path(__file__).parent/'static/vendor-buddy-logo.png'),width=28,height=28),p('VENDOR BUDDY / DILIGENCE','SmallNote')]],colWidths=[38,452]); brand_header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(-1,-1),'LEFT')]))
 story=[brand_header,p('Vendor payment investigation','Title'),p(f"Case {case['id']} | {case['created_at']}",'SmallNote'),Spacer(1,15),p('Investigation summary','Heading2'),p(f"{len(case['documents'])} documents processed. {len(case['findings'])} findings require review. The system records observations and discrepancies. It does not establish fraud or approve payments."),Spacer(1,10)]
 for warning in case['coverage_warnings']: story.append(p(warning,'SmallNote'))
 for failure in case['failures']: story.append(p(f"Processing failure: {failure['name']}: {failure['error']}",'SmallNote'))
 story += [p('Document overview and extracted information','Heading2')]
 for d in case['documents']:
  block_start=len(story)
  story += [p(f"{d['name']} ({d['type'].replace('_',' ')})",'Heading3'),p(f"SHA-256: {d['sha256']}",'SmallNote'),p('Sources: '+', '.join(f"page {pg['number']}: {pg['method']}" for pg in d['pages']),'SmallNote')]
  rows=[[p('Field','SmallNote'),p('Value','SmallNote'),p('Source / extraction confidence','SmallNote')]]
  for k,v in d['fields'].items(): rows.append([p(k.replace('_',' '),'SmallNote'),p(v['value'],'SmallNote'),p(f"p{v['page']} / "+(f"OCR {v['confidence']:.0%}" if v['confidence'] is not None else 'PDF text, unavailable'),'SmallNote')])
  table=Table(rows,colWidths=[100,190,200]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf3ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#e1e6e4'))])); story += [table,Spacer(1,8)]
  if d['items']:
   story.append(p('Line items and document structure','Heading3'))
   items=[[p(x,'SmallNote') for x in ('SKU / description','Quantity','Unit price','Amount / source')]]
   for item in d['items']:
    items.append([p(item['sku']+' / '+item['description'],'SmallNote'),p(f"{item['quantity']:g}",'SmallNote'),p(f"{item['unit_price']:,.2f}",'SmallNote'),p(f"{item['amount']:,.2f} / p{item['page']}",'SmallNote')])
   item_table=Table(items,colWidths=[210,65,85,130]); item_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf3ef')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#e1e6e4'))]))
   story += [item_table,Spacer(1,8)]
  for w in d['warnings']: story.append(p(w,'SmallNote'))
  story[block_start:]=[KeepTogether(story[block_start:])]
 story += [PageBreak(),p('Contextual analysis and visual forensic findings','Heading2')]
 docs={d['id']:d for d in case['documents']}
 if not case['findings']: story.append(p('No implemented checks produced a finding. This is not an authenticity certificate. Review extraction and coverage limitations.'))
 for finding in case['findings']:
  block_start=len(story)
  story += [p(f"{finding['id']} / {finding['title']}",'Heading3'),p(f"{finding['severity'].upper()} / {finding['status']}",'SmallNote'),p(finding['explanation']),p('Detection confidence: uncalibrated. Priority is a review category, not a fraud probability. Consult the source extraction confidence and original evidence.','SmallNote'),p('Related findings sharing source regions: '+(', '.join(finding.get('related_findings',[])) or 'none'),'SmallNote'),p('Next verification: '+finding['next_action']),Spacer(1,7)]
  for ev in finding['evidence']:
   d=docs[ev['document_id']]; pg=d['pages'][ev['page']-1]
   im=PILImage.open(folder/pg['image']).convert('RGB'); sx=im.width/pg['width']; sy=im.height/pg['height']; x0,y0,x1,y1=ev['bbox']
   bounds=[max(0,int((x0-15)*sx)),max(0,int((y0-6)*sy)),min(im.width,int((x1+15)*sx)),min(im.height,int((y1+6)*sy))]
   im=im.crop(bounds); draw=ImageDraw.Draw(im); draw.rectangle([max(0,x0*sx-bounds[0]),max(0,y0*sy-bounds[1]),min(im.width-1,x1*sx-bounds[0]),min(im.height-1,y1*sy-bounds[1])],outline='#c87722',width=2)
   buf=BytesIO(); im.save(buf,format='PNG'); buf.seek(0)
   w=min(475,im.width); h=im.height*w/im.width
   story += [p(f"Evidence: {ev['document_name']}, page {ev['page']} / {ev['label']}",'SmallNote'),Image(buf,width=w,height=min(h,140)),Spacer(1,7)]
  story[block_start:]=[KeepTogether(story[block_start:])]
 story += [p('Methods, uncertainty and limitations','Heading2'),p('Digital PDFs use embedded text and span metadata. Scanned pages use Tesseract English OCR. A small TF-IDF logistic classifier and explicit headings identify document types. Numeric typography observations compare monetary spans; intentional emphasis can trigger false positives. Structured rules compare extracted evidence. Optional hosted LLM narration, when enabled, receives extracted findings only and cannot create new detections.'),p('Supported extraction targets English labelled vendor documents and SKU rows with quantity, unit price and amount. General layouts, handwriting, signature authentication, legal tax validation and external bank verification are unsupported. Partial deliveries, revisions, outdated vendor records, currency differences and OCR errors require human review. Demonstration files are fictional and the tests are not a production benchmark.'),p('Audit trail','Heading2')]
 for event in case['audit']: story.append(p(event['at']+' '+event['event'],'SmallNote'))
 def footer(canvas,doc):
  canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#52616b')); canvas.drawString(42,25,'Vendor Buddy / Human review required'); canvas.drawRightString(550,25,str(doc.page))
 SimpleDocTemplate(output,pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=40,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
 return output.getvalue()
