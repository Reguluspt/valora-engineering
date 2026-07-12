import os
import sys
import tempfile


def write_temp_file(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".ts")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _import_checker():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import check_security
    return check_security


def test_hardcoded_slug_fails():
    temp_path = write_temp_file('const x = "hd-98-gia-lai";')
    try:
        m = _import_checker()
        issues = m.check_security_baseline_and_blockers(os.path.dirname(temp_path))
        assert issues > 0, "Expected blocker for hard-coded slug"
    finally:
        os.unlink(temp_path)


def test_all_zero_uuid_fails():
    temp_path = write_temp_file('const x = "00000000-0000-0000-0000-000000000000";')
    try:
        m = _import_checker()
        issues = m.check_security_baseline_and_blockers(os.path.dirname(temp_path))
        assert issues > 0, "Expected blocker for all-zero UUID"
    finally:
        os.unlink(temp_path)


def test_clean_source_passes():
    temp_path = write_temp_file('const x = "normal-string";')
    try:
        m = _import_checker()
        issues = m.check_security_baseline_and_blockers(os.path.dirname(temp_path))
        assert issues == 0, f"Expected 0 issues for clean source, got {issues}"
    finally:
        os.unlink(temp_path)
