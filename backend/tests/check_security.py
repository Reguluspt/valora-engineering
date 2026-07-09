import os
import sys

def check_secret_placeholders(directory):
    print("=== Scanning for hardcoded secrets ===")
    secret_keywords = ["SECRET_KEY", "PASSWORD", "token"]
    issues_found = 0
    for root, dirs, files in os.walk(directory):
        if "node_modules" in root or ".git" in root or "__pycache__" in root or ".pytest_cache" in root:
            continue
        for file in files:
            if file.endswith((".py", ".ts", ".tsx", ".yml", ".json", ".env")):
                if "test" in file or "check_security" in file:
                    continue
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line_idx, line in enumerate(f, 1):
                            # Simple heuristics to check if someone hardcoded a non-placeholder value
                            # Match variable = "something" but allow standard defaults and local configs
                            for kw in secret_keywords:
                                if kw in line and "=" in line:
                                    # Basic heuristic checks
                                    if '"' in line or "'" in line:
                                        # Filter out standard local placeholders
                                        if any(p in line.lower() for p in ["local", "placeholder", "example", "test", "change-this", "change_this"]):
                                            continue
                                        # Simple warning logs
                                        print(f"Potential hardcoded secret found in {path}:{line_idx} - {line.strip()}")
                                        issues_found += 1
                except Exception as e:
                    pass
    if issues_found > 0:
        print(f"Scan finished: {issues_found} potential secrets found.")
    else:
        print("Scan finished: No hardcoded secrets found.")
    return issues_found == 0

def check_forbidden_behavior(directory):
    print("=== Scanning for forbidden behaviors and leaked endpoints ===")
    forbidden_terms = [
        "/asset-lines/{line_id}/context",
        "/projects/{project_id}/asset-lines",
        "/inline-edits/{draft_id}/commit",
        "Celery",
        "redis-worker",
    ]
    issues_found = 0
    for root, dirs, files in os.walk(directory):
        if "node_modules" in root or ".git" in root or "__pycache__" in root or "tests" in root or "check_security.py" in root or ".agents" in root:
            continue
        for file in files:
            if file.endswith((".py", ".ts", ".tsx")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line_idx, line in enumerate(f, 1):
                            for term in forbidden_terms:
                                if term in line:
                                    print(f"Forbidden term '{term}' matched in {path}:{line_idx} - {line.strip()}")
                                    issues_found += 1
                except Exception as e:
                    pass
    if issues_found > 0:
        print(f"Scan finished: {issues_found} forbidden patterns matched.")
    else:
        print("Scan finished: No forbidden patterns found.")
    return issues_found == 0

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    secrets_ok = check_secret_placeholders(base_dir)
    behavior_ok = check_forbidden_behavior(base_dir)
    if not secrets_ok or not behavior_ok:
        sys.exit(1)
    sys.exit(0)
