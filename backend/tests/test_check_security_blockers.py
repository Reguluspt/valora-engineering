import os
import sys
import tempfile


def _import_checker():
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, backend_dir)
    import check_security
    return check_security


def test_hardcoded_slug_fails():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.ts"), "w", encoding="utf-8") as f:
            f.write('const x = "hd-98-gia-lai";')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for hard-coded slug"


def test_all_zero_uuid_fails():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.ts"), "w", encoding="utf-8") as f:
            f.write('const x = "00000000-0000-0000-0000-000000000000";')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for all-zero UUID"


def test_clean_source_passes():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.ts"), "w", encoding="utf-8") as f:
            f.write('const x = "normal-string";')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, f"Expected 0 issues for clean source, got {issues}"


def test_unbounded_read_blocked():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        # Create Excel import path scope
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('data = spool.read()')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for unbounded .read() in excel import scope"

        # Outside scope should be allowed
        other_dir = os.path.join(tmp, "app", "modules", "other")
        os.makedirs(other_dir, exist_ok=True)
        with open(os.path.join(other_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('data = spool.read()')
        m.check_security_baseline_and_blockers(tmp)
        # Note: issues_other will still be > 0 because we didn't clean/recreate tmp, but let's test isolation
        
def test_unbounded_read_allowed_outside_scope():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        other_dir = os.path.join(tmp, "app", "modules", "other")
        os.makedirs(other_dir, exist_ok=True)
        with open(os.path.join(other_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('data = spool.read()')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, "Expected unbounded .read() to be allowed outside of excel import scope"

def test_bytesio_copy_blocked():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('buf = io.BytesIO(spool.read())')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for BytesIO(spool.read()) in excel scope"

def test_bytesio_copy_allowed_outside_scope():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        other_dir = os.path.join(tmp, "app", "modules", "other")
        os.makedirs(other_dir, exist_ok=True)
        with open(os.path.join(other_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('buf = io.BytesIO(spool.read())')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, "Expected BytesIO copy to be allowed outside scope"

def test_list_iter_rows_blocked():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('rows = list(ws.iter_rows(values_only=True))')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for materialised iter_rows in excel scope"

def test_chunked_read_allowed():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('chunk = file.file.read(65536)')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, f"Expected 0 issues for chunked read, got {issues}"

def test_streaming_iter_rows_allowed():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('for row in ws.iter_rows(values_only=True):\n    pass')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, f"Expected 0 issues for streaming iter_rows, got {issues}"


def test_projects_api_scoping_blocks_inside_upload():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        api_dir = os.path.join(tmp, "app", "api")
        os.makedirs(api_dir, exist_ok=True)
        with open(os.path.join(api_dir, "projects.py"), "w", encoding="utf-8") as f:
            f.write('''
def upload_project_asset_import_file():
    data = spool.read()
''')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker inside upload function in projects.py"


def test_projects_api_scoping_allows_outside_upload():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        api_dir = os.path.join(tmp, "app", "api")
        os.makedirs(api_dir, exist_ok=True)
        with open(os.path.join(api_dir, "projects.py"), "w", encoding="utf-8") as f:
            f.write('''
def unrelated_function():
    data = spool.read()
''')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, "Expected no blocker outside upload function in projects.py"



def test_apply_staging_for_update_blocker():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import", "application")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "apply_staging.py"), "w", encoding="utf-8") as f:
            f.write(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).order_by(ProjectAssetImportStagingRow.id).all()\n"
            )
        issues = m.check_apply_path_blockers(tmp)
        assert issues > 0, "Expected FOR UPDATE blocker on Apply staging query"


def test_apply_setattr_blocker():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import", "application")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "apply_staging.py"), "w", encoding="utf-8") as f:
            f.write(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n"
                "    setattr(line, 'asset_name', x)\n"
            )
        issues = m.check_apply_path_blockers(tmp)
        assert issues > 0, "Expected setattr blocker on Apply path"


def test_apply_raw_values_blocker():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import", "application")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "apply_staging.py"), "w", encoding="utf-8") as f:
            f.write(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n"
                "    v = row.raw_values\n"
            )
        issues = m.check_apply_path_blockers(tmp)
        assert issues > 0, "Expected raw_values blocker on Apply path"


def test_approved_apply_implementation_passes_scanner():
    m = _import_checker()
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    monorepo = os.path.abspath(os.path.join(backend_root, ".."))
    issues = m.check_apply_path_blockers(monorepo)
    assert issues == 0, f"Approved Apply implementation must pass scanner, got {issues}"


def test_apply_update_upsert_merge_blockers():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import", "application")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "apply_staging.py"), "w", encoding="utf-8") as f:
            f.write(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n"
                "    db.query(ProjectAssetLine).filter_by(id=x).update({})\n"
                "    db.merge(line)\n"
                "    db.bulk_update_mappings(ProjectAssetLine, [])\n"
            )
        issues = m.check_apply_path_blockers(tmp)
        assert issues >= 3, f"Expected update/merge/bulk blockers, got {issues}"


def test_apply_preexisting_line_assign_blocker():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import", "application")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "apply_staging.py"), "w", encoding="utf-8") as f:
            f.write(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n"
                "    existing_line.asset_name = 'x'\n"
            )
        issues = m.check_apply_path_blockers(tmp)
        assert issues > 0, "Expected pre-existing line update blocker"


def test_apply_endpoint_missing_workbench_edit():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        excel_dir = os.path.join(tmp, "app", "modules", "excel_import", "application")
        os.makedirs(excel_dir, exist_ok=True)
        with open(os.path.join(excel_dir, "apply_staging.py"), "w", encoding="utf-8") as f:
            f.write(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n"
            )
        api_dir = os.path.join(tmp, "app", "api")
        os.makedirs(api_dir, exist_ok=True)
        with open(os.path.join(api_dir, "projects.py"), "w", encoding="utf-8") as f:
            f.write(
                "@router.post('/x/apply')\n"
                "def apply_project_asset_import_batch_endpoint():\n"
                "    return apply_project_asset_import_batch()\n"
            )
        issues = m.check_apply_path_blockers(tmp)
        assert issues > 0, "Expected missing workbench:edit blocker"
