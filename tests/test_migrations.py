import os

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy import text

import app as chat_app
from dbModel import db

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'migrations')


def test_models_match_migrations(flask_app):
    """migrations/ 跑完之後的 schema 必須和 dbModel.py 的定義一致（欄位型別、長度、unique）。"""
    with flask_app.app_context():
        db.drop_all()
        try:
            upgrade(directory=MIGRATIONS_DIR)
            with db.engine.connect() as conn:
                diff = compare_metadata(MigrationContext.configure(conn), db.metadata)
            assert diff == []
        finally:
            db.drop_all()
            with db.engine.begin() as conn:
                conn.execute(text('DROP TABLE IF EXISTS alembic_version'))


def test_migrate_uses_batch_mode_for_sqlite():
    # SQLite 不支援大部分 ALTER TABLE，autogenerate 必須產生 batch_alter_table
    # （migrations/env.py 就是從這裡讀 configure_args）
    assert chat_app.app.extensions['migrate'].configure_args['render_as_batch'] is True
