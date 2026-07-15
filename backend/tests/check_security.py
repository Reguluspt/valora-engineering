import os
import sys
import re
import ast

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
    }
]

class ExcelIntakeSecurityVisitor(ast.NodeVisitor):
    def __init__(self, check_all=True):
        self.issues = []
        self.check_all = check_all
        self.in_upload_func = False

    def visit_FunctionDef(self, node):
        if not self.check_all:
            if node.name == "upload_project_asset_import_file":
                self.in_upload_func = True
                self.generic_visit(node)
                self.in_upload_func = False
        else:
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if not self.check_all:
            if node.name == "upload_project_asset_import_file":
                self.in_upload_func = True
                self.generic_visit(node)
                self.in_upload_func = False
        else:
            self.generic_visit(node)

    def visit_Call(self, node):
        if self.check_all or self.in_upload_func:
            # 1. Unbounded read: .read() with no args
            if isinstance(node.func, ast.Attribute) and node.func.attr == "read":
                if len(node.args) == 0 and not any(kw.arg == "size" for kw in node.keywords):
                    self.issues.append((node.lineno, "Unbounded UploadFile read in runtime", ".read() called without size limit"))
            
            # 2. BytesIO copy: BytesIO(source.read())
            is_bytesio = False
            if isinstance(node.func, ast.Name) and node.func.id == "BytesIO":
                is_bytesio = True
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "BytesIO":
                is_bytesio = True
                
            if is_bytesio and len(node.args) > 0:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "read":
                    self.issues.append((node.lineno, "Whole-file BytesIO copy in runtime", "BytesIO(source.read()) detected"))

            # 3. Worksheet row materialization: list(ws.iter_rows(...))
            if isinstance(node.func, ast.Name) and node.func.id == "list" and len(node.args) > 0:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "iter_rows":
                    self.issues.append((node.lineno, "Worksheet row materialization in runtime", "list(ws.iter_rows(...)) detected"))

        self.generic_visit(node)


class ApplyStagingSecurityVisitor(ast.NodeVisitor):
    """AST fail-closed checks for apply_staging.py."""

    FORBIDDEN_MUTATORS = frozenset(
        {
            "update",
            "delete",
            "merge",
            "upsert",
            "bulk_update_mappings",
            "bulk_insert_mappings",
            "bulk_save_objects",
        }
    )

    def __init__(self):
        self.issues = []
        self.has_staging_for_update = False
        self.staging_query_seen = False

    def visit_Call(self, node):
        # setattr(...)
        if isinstance(node.func, ast.Name) and node.func.id == "setattr":
            self.issues.append((node.lineno, "Apply uses raw setattr", "setattr()"))
        if isinstance(node.func, ast.Name) and node.func.id in ("merge", "upsert"):
            self.issues.append(
                (node.lineno, "Apply uses merge/upsert", f"{node.func.id}()")
            )
        # .delete() / .update() / merge / replace / bulk_* targeting official lines
        if isinstance(node.func, ast.Attribute) and node.func.attr in self.FORBIDDEN_MUTATORS:
            if self._chain_queries_asset_line(node.func.value) or node.func.attr in (
                "delete",
                "merge",
                "upsert",
                "bulk_update_mappings",
                "bulk_insert_mappings",
                "bulk_save_objects",
            ):
                # Always block delete/update/merge/upsert/bulk on Apply path
                self.issues.append(
                    (
                        node.lineno,
                        "Apply mutates/deletes official lines",
                        f".{node.func.attr}()",
                    )
                )
        # with_for_update on any call chain involving ProjectAssetImportStagingRow
        if isinstance(node.func, ast.Attribute) and node.func.attr == "with_for_update":
            if self._chain_queries_staging(node.func.value):
                self.has_staging_for_update = True
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr == "raw_values":
            self.issues.append((node.lineno, "Apply reads raw_values", "raw_values"))
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Flag assignment to attributes on a name that looks like a pre-existing line update
        # e.g. existing_line.asset_name = ... after query(ProjectAssetLine)
        for t in node.targets:
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name):
                if t.value.id in (
                    "existing",
                    "existing_line",
                    "preexisting",
                    "old_line",
                    "manual",
                    "prior_line",
                ):
                    self.issues.append(
                        (
                            node.lineno,
                            "Apply updates pre-existing ProjectAssetLine",
                            f"{t.value.id}.{t.attr} = ...",
                        )
                    )
        self.generic_visit(node)

    def _chain_queries_model(self, node, model_names: set[str]) -> bool:
        cur = node
        while isinstance(cur, ast.Call):
            if isinstance(cur.func, ast.Attribute) and cur.func.attr == "query":
                for arg in cur.args:
                    if isinstance(arg, ast.Name) and arg.id in model_names:
                        return True
                    if isinstance(arg, ast.Attribute) and arg.attr in model_names:
                        return True
            if isinstance(cur.func, ast.Attribute):
                cur = cur.func.value
            else:
                break
        while isinstance(cur, ast.Attribute):
            cur = cur.value
            if isinstance(cur, ast.Call):
                return self._chain_queries_model(cur, model_names)
        return False

    def _chain_queries_staging(self, node) -> bool:
        hit = self._chain_queries_model(node, {"ProjectAssetImportStagingRow"})
        if hit:
            self.staging_query_seen = True
        return hit

    def _chain_queries_asset_line(self, node) -> bool:
        return self._chain_queries_model(node, {"ProjectAssetLine"})


def check_apply_path_blockers(directory):
    """S12-PR-004: fail-closed rules for Apply runtime only."""
    print("=== Checking S12-PR-004 Apply path blockers ===")
    issues = 0
    apply_path = os.path.join(
        directory, "backend", "app", "modules", "excel_import", "application", "apply_staging.py"
    )
    if not os.path.isfile(apply_path):
        apply_path = os.path.join(
            directory, "app", "modules", "excel_import", "application", "apply_staging.py"
        )
    projects_path = os.path.join(directory, "backend", "app", "api", "projects.py")
    if not os.path.isfile(projects_path):
        projects_path = os.path.join(directory, "app", "api", "projects.py")

    if not os.path.isfile(apply_path):
        print("[BLOCKER FAIL] missing apply_staging.py")
        issues += 1
    else:
        with open(apply_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            tree = ast.parse(content, filename=apply_path)
            visitor = ApplyStagingSecurityVisitor()
            visitor.visit(tree)
            for lineno, name, detail in visitor.issues:
                print(f"[BLOCKER FAIL] {name} found in apply_staging.py:{lineno} - {detail}")
                issues += 1
            if not visitor.has_staging_for_update:
                print(
                    "[BLOCKER FAIL] Apply staging query missing with_for_update() on ProjectAssetImportStagingRow"
                )
                issues += 1
        except SyntaxError as se:
            print(f"[AST ERROR] apply_staging.py: {se}")
            issues += 1

    if not os.path.isfile(projects_path):
        print("[BLOCKER FAIL] missing projects.py API file")
        issues += 1
    else:
        with open(projects_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            tree = ast.parse(content, filename=projects_path)
        except SyntaxError as se:
            print(f"[AST ERROR] projects.py: {se}")
            issues += 1
            return issues
        # Find apply endpoint function
        apply_fn = None
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if "apply" in node.name and "asset_import" in node.name:
                    apply_fn = node
                    break
        if apply_fn is None:
            # also scan for decorator path containing /apply
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for dec in node.decorator_list:
                        src = ast.dump(dec)
                        if "apply" in src:
                            apply_fn = node
                            break
        if apply_fn is None:
            print("[BLOCKER FAIL] Apply endpoint function not found in projects.py")
            issues += 1
        else:
            lines = content.splitlines()
            start = max(0, apply_fn.lineno - 8)
            end = apply_fn.end_lineno or (apply_fn.lineno + 40)
            fn_text = "\n".join(lines[start:end])
            if "workbench:edit" not in fn_text:
                print("[BLOCKER FAIL] Apply endpoint missing workbench:edit")
                issues += 1
            if "apply_project_asset_import_batch(" not in fn_text:
                print(
                    "[BLOCKER FAIL] Apply endpoint does not call application command apply_project_asset_import_batch"
                )
                issues += 1

    return issues


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
            is_excel_scope = ("app/modules/excel_import" in rel_path or "app/api/projects.py" in rel_path)
            if is_excel_scope and file.endswith(".py"):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    try:
                        tree = ast.parse(content, filename=path)
                        check_all = "app/api/projects.py" not in rel_path
                        visitor = ExcelIntakeSecurityVisitor(check_all=check_all)
                        visitor.visit(tree)
                        for lineno, name, detail in visitor.issues:
                            print(f"[BLOCKER FAIL] {name} found in {rel_path}:{lineno} - {detail}")
                            issues += 1
                    except SyntaxError as se:
                        print(f"[AST ERROR] Syntax error parsing {rel_path}: {se}")
                        issues += 1

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
    apply_failed = check_apply_path_blockers(base_dir)

    total_failures = secrets_failed + baseline_failed + apply_failed
    if total_failures > 0:
        print(f"\nScan failed: {total_failures} critical security issues found.")
        sys.exit(1)

    print("\nScan passed: Controlled baseline validated without blocker regressions.")
    sys.exit(0)
