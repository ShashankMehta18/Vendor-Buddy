"""Reproduce synthetic demonstration results. Not a real-world accuracy benchmark."""
import json, sys, tempfile, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.engine import run_case
ROOT=Path(__file__).resolve().parents[1]
def main():
 truth=json.loads((ROOT/'data/samples/ground_truth.json').read_text()); results=[]
 for scenario,expected in truth.items():
  with tempfile.TemporaryDirectory() as tmp:
   start=time.perf_counter(); c=run_case(sorted((ROOT/'data/samples'/scenario).iterdir()),Path(tmp)); elapsed=time.perf_counter()-start
   actual=sorted({f['code'] for f in c['findings']}); results.append({'scenario':scenario,'documents':len(c['documents']),'expected_categories':sorted(expected),'observed_categories':actual,'matches_expected':actual==sorted(expected),'findings':len(c['findings']),'evidence_references':sum(len(f['evidence']) for f in c['findings']),'elapsed_seconds':round(elapsed,3),'processing_failures':len(c['failures'])})
 out={'scope':'Four synthetic, template-controlled demonstration cases. Results do not estimate real-world accuracy. Timing depends on machine.','results':results,'matching_cases':sum(x['matches_expected'] for x in results),'total_cases':len(results)}
 (ROOT/'docs/evaluation.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
