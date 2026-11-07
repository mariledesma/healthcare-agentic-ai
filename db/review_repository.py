"""Transactional run-bound review records and read-only run history."""
import copy
import uuid
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from db.database import SessionLocal
from db.models import PipelineRun, RunArtifact, RecommendationRecord, GovernanceRecord, HumanReviewRecord
from research.provenance import digest, verify


class StorageNotFound(Exception): pass
class StorageConflict(Exception): pass


def iso(value): return value.isoformat() if value else None


def review_json(row):
    return {'review_id':row.review_id,'request_id':row.request_id,'run_id':row.run_id,
            'recommendation_id':row.recommendation_id,'decision':row.decision,
            'review_status':{'approved':'human_approved','rejected':'human_rejected','flagged':'human_flagged'}[row.decision],
            'reviewer_role':row.reviewer_role,'notes':row.notes,'created_at':iso(row.created_at),
            'execution_performed':False}


def record_review(request):
    payload = copy.deepcopy(request)
    payload['request_id'] = str(payload['request_id'])
    payload['run_id'] = str(payload['run_id'])
    request_hash = digest(payload)
    with SessionLocal() as session:
        existing = session.scalar(select(HumanReviewRecord).where(HumanReviewRecord.request_id==payload['request_id']))
        if existing:
            if existing.request_sha256 != request_hash: raise StorageConflict('Request ID was already used for different review content')
            return {**review_json(existing), 'replayed':True}
        run = session.get(PipelineRun,payload['run_id'])
        if not run: raise StorageNotFound('Saved run not found')
        proposal = session.scalar(select(RecommendationRecord).where(
            RecommendationRecord.run_id==run.run_id, RecommendationRecord.recommendation_id==payload['recommendation_id']))
        outcome = session.scalar(select(GovernanceRecord).where(
            GovernanceRecord.run_id==run.run_id, GovernanceRecord.recommendation_id==payload['recommendation_id']))
        if not proposal or not outcome: raise StorageNotFound('Recommendation is not reviewable in this run; legacy runs may lack review records')
        for key, expected in [('case_id',run.case_id),('task_id',proposal.task_id),('action',proposal.proposal.get('action'))]:
            if payload.get(key) != expected: raise StorageConflict(f'{key} does not match the saved recommendation')
        artifact = session.get(RunArtifact,run.run_id)
        if not artifact or artifact.payload_sha256 != digest(artifact.payload):
            raise StorageConflict('Saved run artifact failed its integrity check')
        saved = artifact.payload
        if not verify(saved['provenance'],saved['input_reader']['patient_record'],saved['integrity_artifacts']):
            raise StorageConflict('Saved evidence failed its integrity check')
        saved_proposal = next((p for p in saved['recommendation_agent']['recommendations']
                               if p['recommendation_id']==proposal.recommendation_id),None)
        saved_outcome = next((o for o in saved['governance']['results']
                              if o['recommendation_id']==proposal.recommendation_id),None)
        if saved_proposal != proposal.proposal or saved_outcome != outcome.outcome:
            raise StorageConflict('Stored proposal or governance differs from the immutable run artifact')
        if payload['decision']=='approved' and (outcome.policy_status!='allowed' or outcome.approval_status=='blocked'):
            raise StorageConflict('A blocked or unpermitted recommendation cannot be approved')
        row = HumanReviewRecord(review_id=str(uuid.uuid4()),request_id=payload['request_id'],request_sha256=request_hash,
            run_id=run.run_id,recommendation_id=payload['recommendation_id'],decision=payload['decision'],
            reviewer_role=payload['reviewer_role'],notes=payload.get('notes'))
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(select(HumanReviewRecord).where(HumanReviewRecord.request_id==payload['request_id']))
            if not existing or existing.request_sha256 != request_hash:
                raise StorageConflict('Concurrent review request conflicts with this submission')
            return {**review_json(existing),'replayed':True}
        session.refresh(row)
        return {**review_json(row),'replayed':False}


def list_runs(limit=25,offset=0,case_id=None):
    with SessionLocal() as session:
        query=select(PipelineRun)
        count=select(func.count()).select_from(PipelineRun)
        if case_id:
            query=query.where(PipelineRun.case_id==case_id);count=count.where(PipelineRun.case_id==case_id)
        rows=session.scalars(query.order_by(PipelineRun.created_at.desc(),PipelineRun.run_id.desc()).limit(limit).offset(offset)).all()
        artifacts=set(session.scalars(select(RunArtifact.run_id).where(RunArtifact.run_id.in_([r.run_id for r in rows])))) if rows else set()
        return {'total':session.scalar(count),'limit':limit,'offset':offset,'runs':[
            {'run_id':r.run_id,'case_id':r.case_id,'model':r.llm_model,'status':r.status,
             'final_status':r.final_status,'created_at':iso(r.created_at),'has_full_artifact':r.run_id in artifacts} for r in rows]}


def get_run(run_id):
    with SessionLocal() as session:
        run=session.get(PipelineRun,str(run_id))
        if not run: raise StorageNotFound('Saved run not found')
        artifact=session.get(RunArtifact,run.run_id)
        reviews=session.scalars(select(HumanReviewRecord).where(HumanReviewRecord.run_id==run.run_id).order_by(HumanReviewRecord.created_at,HumanReviewRecord.review_id)).all()
        if not artifact:
            return {'run_id':run.run_id,'case_id':run.case_id,'legacy':True,'result':None,
                    'evaluation':run.evaluation,'reviews':[review_json(r) for r in reviews],
                    'message':'Legacy run has no full response artifact; rerun the case to create one.'}
        if digest(artifact.payload)!=artifact.payload_sha256: raise StorageConflict('Saved artifact failed its integrity check')
        payload=copy.deepcopy(artifact.payload)
        if not verify(payload['provenance'],payload['input_reader']['patient_record'],payload['integrity_artifacts']):
            raise StorageConflict('Saved evidence failed its integrity check')
        payload['database']={'status':'saved','run_id':run.run_id,'case_id':run.case_id}
        return {'run_id':run.run_id,'case_id':run.case_id,'legacy':False,'result':payload,
                'reviews':[review_json(r) for r in reviews],'integrity':'verified',
                'execution_performed':False}
