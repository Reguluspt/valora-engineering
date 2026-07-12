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
        with open(os.path.join(tmp, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('data = spool.read()')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for unbounded .read()"


def test_bytesio_copy_blocked():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('buf = io.BytesIO(spool.read())')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for BytesIO(spool.read())"


def test_list_iter_rows_blocked():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('rows = list(ws.iter_rows(values_only=True))')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues > 0, "Expected blocker for materialised iter_rows"


def test_chunked_read_allowed():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('chunk = file.file.read(65536)')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, f"Expected 0 issues for chunked read, got {issues}"


def test_streaming_iter_rows_allowed():
    m = _import_checker()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "runtime.py"), "w", encoding="utf-8") as f:
            f.write('for row in ws.iter_rows(values_only=True):')
        issues = m.check_security_baseline_and_blockers(tmp)
        assert issues == 0, f"Expected 0 issues for streaming iter_rows, got {issues}"
