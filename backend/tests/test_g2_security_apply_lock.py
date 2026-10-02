from tests.check_security import check_apply_path_blockers


def test_recovery_lock_cannot_mask_missing_command_lock(tmp_path):
    directory = tmp_path / "backend" / "app" / "modules" / "excel_import" / "application"
    directory.mkdir(parents=True)
    (directory / "apply_staging.py").write_text('''
def _recover_apply_failure(db):
    db.query(ProjectAssetImportStagingRow).with_for_update().all()
def apply_project_asset_import_batch(db):
    db.query(ProjectAssetImportStagingRow).all()
''', encoding="utf-8")
    api = tmp_path / "backend" / "app" / "api"
    api.mkdir()
    (api / "projects.py").write_text('''
@router.post("/apply")
def apply_project_asset_import_batch_endpoint(db):
    permission = "workbench:edit"
    return apply_project_asset_import_batch(db)
''', encoding="utf-8")
    assert check_apply_path_blockers(str(tmp_path)) > 0
