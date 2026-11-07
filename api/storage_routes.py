"""Persistent history and append-only review endpoints for the local prototype."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from db.review_repository import record_review, get_run, list_runs, StorageConflict, StorageNotFound
from evaluation.audit_logger import AuditLogger
from pathlib import Path

router=APIRouter()


class ReviewRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    run_id: UUID
    request_id: UUID
    case_id: str = Field(min_length=1,max_length=50)
    recommendation_id: str = Field(min_length=1,max_length=250)
    task_id: str = Field(min_length=1,max_length=150)
    action: str = Field(min_length=1,max_length=2000)
    decision: Literal['approved','rejected','flagged']
    reviewer_role: str = Field(default='Research Reviewer',min_length=1,max_length=150)
    notes: str | None = Field(default=None,max_length=10000)


def storage_error(error):
    if isinstance(error,StorageNotFound): return HTTPException(status_code=404,detail=str(error))
    if isinstance(error,StorageConflict): return HTTPException(status_code=409,detail=str(error))
    return HTTPException(status_code=503,detail='Database unavailable or schema not ready; run python -m db.migrate')


@router.get('/runs')
def history(limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),case_id:str|None=Query(None,max_length=50)):
    try: return list_runs(limit,offset,case_id)
    except SQLAlchemyError as error: raise storage_error(error) from error


@router.get('/runs/{run_id}')
def detail(run_id:UUID):
    try: return get_run(str(run_id))
    except (StorageNotFound,StorageConflict,SQLAlchemyError) as error: raise storage_error(error) from error


@router.post('/reviews')
def review(request:ReviewRequest):
    data=request.model_dump(mode='json')
    try: saved=record_review(data)
    except (StorageNotFound,StorageConflict,SQLAlchemyError) as error: raise storage_error(error) from error
    # PostgreSQL is the durable source of truth. Audit-file failure never undoes a
    # committed review or turns it into a retry that creates a second decision.
    audit_status='already_recorded' if saved['replayed'] else 'written'
    if not saved['replayed']:
        try:
            AuditLogger(Path(__file__).resolve().parents[1]/'results/audit_logs').log(
                case_id=data['case_id'],module='HumanReview',action=data['action'],status=saved['review_status'],
                details={**saved,'execution_performed':False})
        except OSError:
            audit_status='file_write_failed_database_saved'
    return {'status':'success','run_id':data['run_id'],'case_id':data['case_id'],
            'recommendation_id':data['recommendation_id'],'task_id':data['task_id'],'action':data['action'],
            'human_review':saved,'audit_status':audit_status,'execution_performed':False,
            'message':'Research review decision saved. No clinical action was executed.'}
