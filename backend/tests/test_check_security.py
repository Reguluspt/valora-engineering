import pytest
import os
import tempfile
import shutil
import sys
from unittest.mock import patch

# Ensure tests directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from check_security import check_secret_placeholders, check_security_baseline_and_blockers

@pytest.fixture
def temp_workspace():
    # Set up a temporary directory to simulate the workspace
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_python_double_quoted_secret(temp_workspace):
    # Test that double-quoted secret is detected
    file_path = os.path.join(temp_workspace, "app_file.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('SECRET_KEY = "real-secret"\n')
    
    issues = check_secret_placeholders(temp_workspace)
    assert issues == 1

def test_python_single_quoted_secret(temp_workspace):
    # Test that single-quoted secret is detected
    file_path = os.path.join(temp_workspace, "app_file.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("SECRET_KEY = 'real-secret'\n")
        f.write("PASSWORD = 'real-password'\n")
    
    issues = check_secret_placeholders(temp_workspace)
    assert issues == 2

def test_json_secret(temp_workspace):
    # Test that JSON secret is detected
    file_path = os.path.join(temp_workspace, "config.json")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('{"api_token": "real-token"}\n')
    
    issues = check_secret_placeholders(temp_workspace)
    assert issues == 1

def test_placeholders_allowlist(temp_workspace):
    # Test that placeholder values are ignored
    file_path = os.path.join(temp_workspace, "app_file.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('SECRET_KEY = "local-secret-key-change-this"\n')
        f.write('PASSWORD = "placeholder-password"\n')
        f.write('api_token = "example-token"\n')
    
    issues = check_secret_placeholders(temp_workspace)
    assert issues == 0

def test_file_scan_error_fails(temp_workspace):
    # Test that reading a file throws an error (fail-closed behavior)
    file_path = os.path.join(temp_workspace, "corrupted.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('SECRET_KEY = "real-secret"\n')
    
    # Mock builtins.open to raise PermissionError to simulate scan error
    with patch("builtins.open", side_effect=PermissionError("Mocked Permission Error")):
        with pytest.raises(PermissionError):
            check_secret_placeholders(temp_workspace)

def test_baseline_occurrence_increase_fails(temp_workspace, monkeypatch):
    # Mock baseline config
    mock_baseline = {
        "S12R-AUTH-001": {
            "pattern": r"X-User-Id",
            "description": "Test Auth Pattern",
            "files": {
                "app/core/rbac.py": 2
            },
            "target_pr": "S12-R-002",
            "expiry_condition": "Test"
        }
    }
    monkeypatch.setattr("check_security.TEMPORARY_BASELINE", mock_baseline)

    # 1. 2 occurrences (allowed)
    os.makedirs(os.path.join(temp_workspace, "app/core"), exist_ok=True)
    file_path = os.path.join(temp_workspace, "app/core/rbac.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("X-User-Id\nX-User-Id\n")
    
    issues = check_security_baseline_and_blockers(temp_workspace)
    assert issues == 0

    # 2. 3 occurrences (exceeds baseline)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("X-User-Id\nX-User-Id\nX-User-Id\n")
    
    issues = check_security_baseline_and_blockers(temp_workspace)
    assert issues == 1

def test_pattern_in_new_file_fails(temp_workspace, monkeypatch):
    # Mock baseline config
    mock_baseline = {
        "S12R-AUTH-001": {
            "pattern": r"X-User-Id",
            "description": "Test Auth Pattern",
            "files": {
                "app/core/rbac.py": 2
            },
            "target_pr": "S12-R-002",
            "expiry_condition": "Test"
        }
    }
    monkeypatch.setattr("check_security.TEMPORARY_BASELINE", mock_baseline)

    # Create allowed file
    os.makedirs(os.path.join(temp_workspace, "app/core"), exist_ok=True)
    with open(os.path.join(temp_workspace, "app/core/rbac.py"), "w", encoding="utf-8") as f:
        f.write("X-User-Id\n")

    # Create new file containing the baseline pattern
    with open(os.path.join(temp_workspace, "app/core/new_file.py"), "w", encoding="utf-8") as f:
        f.write("X-User-Id\n")
    
    issues = check_security_baseline_and_blockers(temp_workspace)
    assert issues == 1

def test_baseline_occurrence_decrease_allowed(temp_workspace, monkeypatch):
    # Mock baseline config
    mock_baseline = {
        "S12R-AUTH-001": {
            "pattern": r"X-User-Id",
            "description": "Test Auth Pattern",
            "files": {
                "app/core/rbac.py": 2
            },
            "target_pr": "S12-R-002",
            "expiry_condition": "Test"
        }
    }
    monkeypatch.setattr("check_security.TEMPORARY_BASELINE", mock_baseline)

    # Create file with 1 occurrence (expected 2)
    os.makedirs(os.path.join(temp_workspace, "app/core"), exist_ok=True)
    with open(os.path.join(temp_workspace, "app/core/rbac.py"), "w", encoding="utf-8") as f:
        f.write("X-User-Id\n")
    
    issues = check_security_baseline_and_blockers(temp_workspace)
    assert issues == 0
