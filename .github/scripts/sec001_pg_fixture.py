"""Run the disposable SEC-001 PostgreSQL phases and reject incomplete pytest evidence."""

import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

import psycopg
from psycopg import sql


BACKEND = Path(__file__).resolve().parents[2] / "backend"
SEC_FILES = [
    "tests/test_document_engine_tenant_postgresql.py",
    "tests/test_document_engine_migration_postgresql.py",
]
T1_FILES = {
    "tests/test_document_engine_api.py",
    "tests/test_document_engine_persistence.py",
    "tests/test_s5_acceptance.py",
}
SELECTOR = "tenant_route or secondary_reference or inconsistent_lineage or legacy_references"
MARKER = "VALORA SEC-001 disposable synthetic"
LABEL = "valora.sec001.fixture"


def run_tests(name, arguments, env, collect=False):
    destination = Path(env["RUNNER_TEMP"]) / "valora-sec001-results"
    destination.mkdir(exist_ok=True)
    report = destination / f"{name}.json"
    if report.exists():
        raise RuntimeError(f"Refusing to reuse pytest evidence: {name}")
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "_pytest", str(report), *arguments],
        cwd=BACKEND, env=env, check=True,
    )
    result = json.loads(report.read_text(encoding="utf-8"))
    nodes = result["collected"]
    if not nodes or len(nodes) != len(set(nodes)):
        raise RuntimeError(f"Empty or duplicate pytest collection: {name}")
    if any(row["outcome"] in {"failed", "skipped"} or row["xfail"]
           for row in result["reports"]):
        raise RuntimeError(f"Failed, skipped or expected-failure tests: {name}")
    if not collect:
        passed = [row["nodeid"] for row in result["reports"]
                  if row["when"] == "call" and row["outcome"] == "passed"]
        if (set(passed) != set(nodes) or len(passed) != len(nodes)
                or any(row["outcome"] in {"failed", "skipped"} or row["xfail"]
                       for row in result["reports"])):
            raise RuntimeError(f"Incomplete, failed or skipped tests: {name}")
    print(json.dumps({"phase": name, "collected": len(nodes),
                      "PASS": 0 if collect else len(nodes), "FAIL": 0, "SKIP": 0}), flush=True)
    return nodes


def pytest_child(report_path, arguments):
    import pytest

    class Evidence:
        def __init__(self):
            self.collected = []
            self.reports = []

        def pytest_collection_finish(self, session):
            self.collected = [item.nodeid for item in session.items]

        def pytest_collectreport(self, report):
            if report.failed or report.skipped:
                self.reports.append({"nodeid": report.nodeid, "when": "collect",
                                     "outcome": report.outcome, "xfail": False})

        def pytest_runtest_logreport(self, report):
            self.reports.append({
                "nodeid": report.nodeid, "when": report.when,
                "outcome": report.outcome, "xfail": bool(getattr(report, "wasxfail", False)),
            })

    evidence = Evidence()
    code = pytest.main(["-pno:cacheprovider", "-vv", "-rs", "--tb=short", *arguments],
                       plugins=[evidence])
    Path(report_path).write_text(json.dumps({
        "exit_code": int(code), "collected": evidence.collected, "reports": evidence.reports,
    }, indent=2) + "\n", encoding="utf-8")
    return int(code)


def regression():
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    arguments = [f"--ignore={name}" for name in SEC_FILES]
    nodes = run_tests("regression", arguments, env)
    t1 = [node for node in nodes if node.split("::", 1)[0] in T1_FILES]
    if not t1:
        raise RuntimeError("Missing Document Engine compatibility tests")
    print(json.dumps({"phase": "T1", "PASS": len(t1), "FAIL": 0, "SKIP": 0}), flush=True)


def fixture_connection():
    container = os.environ["VALORA_SEC001_FIXTURE_CONTAINER"]
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise RuntimeError("Expected the exact new disposable service container ID")
    info = json.loads(subprocess.check_output(
        ["docker", "inspect", container], text=True,
    ))[0]
    if (info["Id"] != container or not info["State"]["Running"]
            or info["Config"].get("Labels", {}).get(LABEL) != "true"
            or info["Config"]["Image"] != "postgres:16"):
        raise RuntimeError("SEC-001 fixture container identity does not match")
    internal_port = os.environ.get("VALORA_SEC001_FIXTURE_INTERNAL_PORT", "5432")
    if internal_port not in {"5432", "55432"}:
        raise RuntimeError("Unexpected disposable service port")
    expected_system = subprocess.check_output([
        "docker", "exec", container, "psql", "-X", "-U", "sec001_bootstrap",
        "-p", internal_port, "-d", "postgres", "-Atc",
        "SELECT system_identifier FROM pg_control_system()",
    ], text=True).strip()
    connection = psycopg.connect(
        host="127.0.0.1", port=55432, dbname="postgres", user="sec001_bootstrap",
        password="sec001_synthetic_bootstrap", autocommit=True,
    )
    try:
        version, system = connection.execute(
            "SELECT current_setting('server_version_num')::int, "
            "system_identifier::text FROM pg_control_system()"
        ).fetchone()
        if not 160000 <= version < 170000 or system != expected_system:
            raise RuntimeError("Loopback connection is not the verified PostgreSQL16 fixture")
        extra = connection.execute(
            "SELECT datname FROM pg_database "
            "WHERE datname NOT IN ('postgres', 'template0', 'template1')"
        ).fetchall()
        if extra:
            raise RuntimeError("Disposable PostgreSQL is not fresh; refusing to provision")
        return connection
    except BaseException:
        connection.close()
        raise


def provision():
    app_password, migrator_password = secrets.token_hex(24), secrets.token_hex(24)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for password in (app_password, migrator_password):
            print(f"::add-mask::{password}", flush=True)
    with fixture_connection() as connection:
        for role, password in (("sec001_app", app_password), ("sec001_migrator", migrator_password)):
            connection.execute(sql.SQL(
                "CREATE ROLE {} LOGIN PASSWORD {} "
                "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
            ).format(sql.Identifier(role), sql.Literal(password)))
        for database in ("valora_sec001_stage1", "valora_sec001_migration",
                         "valora_sec001_migration_owner"):
            name = sql.Identifier(database)
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER sec001_migrator").format(name))
            connection.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(name))
            connection.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(name, sql.Literal(MARKER)))
        connection.execute("GRANT CONNECT ON DATABASE valora_sec001_stage1 TO sec001_app")
    with psycopg.connect(
        host="127.0.0.1", port=55432, dbname="valora_sec001_stage1",
        user="sec001_migrator", password=migrator_password,
    ) as connection:
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.execute("GRANT USAGE ON SCHEMA public TO sec001_app")
        connection.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sec001_app"
        )
        connection.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO sec001_app"
        )
    return app_password, migrator_password


def security():
    app_password, migrator_password = provision()
    env = {
        **os.environ, "PYTHONDONTWRITEBYTECODE": "1",
        "POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "55432",
        "POSTGRES_DB": "valora_sec001_stage1", "POSTGRES_USER": "sec001_app",
        "POSTGRES_PASSWORD": app_password, "VALORA_SEC001_DISPOSABLE_PG": "1",
        "VALORA_SEC001_MIGRATOR_PASSWORD": migrator_password,
        "VALORA_ENV": "local", "BACKEND_CORS_ORIGINS": "http://localhost:5173",
    }
    env.pop("TEST_DATABASE_URL", None)
    migrator = {**env, "POSTGRES_USER": "sec001_migrator", "POSTGRES_PASSWORD": migrator_password}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                   cwd=BACKEND, env=migrator, check=True)
    expected = run_tests("SEC-collection", ["--collect-only", *SEC_FILES], env, collect=True)
    t2 = run_tests("T2", ["-k", SELECTOR, SEC_FILES[0]], env)
    t3 = run_tests("T3", ["-k", f"not ({SELECTOR})", *SEC_FILES], env)
    if set(t2) & set(t3) or set(t2 + t3) != set(expected):
        raise RuntimeError("SEC-001 phase union differs from full security collection")
    for number in range(1, 18):
        for ownership in ("own", "foreign"):
            node = SEC_FILES[0] + f"::test_tenant_route[r{number:02d}-{ownership}]"
            if node not in t2:
                raise RuntimeError(f"Missing mandatory tenant route: {node}")
    destination = Path(env["RUNNER_TEMP"]) / "valora-sec001-results"
    regression_result = json.loads((destination / "regression.json").read_text(encoding="utf-8"))
    general = regression_result["collected"]
    complete = run_tests("full-collection", ["--collect-only"], env, collect=True)
    if set(general) & set(expected) or set(general + expected) != set(complete):
        raise RuntimeError("Full backend collection differs from executed phase union")
    summary = {
        "backend_unique_PASS": len(complete), "FAIL": 0, "SKIP": 0,
        "T2_PASS": len(t2), "T3_PASS": len(t3), "tenant_route_nodes": 34,
        "PostgreSQL": 16, "app_role": "sec001_app", "migrator_role": "sec001_migrator",
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    os.chdir(BACKEND)
    if sys.argv[1] == "_pytest":
        raise SystemExit(pytest_child(sys.argv[2], sys.argv[3:]))
    if sys.argv[1] == "regression":
        regression()
    elif sys.argv[1] == "security":
        security()
    else:
        raise SystemExit("Expected regression or security")
