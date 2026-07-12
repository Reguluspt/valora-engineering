import os
import sys
import re

# Controlled security debt baseline configuration
TEMPORARY_BASELINE = {
    "S12R-AUTH-001": {
        "pattern": r"X-User-Id",
        "description": "Production X-User-Id authentication usage",
        "files": {},
        "target_pr": "S12-R-002",
        "expiry_condition": "Implement credential-based auth session"
    }
}

CRITICAL_BLOCKERS = [
    {
        "name": "Dangerous wildcard production CORS",
        "pattern": r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]",
        "exts": (".py",)
    },
    {
        "name": "Hard-coded project slug in runtime source",
        "pattern": r"hd-98-gia-lai",
        "exts": (".ts", ".tsx", ".py", ".yml", ".json"),
        "description": "The remediation slug must never reappear in production runtime code."
    },
    {
        "name": "All-zero UUID runtime fallback",
        "pattern": r"00000000-0000-0000-0000-000000000000",
        "exts": (".ts", ".tsx", ".py"),
        "description": "All-zero UUID must never be sent as a project or session identifier."
    },
    {
        "name": "Unbounded UploadFile read in runtime",
        "pattern": r"\.read\(\s*\)",
        "exts": (".py",),
        "description": ".read() without a size argument on a file/spool/socket consumes unlimited memory."
    },
    {
        "name": "Whole-file BytesIO copy in runtime",
        "pattern": r"BytesIO\s*\(\s*.*\.read\s*\(\s*\)\s*\)",
        "exts": (".py",),
        "description": "io.BytesIO(file.read()) creates an extra copy of the entire upload."
    },
    {
        "name": "Worksheet row materialization in runtime",
        "pattern": r"list\(\s*.*\.iter_rows\(",
        "exts": (".py",),
        "description": "list(ws.iter_rows(...)) materialises all workbook rows into memory at once."
    }
]

def check_secret_placeholders(directory):
    print("=== Scanning for hardcoded secrets ===")
    secret_patterns = [
        r"(?:secret_key|password|api_token|auth_token)\s*=\s*['\"][^'\"]+['\"]",
        r"['\"](?:secret_key|password|api_token|auth_token)['\"]\s*:\s*['\"][^'\"]+['\"]"
    ]
    issues_found = 0
    for root, dirs, files in os.walk(directory):
        if "node_modules" in root or ".git" in root or "__pycache__" in root or ".pytest_cache" in root or "docs" in root or "dist" in root:
            continue
        for file in files:
            if file.endswith((".py", ".ts", ".tsx", ".yml", ".json", ".env")):
                if "test" in file or "check_security" in file:
                    continue
                path = os.path.join(root, file)
                # Fail-closed: No generic try-except block here. If file fails to open/read, let it raise.
                with open(path, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f, 1):
                        if line.strip().startswith(("#", "//")):
                            continue
                        for pattern in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                if any(p in line.lower() for p in ["local", "placeholder", "example", "test", "change-this", "change_this"]):
                                    continue
                                print(f"[SECURITY FAIL] Hardcoded secret found in {path}:{line_idx} - {line.strip()}")
                                issues_found += 1
    return issues_found

def check_security_baseline_and_blockers(directory):
    print("=== Checking security baseline & critical blockers ===")
    issues = 0
    
    # Store dynamic counts per file for baseline items
    actual_counts = {fid: {} for fid in TEMPORARY_BASELINE}

    for root, dirs, files in os.walk(directory):
        if "node_modules" in root or ".git" in root or "__pycache__" in root or ".pytest_cache" in root:
            continue
        for file in files:
            # ONLY scan text/source files to prevent UnicodeDecodeError on binaries (like SQLite .db or .rar)
            if not file.endswith((".py", ".ts", ".tsx", ".yml", ".json", ".env")):
                continue

            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, directory).replace("\\", "/")

            # Exclude tests, check script, docs, and build outputs
            if "tests" in rel_path or "check_security.py" in rel_path or "conftest.py" in rel_path or "docs" in rel_path or "dist" in rel_path:
                continue

            # Fail-closed: Let file open/read raise errors if it encounters issues
            with open(path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, 1):
                    if line.strip().startswith(("#", "//")):
                        continue

                    # 1. Check critical blockers
                    for cb in CRITICAL_BLOCKERS:
                        if file.endswith(cb["exts"]):
                            if re.search(cb["pattern"], line, re.IGNORECASE):
                                print(f"[BLOCKER FAIL] {cb['name']} found in {rel_path}:{line_idx} - {line.strip()}")
                                issues += 1

                    # 2. Track baseline violations
                    for fid, config in TEMPORARY_BASELINE.items():
                        if re.search(config["pattern"], line, re.IGNORECASE):
                            actual_counts[fid][rel_path] = actual_counts[fid].get(rel_path, 0) + 1

    # Compare actual counts against baseline
    for fid, config in TEMPORARY_BASELINE.items():
        expected_files = config["files"]
        actual_files = actual_counts[fid]

        # Check for new files with this violation
        for rel_path, count in actual_files.items():
            if rel_path not in expected_files:
                print(f"[BASELINE FAIL] New file '{rel_path}' introduced baseline violation '{fid}' ({config['description']}): {count} occurrences")
                issues += 1
            else:
                expected_count = expected_files[rel_path]
                if count > expected_count:
                    print(f"[BASELINE FAIL] Violations in '{rel_path}' for '{fid}' increased from {expected_count} to {count}")
                    issues += 1
                else:
                    print(f"[BASELINE OK] '{rel_path}' has {count}/{expected_count} allowed violations of '{fid}'")

        # Check if some baseline violations were resolved (can decrease, but count must not exceed)
        for rel_path in expected_files:
            if rel_path not in actual_files:
                print(f"[BASELINE INFO] Clean check: '{rel_path}' no longer has violations of '{fid}' (Expected {expected_files[rel_path]})")

    return issues

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    secrets_failed = check_secret_placeholders(base_dir)
    baseline_failed = check_security_baseline_and_blockers(base_dir)
    
    total_failures = secrets_failed + baseline_failed
    if total_failures > 0:
        print(f"\nScan failed: {total_failures} critical security issues found.")
        sys.exit(1)
    
    print("\nScan passed: Controlled baseline validated without blocker regressions.")
    sys.exit(0)
