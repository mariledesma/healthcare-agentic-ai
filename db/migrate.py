"""Versioned additive schema initialization. Never drops or rewrites existing data."""
import hashlib
import json
from sqlalchemy import inspect, select
from sqlalchemy.schema import CreateTable, CreateIndex
from db.database import Base, engine
from db import models

REVISION = '2026_11_review_storage_v1'


def schema_checksum(connection):
    names = ('schema_migrations','run_artifacts','recommendation_records','governance_records','human_review_records')
    ddl = '\n'.join(str(CreateTable(Base.metadata.tables[name]).compile(dialect=connection.dialect)) for name in names)
    indexes = [index for name in names for index in Base.metadata.tables[name].indexes]
    indexes += list(Base.metadata.tables['pipeline_runs'].indexes)
    ddl += '\n' + '\n'.join(str(CreateIndex(index).compile(dialect=connection.dialect)) for index in sorted(indexes,key=lambda i:i.name))
    return hashlib.sha256(ddl.encode()).hexdigest()


def migrate():
    with engine.begin() as connection:
        if connection.dialect.name == 'postgresql':
            connection.exec_driver_sql('SELECT pg_advisory_xact_lock(68110601)')
        before = set(inspect(connection).get_table_names())
        # Existing tables are not altered. Later column changes require a new migration.
        Base.metadata.create_all(connection)
        for index in Base.metadata.tables['pipeline_runs'].indexes:
            index.create(connection, checkfirst=True)
        checksum = schema_checksum(connection)
        previous = connection.execute(select(models.SchemaMigration.checksum).where(models.SchemaMigration.revision==REVISION)).scalar_one_or_none()
        if previous and previous != checksum:
            raise ValueError('Recorded migration checksum differs; create a new migration instead of changing applied DDL')
        if not previous:
            connection.execute(models.SchemaMigration.__table__.insert().values(revision=REVISION,checksum=checksum))
        after = set(inspect(connection).get_table_names())
    return {'revision':REVISION,'status':'already_applied' if previous else 'applied',
            'created_tables':sorted(after-before), 'destructive_changes':False}


if __name__=='__main__': print(json.dumps(migrate(),indent=2))
