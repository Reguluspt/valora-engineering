"""Round-trip only an independently created #208 PostgreSQL database."""
import os
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

assert os.environ["POSTGRES_DB"] == "valora_issue208"
source = make_url(os.environ["TEST_DATABASE_URL"])
name = "issue208_migration_" + uuid.uuid4().hex
assert name.startswith("issue208_migration_") and len(name) == 51
admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as connection:
    connection.execute(text(f'CREATE DATABASE "{name}"'))
try:
    env = {**os.environ, "POSTGRES_DB": name}
    check = create_engine(source.set(database=name))
    for target in ("head", "e8f9a0b1c2d3", "head"):
        direction = "downgrade" if target == "e8f9a0b1c2d3" else "upgrade"
        subprocess.run([sys.executable, "-m", "alembic", direction, target], env=env, check=True)
        with check.connect() as connection:
            assert connection.scalar(text("select version_num from alembic_version")) == ("e8f9a0b1c2d3" if direction == "downgrade" else "f9a0b1c2d3e4")
            found = connection.scalar(text("select count(*) from information_schema.tables where table_schema='public' and table_name like 'quotation_document_import_%'"))
            assert found == (0 if direction == "downgrade" else 2)
            roles = list(connection.execute(text("select code,permissions::text from roles order by code")))
            if target == "head" and "first_roles" not in locals():
                first_roles = roles
            else:
                assert roles == first_roles
            assert connection.scalar(text("select count(*) from document_revisions")) == 0
    check.dispose()
    print("PASS: upgrade/downgrade/upgrade; one head; owned tables only; role grants unchanged; no historical revision backfill")
finally:
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()
