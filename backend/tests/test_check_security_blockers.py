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
