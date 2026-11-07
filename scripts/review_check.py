"""Read-only review checks. Tests use an isolated temporary database."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import httpx
from research import service
from research.provenance import implementation_hashes

ROOT=Path(__file__).resolve().parents[1]


def run(live=False):
    checks={}
    for name,args in [('tests',['-m','unittest','discover','-s','tests','-p','test_*.py']),
                      ('frozen_challenge',['-m','synthesis.freeze_challenge','--verify','data/challenge/discharge_approved_v1'])]:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,text=True,capture_output=True,timeout=120)
        checks[name]={'passed':result.returncode==0,'summary':(result.stdout+result.stderr).strip()[-2000:]}
    try:
        name,files=service.load_bundle()
        checks['frozen_research_bundle']={'passed':True,'bundle':name}
        checks['experiment_source_matches']={'passed':implementation_hashes()==files['report.json']['implementation_sha256']}
    except (TypeError,ValueError,OSError,KeyError):
        checks['frozen_research_bundle']={'passed':False,'reason':'Missing or invalid selected bundle'}
    if live:
        with httpx.Client(timeout=12,trust_env=False) as client:
            for name,route in [('liveness','/health'),('readiness','/ready'),('run_history','/runs?limit=1')]:
                try:
                    response=client.get('http://127.0.0.1:8000'+route)
                    checks[name]={'passed':response.status_code==200,'http_status':response.status_code,'result':response.json()}
                except (httpx.HTTPError,ValueError): checks[name]={'passed':False,'reason':'Local service unavailable'}
    return {'created_at':datetime.now(timezone.utc).isoformat(),'python':sys.version.split()[0],
            'passed':all(c['passed'] for c in checks.values()),'checks':checks,
            'scope':'Software and development artifact checks, not clinical validation.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Also check the running localhost API without creating runs')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output and args.output.exists(): raise SystemExit('Choose a fresh output file')
    report=run(args.live)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
