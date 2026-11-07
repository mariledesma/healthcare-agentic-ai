"""Runs only in an isolated temporary SQLite database, never the user's PostgreSQL."""
import copy
import json
import os
from pathlib import Path
import uuid
from unittest.mock import patch

assert os.environ.get('DATABASE_URL','').startswith('sqlite'), 'Storage contract tests require isolated SQLite'
from sqlalchemy import select, func, inspect
from fastapi.testclient import TestClient
from db.database import engine, SessionLocal
from db.models import PatientCase, PipelineRun, RunArtifact, RecommendationRecord, GovernanceRecord, HumanReviewRecord
from db.migrate import migrate
from db.repository import save_pipeline_run
from db.review_repository import record_review, get_run, StorageConflict
from api.main import app
import run_prototype

root=Path(__file__).resolve().parents[1]
assert migrate()['status']=='applied'
assert migrate()['status']=='already_applied'
assert len(inspect(engine).get_table_names())==9

with patch.object(run_prototype,'AuditLogger'):
    result=run_prototype.run_pipeline(root/'data/synthetic/case_007_med_review.json',use_llm=False,persist=False)
record=result['input_reader']['patient_record']
result.pop('database')
first=save_pipeline_run(record,result,'synthetic-test')
second=save_pipeline_run(record,result,'synthetic-test')
assert first['run_id']!=second['run_id']
assert first['recommendations_saved']==1 and first['governance_saved']==1
with SessionLocal() as session:
    assert session.scalar(select(func.count()).select_from(PatientCase))==1
    assert session.scalar(select(func.count()).select_from(PipelineRun))==2
    assert session.scalar(select(func.count()).select_from(RecommendationRecord))==2
    assert session.scalar(select(func.count()).select_from(RunArtifact))==2

# A constraint/consistency failure must roll back the case upsert and every run row.
bad=copy.deepcopy(result)
bad['governance']['results']=[]
try: save_pipeline_run(record,bad,'should-rollback')
except ValueError: pass
else: raise AssertionError('Inconsistent governance was saved')
with SessionLocal() as session:
    assert session.scalar(select(func.count()).select_from(PipelineRun))==2
    assert session.get(PatientCase,record['case_id']).source_file=='synthetic-test'

proposal=result['recommendation_agent']['recommendations'][0]
request={'run_id':first['run_id'],'request_id':str(uuid.uuid4()),'case_id':record['case_id'],
         'recommendation_id':proposal['recommendation_id'],'task_id':proposal['task_id'],
         'action':proposal['action'],'decision':'flagged','reviewer_role':'Automated Storage Test','notes':'Synthetic test only'}
saved=record_review(request)
assert saved['replayed'] is False
assert record_review(request)['review_id']==saved['review_id']
assert record_review(request)['replayed'] is True
changed={**request,'decision':'approved'}
try: record_review(changed)
except StorageConflict: pass
else: raise AssertionError('Idempotency conflict not rejected')
for field,value in [('run_id',second['run_id']),('case_id','forged'),('action','forged')]:
    mismatch={**request,'request_id':str(uuid.uuid4()),field:value}
    # A recommendation identity may legitimately repeat across runs, but decisions
    # remain bound to the explicitly requested run.
    if field=='run_id':
        other=record_review(mismatch)
        assert other['run_id']==second['run_id']
    else:
        try: record_review(mismatch)
        except StorageConflict: pass
        else: raise AssertionError('Forged metadata accepted')

client=TestClient(app)
assert client.get('/runs?limit=0').status_code==422
assert client.get('/runs?limit=1').json()['total']==2
assert client.get('/runs/'+str(uuid.uuid4())).status_code==404
restored=client.get('/runs/'+first['run_id']).json()
assert restored['integrity']=='verified' and restored['reviews'][0]['review_id']==saved['review_id']
assert restored['result']['database']['run_id']==first['run_id']
assert client.post('/reviews',json={k:v for k,v in request.items() if k!='run_id'}).status_code==422
with patch('api.storage_routes.AuditLogger',side_effect=OSError('disk full')):
    response=client.post('/reviews',json={**request,'request_id':str(uuid.uuid4()),'decision':'rejected'})
    assert response.status_code==200
    assert response.json()['audit_status']=='file_write_failed_database_saved'
    assert response.json()['execution_performed'] is False

# A blocked saved recommendation cannot be approved, but can be flagged.
from research.provenance import seal
blocked=copy.deepcopy(result)
blocked['governance']['results'][0]['policy']['policy_status']='forbidden'
blocked['governance']['results'][0]['approval']['approval_status']='blocked'
blocked['provenance']=seal(record,blocked['integrity_artifacts'],{'mode':'blocked_storage_fixture'})
blocked_run=save_pipeline_run(record,blocked,'blocked-test-fixture')
blocked_request={**request,'run_id':blocked_run['run_id'],'request_id':str(uuid.uuid4()),'decision':'approved'}
try: record_review(blocked_request)
except StorageConflict: pass
else: raise AssertionError('Blocked recommendation was approved')
assert record_review({**blocked_request,'request_id':str(uuid.uuid4()),'decision':'flagged'})['decision']=='flagged'

# Tampering with normalized proposals cannot bypass the immutable artifact.
with SessionLocal() as session:
    row=session.scalar(select(RecommendationRecord).where(RecommendationRecord.run_id==first['run_id']))
    forged=copy.deepcopy(row.proposal);forged['owner_role']='forged';row.proposal=forged;session.commit()
try: record_review({**request,'request_id':str(uuid.uuid4())})
except StorageConflict: pass
else: raise AssertionError('Normalized proposal tampering accepted')

with SessionLocal() as session:
    artifact=session.get(RunArtifact,first['run_id'])
    changed=copy.deepcopy(artifact.payload);changed['condition']='tampered';artifact.payload=changed;session.commit()
assert client.get('/runs/'+first['run_id']).status_code==409
print(json.dumps({'checks':'passed','tables':9,'coverage':['additive/idempotent migration','transaction rollback','separate runs','normalized persistence','run-bound review','retry idempotency','metadata forgery','history restoration','audit failure durability','artifact tampering']}))
