"""Bounded dependency checks, separate from process liveness."""
import os
from pathlib import Path
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
import httpx
from db.database import engine
from db.models import SchemaMigration
from db.migrate import REVISION


def check_dependencies():
    dependencies={}
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
            tables=set(inspect(connection).get_table_names())
            expected={'run_artifacts','recommendation_records','governance_records','human_review_records','schema_migrations'}
            revision=connection.execute(select(SchemaMigration.revision).where(SchemaMigration.revision==REVISION)).scalar_one_or_none() if 'schema_migrations' in tables else None
            dependencies['database']={'ready':expected<=tables and revision==REVISION,
                                      'schema_revision':revision,'missing_tables':sorted(expected-tables)}
    except SQLAlchemyError:
        dependencies['database']={'ready':False,'reason':'unavailable_or_schema_not_ready'}
    try:
        with httpx.Client(timeout=3,trust_env=False) as client:
            response=client.get(os.getenv('OLLAMA_HOST','http://localhost:11434').rstrip('/')+'/api/tags')
            response.raise_for_status()
            models={m['name'] for m in response.json().get('models',[])}
            model=os.getenv('OLLAMA_MODEL','medgemma1.5:4b')
            dependencies['ollama']={'ready':model in models,'configured_model':model}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        dependencies['ollama']={'ready':False,'reason':'unavailable_or_invalid_response'}
    ready=all(v['ready'] for v in dependencies.values())
    return {'status':'ready' if ready else 'not_ready','dependencies':dependencies,
            'scope':'Dependency availability, not clinical readiness.'}
