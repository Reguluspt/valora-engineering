"""S13-PR-003 deterministic workbook-structure evidence and adversarial gates."""
from __future__ import annotations

import io
import json
import tempfile
import uuid
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app as fastapi_app
import app.modules.excel_import.models  # noqa: F401
from app.modules.excel_import.domain.workbook_structure import (
    STRUCTURE_RULE_VERSION,
    analyze_workbook_structure,
    canonical_payload_digest,
    require_review_for_drift,
)
from app.modules.excel_import.domain.workbook_adapter import (
    AdapterInspectionResult,
    CellValue,
    SheetSummary,
    WorkbookFormat,
)
from app.modules.excel_import.infrastructure.object_storage import (
    FakeObjectStorage,
    set_object_storage_override,
)
from app.modules.excel_import.models import (
    ImportSourceArtifact,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    ImportBatchStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectAssetLine,
    ProjectWorkflowStatus,
    Role,
    User,
    UserRole,
    UserStatus,
)


@pytest.fixture
def structure_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def structure_storage():
    storage = FakeObjectStorage()
    set_object_storage_override(storage)
    try:
        yield storage
    finally:
        set_object_storage_override(None)


@pytest.fixture
def structure_client(structure_db: Session, structure_storage) -> TestClient:
    def override_get_db():
        yield structure_db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)


def _seed(db: Session):
    org = OrganizationProfile(
        legal_name="Structure Org",
        organization_slug=f"structure-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    other_org = OrganizationProfile(
        legal_name="Other Org",
        organization_slug=f"other-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    db.add_all([org, other_org])
    db.commit()

    role = Role(
        code=f"structure-editor-{uuid.uuid4().hex[:8]}",
        display_name="Structure editor",
        permissions=["project:read", "workbench:edit"],
    )
    db.add(role)
    db.commit()
    user = User(
        organization_id=org.id,
        email=f"structure-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Structure Editor",
        status=UserStatus.ACTIVE,
    )
    other_user = User(
        organization_id=other_org.id,
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Other Editor",
        status=UserStatus.ACTIVE,
    )
    db.add_all([user, other_user])
    db.commit()
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id, is_active=True),
            UserRole(user_id=other_user.id, role_id=role.id, is_active=True),
        ]
    )
    db.commit()

    customer = Customer(
        organization_id=org.id,
        legal_name="Structure Customer",
        status=CustomerStatus.ACTIVE,
        created_by=user.id,
    )
    db.add(customer)
    db.commit()
    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        name="Structure Project",
        code=f"SP-{uuid.uuid4().hex[:6]}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=user.id,
    )
    db.add(project)
    db.commit()
    batch = ProjectAssetImportBatch(
        organization_id=org.id,
        project_id=project.id,
        source_filename="structure.xlsx",
        status=ImportBatchStatus.CREATED,
        created_by_user_id=user.id,
    )
    db.add(batch)
    db.commit()
    return org, user, other_user, project, batch


def _populate_pd001_sheet(ws, *, header_row: int = 5, multi_row: bool = False) -> None:
    ws.title = "PD-001"
    ws.merge_cells("A1:H1")
    ws["A1"] = "BẢNG KÊ TÀI SẢN THẨM ĐỊNH"
    ws["A2"] = "Khách hàng: ACME"
    ws["A3"] = "Đơn vị: VNĐ"
    if header_row > 5:
        ws.insert_rows(4, header_row - 5)
    if multi_row:
        ws.cell(header_row, 1, "Thông tin")
        ws.cell(header_row, 5, "Giá trị")
        ws.cell(header_row + 1, 1, "STT")
        ws.cell(header_row + 1, 2, "Tên tài sản")
        ws.cell(header_row + 1, 3, "Đặc điểm")
        ws.cell(header_row + 1, 4, "ĐVT")
        ws.cell(header_row + 1, 5, "Số lượng")
        ws.cell(header_row + 1, 6, "Đơn giá")
        ws.cell(header_row + 1, 7, "Thành tiền")
        ws.cell(header_row + 1, 8, "Ghi chú")
        data_row = header_row + 2
    else:
        headers = [
            "STT",
            "Tên tài sản",
            "Đặc điểm",
            "ĐVT",
            "Số lượng",
            "Đơn giá",
            "Thành tiền",
            "Ghi chú",
        ]
        for column, value in enumerate(headers, 1):
            ws.cell(header_row, column, value)
        data_row = header_row + 1

    rows = [
        [1, "Máy bơm", "Model X", "cái", 2, 100, 200, None],
        [2, "Máy phát", "Model Y", "bộ", 1, 300, 300, None],
        ["PHẦN ĐIỆN", None, None, None, None, None, None, None],
        [3, "Tủ điện", "IP54", "bộ", 1, 400, 400, None],
        ["Cộng phần điện", None, None, None, None, None, 400, None],
        ["PHẦN NƯỚC", None, None, None, None, None, None, None],
        [4, "Máy lọc", "Model Z", "bộ", 1, 500, 500, None],
        ["TỔNG CỘNG", None, None, None, None, None, 900, None],
        ["Ghi chú: tài sản đã qua sử dụng", None, None, None, None, None, None, None],
        ["Dòng chưa xác định", None, None, None, None, None, None, None],
    ]
    for offset, values in enumerate(rows):
        for column, value in enumerate(values, 1):
            ws.cell(data_row + offset, column, value)


def _xlsx_bytes(*, header_row: int = 5, multi_row: bool = False, two_sheets: bool = False) -> bytes:
    workbook = openpyxl.Workbook()
    _populate_pd001_sheet(workbook.active, header_row=header_row, multi_row=multi_row)
    if two_sheets:
        second = workbook.create_sheet("PD-002")
        _populate_pd001_sheet(second, header_row=header_row, multi_row=multi_row)
        second.title = "PD-002"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _xls_bytes() -> bytes:
    pytest.importorskip("xlwt")
    import xlwt

    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet("PD-001")
    sheet.write_merge(0, 0, 0, 7, "BẢNG KÊ TÀI SẢN THẨM ĐỊNH")
    sheet.write(1, 0, "Khách hàng: ACME")
    sheet.write(2, 0, "Đơn vị: VNĐ")
    headers = [
        "STT",
        "Tên tài sản",
        "Đặc điểm",
        "ĐVT",
        "Số lượng",
        "Đơn giá",
        "Thành tiền",
        "Ghi chú",
    ]
    for column, value in enumerate(headers):
        sheet.write(4, column, value)
    for row, values in enumerate(
        [
            [1, "Máy bơm", "Model X", "cái", 2, 100, 200],
            [2, "Máy phát", "Model Y", "bộ", 1, 300, 300],
            ["PHẦN ĐIỆN"],
            [3, "Tủ điện", "IP54", "bộ", 1, 400, 400],
            ["Cộng phần điện", "", "", "", "", "", 400],
            ["PHẦN NƯỚC"],
            [4, "Máy lọc", "Model Z", "bộ", 1, 500, 500],
            ["TỔNG CỘNG", "", "", "", "", "", 900],
            ["Ghi chú: tài sản đã qua sử dụng"],
        ],
        5,
    ):
        for column, value in enumerate(values):
            sheet.write(row, column, value)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _upload(
    client: TestClient,
    user: User,
    project: Project,
    batch: ProjectAssetImportBatch,
    data: bytes,
    *,
    suffix: str = "xlsx",
) -> dict:
    content_type = (
        "application/vnd.ms-excel"
        if suffix == "xls"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response = client.post(
        f"/api/v1/projects/{project.id}/asset-imports/{batch.id}/source-artifacts",
        files={"file": (f"source.{suffix}", io.BytesIO(data), content_type)},
        headers={"X-User-Id": str(user.id)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _snapshot_path(project: Project, batch: ProjectAssetImportBatch, artifact_id: str) -> str:
    return (
        f"/api/v1/projects/{project.id}/asset-imports/{batch.id}/source-artifacts/"
        f"{artifact_id}/structure-snapshots"
    )


@pytest.mark.parametrize(
    ("suffix", "factory"),
    [("xlsx", _xlsx_bytes), ("xls", _xls_bytes)],
)
def test_real_adapters_propose_row_five_and_classify_markers(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
    suffix,
    factory,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact = _upload(structure_client, user, project, batch, factory(), suffix=suffix)
    path = _snapshot_path(project, batch, artifact["id"])
    response = structure_client.post(path, headers={"X-User-Id": str(user.id)})
    assert response.status_code == 201, response.text
    body = response.json()
    payload = body["structure_payload"]
    assert body["rule_version"] == STRUCTURE_RULE_VERSION
    assert body["disposition"] == "proposed"
    assert payload["candidates"][0]["sheet_name"] == "PD-001"
    assert payload["candidates"][0]["header_start_row"] == 5
    assert payload["candidates"][0]["header_end_row"] == 5
    assert payload["candidates"][0]["header_labels"][0] == "STT"
    counts = payload["row_classification"]["counts"]
    assert counts["asset"] == 4
    assert counts["section"] == 2
    assert counts["subtotal"] == 1
    assert counts["total"] == 1
    assert counts["note"] == 1
    assert body["analysis_digest_sha256"] == canonical_payload_digest(payload)


def test_multirow_header_is_detected_without_absorbing_asset_row(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact = _upload(
        structure_client,
        user,
        project,
        batch,
        _xlsx_bytes(multi_row=True),
    )
    response = structure_client.post(
        _snapshot_path(project, batch, artifact["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert response.status_code == 201, response.text
    candidate = response.json()["structure_payload"]["candidates"][0]
    assert candidate["header_start_row"] == 5
    assert candidate["header_end_row"] == 6
    assert candidate["data_start_row"] == 7
    assert "Thông tin" in candidate["header_labels"][0]
    assert "STT" in candidate["header_labels"][0]


def test_competing_sheets_fail_to_review_and_title_never_wins(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact = _upload(
        structure_client,
        user,
        project,
        batch,
        _xlsx_bytes(two_sheets=True),
    )
    response = structure_client.post(
        _snapshot_path(project, batch, artifact["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert response.status_code == 201, response.text
    payload = response.json()["structure_payload"]
    assert payload["disposition"] == "review_required"
    assert "competing_candidates" in payload["disposition_reasons"]
    assert payload["candidates"][0]["header_start_row"] == 5
    assert all(candidate["header_start_row"] != 1 for candidate in payload["candidates"])


def test_structure_drift_forces_review_without_changing_original_payload():
    current = {
        "disposition": "proposed",
        "disposition_reasons": [],
        "proposed_candidate_index": 0,
        "candidates": [
            {
                "sheet_name": "PD-001",
                "header_start_row": 6,
                "header_end_row": 6,
                "data_start_row": 7,
                "candidate_table_bounds": {"min_column": 1, "max_column": 8},
            }
        ],
    }
    previous = {
        **current,
        "candidates": [
            {
                **current["candidates"][0],
                "header_start_row": 5,
                "header_end_row": 5,
                "data_start_row": 6,
            }
        ],
    }
    result = require_review_for_drift(current, previous)
    assert result["disposition"] == "review_required"
    assert "structure_drift_from_previous_generation" in result["disposition_reasons"]
    assert current["disposition"] == "proposed"
    assert current["disposition_reasons"] == []


def test_generation_drift_is_detected_from_latest_prior_source(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    first_artifact = _upload(structure_client, user, project, batch, _xlsx_bytes())
    first = structure_client.post(
        _snapshot_path(project, batch, first_artifact["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert first.status_code == 201
    assert first.json()["disposition"] == "proposed"

    second_artifact = _upload(
        structure_client,
        user,
        project,
        batch,
        _xlsx_bytes(header_row=6),
    )
    second = structure_client.post(
        _snapshot_path(project, batch, second_artifact["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert second.status_code == 201, second.text
    payload = second.json()["structure_payload"]
    assert payload["candidates"][0]["header_start_row"] == 6
    assert payload["disposition"] == "review_required"
    assert "structure_drift_from_previous_generation" in payload["disposition_reasons"]


def test_reordered_headers_force_review_even_when_geometry_is_unchanged(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    first_artifact = _upload(structure_client, user, project, batch, _xlsx_bytes())
    first = structure_client.post(
        _snapshot_path(project, batch, first_artifact["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert first.status_code == 201

    workbook = openpyxl.load_workbook(io.BytesIO(_xlsx_bytes()))
    sheet = workbook["PD-001"]
    sheet["B5"], sheet["C5"] = sheet["C5"].value, sheet["B5"].value
    reordered = io.BytesIO()
    workbook.save(reordered)
    second_artifact = _upload(
        structure_client,
        user,
        project,
        batch,
        reordered.getvalue(),
    )
    second = structure_client.post(
        _snapshot_path(project, batch, second_artifact["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert second.status_code == 201, second.text
    payload = second.json()["structure_payload"]
    assert payload["disposition"] == "review_required"
    assert "structure_drift_from_previous_generation" in payload["disposition_reasons"]


def test_scan_candidate_retention_and_preview_are_bounded_and_iterators_close():
    class TrackingRows:
        def __init__(self, rows):
            self._rows = iter(rows)
            self.next_calls = 0
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            self.next_calls += 1
            return next(self._rows)

        def close(self):
            self.closed = True

    def cells(row_number, values):
        return tuple(
            CellValue(
                row=row_number,
                column=index,
                coordinate=f"R{row_number}C{index}",
                value=value,
                cell_type="number" if isinstance(value, (int, float)) else "string",
            )
            for index, value in enumerate(values, 1)
        )

    rows = [
        cells(1, ["BẢNG KÊ TÀI SẢN THẨM ĐỊNH"]),
        cells(2, ["Khách hàng: ACME"]),
        cells(3, ["Đơn vị: VNĐ"]),
        cells(4, [None]),
        cells(5, ["STT", "Tên tài sản", "ĐVT", "Số lượng", "Thành tiền"]),
    ]
    rows.extend(cells(index, [index - 5, f"Tài sản {index}", "cái", 1, 100]) for index in range(6, 501))
    trackers = []

    def row_provider(_sheet_name):
        tracker = TrackingRows(rows)
        trackers.append(tracker)
        return tracker

    inspection = AdapterInspectionResult(
        format=WorkbookFormat.XLSX,
        adapter_name="tracking",
        adapter_version="1",
        sheet_names=("PD-001",),
        sheets=(SheetSummary(name="PD-001", max_row=500, max_column=5),),
    )
    payload = analyze_workbook_structure(inspection, row_provider)
    assert payload["candidate_count"] <= 25
    assert len(payload["row_classification"]["preview"]) == 200
    assert payload["row_classification"]["preview_truncated"] is True
    assert trackers[0].next_calls == 200
    assert all(tracker.closed for tracker in trackers)


def test_append_only_replay_digest_and_no_mutation(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact = _upload(structure_client, user, project, batch, _xlsx_bytes())
    path = _snapshot_path(project, batch, artifact["id"])
    before_staging = structure_db.query(ProjectAssetImportStagingRow).count()
    before_lines = structure_db.query(ProjectAssetLine).count()

    first = structure_client.post(
        path,
        headers={"X-User-Id": str(user.id)},
        json={
            "rule_version": "caller-override",
            "candidate": {"header_start_row": 1},
            "disposition": "proposed",
        },
    )
    second = structure_client.post(path, headers={"X-User-Id": str(user.id)})
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["snapshot_version"] == 1
    assert second.json()["snapshot_version"] == 2
    assert first.json()["rule_version"] == STRUCTURE_RULE_VERSION
    assert first.json()["structure_payload"]["candidates"][0]["header_start_row"] == 5
    assert first.json()["analysis_digest_sha256"] == second.json()["analysis_digest_sha256"]

    listed = structure_client.get(path, headers={"X-User-Id": str(user.id)})
    assert listed.status_code == 200, listed.text
    assert [item["snapshot_version"] for item in listed.json()] == [1, 2]
    snapshot_id = first.json()["id"]
    replayed = structure_client.get(
        f"{path}/{snapshot_id}",
        headers={"X-User-Id": str(user.id)},
    )
    assert replayed.status_code == 200
    assert replayed.json() == first.json()
    assert structure_db.query(ProjectAssetImportStagingRow).count() == before_staging
    assert structure_db.query(ProjectAssetLine).count() == before_lines

    events = (
        structure_db.query(AuditEvent)
        .filter(AuditEvent.event_name == "WorkbookStructureAnalyzed")
        .all()
    )
    assert len(events) == 2
    serialized_audit = json.dumps(events[0].payload, ensure_ascii=False)
    assert "Máy bơm" not in serialized_audit
    assert "header_labels" not in serialized_audit


def test_cross_tenant_snapshot_routes_are_safe_not_found(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, other_user, project, batch = _seed(structure_db)
    artifact = _upload(structure_client, user, project, batch, _xlsx_bytes())
    path = _snapshot_path(project, batch, artifact["id"])
    owner_response = structure_client.post(
        path,
        headers={"X-User-Id": str(user.id)},
    )
    assert owner_response.status_code == 201
    response = structure_client.post(
        path,
        headers={"X-User-Id": str(other_user.id)},
    )
    assert response.status_code == 404
    listed = structure_client.get(path, headers={"X-User-Id": str(other_user.id)})
    assert listed.status_code == 404
    replayed = structure_client.get(
        f"{path}/{owner_response.json()['id']}",
        headers={"X-User-Id": str(other_user.id)},
    )
    assert replayed.status_code == 404
    assert structure_db.query(WorkbookStructureSnapshot).count() == 1


def test_non_available_source_fails_before_object_read(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage: FakeObjectStorage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact_body = _upload(structure_client, user, project, batch, _xlsx_bytes())
    artifact = structure_db.get(ImportSourceArtifact, uuid.UUID(artifact_body["id"]))
    artifact.state = "orphaned"
    structure_db.commit()
    structure_storage.fail_open_stream = True

    response = structure_client.post(
        _snapshot_path(project, batch, artifact_body["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "source_artifact_not_available"
    assert structure_db.query(WorkbookStructureSnapshot).count() == 0


@pytest.mark.parametrize("failure", ["missing", "short_read", "checksum"])
def test_object_evidence_failure_creates_no_snapshot_or_success_audit(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage: FakeObjectStorage,
    failure: str,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact_body = _upload(structure_client, user, project, batch, _xlsx_bytes())
    artifact = structure_db.get(ImportSourceArtifact, uuid.UUID(artifact_body["id"]))
    original = structure_storage._objects[artifact.storage_object_key]
    temp_dir = Path(tempfile.gettempdir())
    temp_before = set(temp_dir.glob("valora-structure-*"))
    if failure == "missing":
        del structure_storage._objects[artifact.storage_object_key]
    elif failure == "short_read":
        structure_storage.truncate_open_to = len(original) - 1
    else:
        structure_storage._objects[artifact.storage_object_key] = b"X" + original[1:]

    response = structure_client.post(
        _snapshot_path(project, batch, artifact_body["id"]),
        headers={"X-User-Id": str(user.id)},
    )
    assert response.status_code == 409
    assert set(temp_dir.glob("valora-structure-*")) == temp_before
    assert structure_db.query(WorkbookStructureSnapshot).count() == 0
    assert (
        structure_db.query(AuditEvent)
        .filter(AuditEvent.event_name == "WorkbookStructureAnalyzed")
        .count()
        == 0
    )
    assert structure_db.query(ProjectAssetImportStagingRow).count() == 0
    assert structure_db.query(ProjectAssetLine).count() == 0


def test_tampered_snapshot_fails_closed_on_list_and_get(
    structure_client: TestClient,
    structure_db: Session,
    structure_storage,
):
    _org, user, _other, project, batch = _seed(structure_db)
    artifact = _upload(structure_client, user, project, batch, _xlsx_bytes())
    path = _snapshot_path(project, batch, artifact["id"])
    created = structure_client.post(path, headers={"X-User-Id": str(user.id)})
    assert created.status_code == 201
    snapshot = structure_db.get(WorkbookStructureSnapshot, uuid.UUID(created.json()["id"]))
    altered = dict(snapshot.structure_payload)
    altered["candidate_count"] = altered["candidate_count"] + 1
    snapshot.structure_payload = altered
    structure_db.commit()

    listed = structure_client.get(path, headers={"X-User-Id": str(user.id)})
    assert listed.status_code == 500
    replayed = structure_client.get(
        f"{path}/{snapshot.id}",
        headers={"X-User-Id": str(user.id)},
    )
    assert replayed.status_code == 500


def test_canonical_digest_is_order_independent_and_tamper_sensitive():
    left = {"b": [2, 1], "a": {"y": "đ", "x": 1}}
    right = {"a": {"x": 1, "y": "đ"}, "b": [2, 1]}
    assert canonical_payload_digest(left) == canonical_payload_digest(right)
    assert canonical_payload_digest(left) != canonical_payload_digest({**right, "b": [1, 2]})
