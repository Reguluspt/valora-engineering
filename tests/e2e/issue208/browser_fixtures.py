"""Create new browser identities in the independent #208 database only."""
import json
import os
import sys
import uuid
from sqlalchemy import text
from app.db import SessionLocal
from acceptance import seed

assert os.environ["POSTGRES_DB"] == "valora_issue208"
if len(sys.argv) == 3 and sys.argv[1] == "--bump-project":
    project_id = uuid.UUID(sys.argv[2])
    with SessionLocal() as db:
        result = db.execute(text("update projects set row_version=row_version+1 where id=:id and code like 'ISSUE208-%'"), {"id": project_id})
        assert result.rowcount == 1
        db.commit()
else:
    fixtures = {name: seed(permission=name != "viewer") for name in ("normal", "lost", "viewer", "stale")}
    print(json.dumps(fixtures, default=str))
