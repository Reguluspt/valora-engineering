"""Focused unit proofs for the PR-05 OneDrive Personal foundation."""
from __future__ import annotations

import hashlib
import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Mapping

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.document_workspace.application.document_revision_service import (
    create_document_with_first_revision,
)
from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.m365_integration.application.bind_document_service import (
    bind_document_revision,
)
from app.modules.m365_integration.application.connection_service import (
    begin_onedrive_authorization,
    complete_onedrive_authorization,
)
from app.modules.m365_integration.domain.graph_gateway import (
    GraphDrive,
    GraphDriveItem,
    OAuthAccessToken,
    OAuthAuthorizationResult,
    OAuthAuthorizationStart,
)
from app.modules.m365_integration.infrastructure.credential_vault import (
    CredentialVaultError,
    DatabaseCredentialVault,
)
from app.modules.m365_integration.infrastructure.graph_adapter import (
    MicrosoftGraphError,
    MicrosoftGraphGateway,
)
from app.modules.m365_integration.infrastructure.microsoft_oauth import CONSUMER_ISSUER
from app.modules.m365_integration.infrastructure.access_log_redaction import (
    OAuthCallbackAccessLogRedactionMiddleware,
    REDACTED_QUERY_STRING,
)
from app.modules.m365_integration.models import (
    M365EncryptedCredential,
    M365OAuthState,
    M365RevisionBinding,
    OneDriveConnection,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Currency,
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectWorkflowStatus,
    Province,
    Role,
    SignerProfile,
    User,
    UserRole,
    UserSession,
    UserStatus,
)


TABLES = [
    OrganizationProfile.__table__,
    User.__table__,
    Role.__table__,
    UserRole.__table__,
    UserSession.__table__,
    Province.__table__,
    Currency.__table__,
    SignerProfile.__table__,
    Customer.__table__,
    Project.__table__,
    AuditEvent.__table__,
    DocumentRecord.__table__,
    DocumentRevision.__table__,
    DocumentRevisionCurrentHead.__table__,
    M365EncryptedCredential.__table__,
    OneDriveConnection.__table__,
    M365OAuthState.__table__,
    M365RevisionBinding.__table__,
]
SNAPSHOT_DIGEST = "a" * 64
CONTENT_CHECKSUM = "b" * 64
FLOW_SECRET = b'flow-material-with-authorization-code-and-state'
TOKEN_CACHE_SECRET = b'{"RefreshToken":{"secret":"refresh-secret"}}'


class FakeOAuthClient:
    def __init__(self) -> None:
        self.state = f"state-{uuid.uuid4()}"
        self.subject = "personal-subject-1"
        self.fail_refresh = False
        self.refresh_calls = 0

    def begin(self) -> OAuthAuthorizationStart:
        return OAuthAuthorizationStart(
            authorization_url=f"https://login.microsoftonline.com/consumers?state={self.state}",
            state=self.state,
            flow_material=FLOW_SECRET,
        )

    def complete(
        self, *, flow_material: bytes, auth_response: Mapping[str, str]
    ) -> OAuthAuthorizationResult:
        assert flow_material == FLOW_SECRET
        assert auth_response["state"] == self.state
        return OAuthAuthorizationResult(
            consumer_issuer=CONSUMER_ISSUER,
            microsoft_account_subject=self.subject,
            access_token="ephemeral-access-token",
            token_cache=TOKEN_CACHE_SECRET,
            granted_scopes=frozenset({"Files.Read"}),
        )

    def acquire_access_token(self, *, token_cache: bytes) -> OAuthAccessToken:
        self.refresh_calls += 1
        if self.fail_refresh:
            raise RuntimeError("provider detail must not escape")
        assert token_cache == TOKEN_CACHE_SECRET
        return OAuthAccessToken(
            access_token="ephemeral-refreshed-access-token",
            token_cache=TOKEN_CACHE_SECRET,
        )


class FakeGraphGateway:
    def __init__(self) -> None:
        self.drive = GraphDrive(drive_id="personal-drive-1", drive_type="personal")
        self.item_calls = 0
        self.item_name = "Bao-cao.docx"
        self.item_path = "/drive/root:/Ho-so/Bao-cao.docx"

    def get_default_drive(self, *, access_token: str) -> GraphDrive:
        assert access_token == "ephemeral-access-token"
        return self.drive

    def get_drive_item(
        self, *, access_token: str, drive_id: str, drive_item_id: str
    ) -> GraphDriveItem:
        assert access_token == "ephemeral-refreshed-access-token"
        self.item_calls += 1
        return GraphDriveItem(
            drive_id=drive_id,
            drive_item_id=drive_item_id,
            graph_version_id=None,
            e_tag='"etag-1"',
            c_tag='"ctag-1"',
            last_modified_at=datetime(2026, 9, 12, 3, 0, tzinfo=timezone.utc),
            size_bytes=2048,
            name=self.item_name,
            path=self.item_path,
            web_url="https://onedrive.live.com/example",
        )


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine, tables=TABLES)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed(db: Session, *, suffix: str = "a") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    organization = OrganizationProfile(
        legal_name=f"PR-05 Organization {suffix}",
        organization_slug=f"pr05-{suffix}-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    db.add(organization)
    db.flush()
    actor = User(
        organization_id=organization.id,
        email=f"pr05-{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        full_name="PR-05 Human",
        status=UserStatus.ACTIVE,
    )
    db.add(actor)
    db.flush()
    role = Role(
        code=f"pr05-{suffix}-{uuid.uuid4().hex[:8]}",
        display_name="PR-05 Operator",
        permissions=["project:update"],
    )
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=actor.id, role_id=role.id, is_active=True))
    customer = Customer(
        organization_id=organization.id,
        legal_name=f"PR-05 Customer {suffix}",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(customer)
    db.flush()
    project = Project(
        organization_id=organization.id,
        customer_id=customer.id,
        code=f"PR05-{suffix}-{uuid.uuid4().hex[:6]}",
        name=f"PR-05 Project {suffix}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    db.add(project)
    db.flush()
    user_session = UserSession(
        user_id=actor.id,
        organization_id=organization.id,
        access_token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        csrf_token_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        status="active",
        access_expires_at=now + timedelta(minutes=15),
        idle_expires_at=now + timedelta(hours=1),
        absolute_expires_at=now + timedelta(hours=8),
    )
    db.add(user_session)
    db.commit()
    return {
        "organization": organization,
        "actor": actor,
        "project": project,
        "session": user_session,
    }


def _vault(db: Session, *, active: str = "v1") -> DatabaseCredentialVault:
    return DatabaseCredentialVault(
        db,
        keys={"v1": b"1" * 32, "v2": b"2" * 32},
        active_key_version=active,
    )


def _connect(
    db: Session,
    seeded: dict[str, object],
    *,
    oauth: FakeOAuthClient | None = None,
    graph: FakeGraphGateway | None = None,
) -> tuple[OneDriveConnection, FakeOAuthClient, FakeGraphGateway]:
    oauth = oauth or FakeOAuthClient()
    graph = graph or FakeGraphGateway()
    vault = _vault(db)
    begin_onedrive_authorization(
        db,
        actor=seeded["actor"],
        user_session=seeded["session"],
        oauth_client=oauth,
        credential_vault=vault,
        correlation_id="corr-pr05-connect",
    )
    connection = complete_onedrive_authorization(
        db,
        auth_response={"state": oauth.state, "code": "authorization-code"},
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
        correlation_id="corr-pr05-callback",
    )
    return connection, oauth, graph


def _document(db: Session, seeded: dict[str, object]) -> DocumentRevision:
    return create_document_with_first_revision(
        db,
        actor=seeded["actor"],
        organization_id=seeded["organization"].id,
        project_id=seeded["project"].id,
        document_type="valuation_report",
        title="Báo cáo thẩm định",
        data_snapshot_digest_sha256=SNAPSHOT_DIGEST,
        content_checksum_sha256=CONTENT_CHECKSUM,
        idempotency_key="document-command-1",
        correlation_id="corr-pr05-document",
    )


def _assert_error(exc: pytest.ExceptionInfo[HTTPException], status: int, code: str) -> None:
    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == code


def test_vault_encrypts_binds_owner_and_rotates_without_plaintext(db: Session) -> None:
    seeded = _seed(db)
    organization = seeded["organization"]
    actor = seeded["actor"]
    secret = b"refresh-token-value-never-persist-plain"
    old_vault = _vault(db, active="v1")
    credential_id = old_vault.store(
        organization_id=organization.id,
        user_id=actor.id,
        purpose="token_cache",
        plaintext=secret,
    )
    db.commit()

    row = db.get(M365EncryptedCredential, credential_id)
    assert row.key_version == "v1"
    assert row.ciphertext != secret
    assert secret not in row.ciphertext
    with pytest.raises(CredentialVaultError):
        old_vault.load(
            organization_id=uuid.uuid4(),
            user_id=actor.id,
            credential_id=credential_id,
            purpose="token_cache",
        )

    rotated_vault = _vault(db, active="v2")
    assert rotated_vault.load(
        organization_id=organization.id,
        user_id=actor.id,
        credential_id=credential_id,
        purpose="token_cache",
    ) == secret
    db.commit()
    db.refresh(row)
    assert row.key_version == "v2"
    assert row.ciphertext != secret

    replacement = b"replacement-refresh-token"
    rotated_vault.replace(
        organization_id=organization.id,
        user_id=actor.id,
        credential_id=credential_id,
        purpose="token_cache",
        plaintext=replacement,
    )
    db.commit()
    assert rotated_vault.load(
        organization_id=organization.id,
        user_id=actor.id,
        credential_id=credential_id,
        purpose="token_cache",
    ) == replacement
    db.refresh(row)
    assert row.key_version == "v2"
    assert replacement not in row.ciphertext


def test_authorization_state_is_single_use_and_secrets_never_enter_audit(
    db: Session,
) -> None:
    seeded = _seed(db)
    oauth = FakeOAuthClient()
    graph = FakeGraphGateway()
    vault = _vault(db)
    url = begin_onedrive_authorization(
        db,
        actor=seeded["actor"],
        user_session=seeded["session"],
        oauth_client=oauth,
        credential_vault=vault,
        correlation_id="corr-pr05-start",
    )
    state_row = db.query(M365OAuthState).one()
    assert oauth.state not in state_row.state_hash
    assert state_row.state_hash == hashlib.sha256(oauth.state.encode()).hexdigest()
    assert url.startswith("https://login.microsoftonline.com/consumers")
    assert FLOW_SECRET not in state_row.state_hash.encode()

    connection = complete_onedrive_authorization(
        db,
        auth_response={"state": oauth.state, "code": "authorization-code"},
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
        correlation_id="corr-pr05-complete",
    )
    db.refresh(state_row)
    assert state_row.consumed_at is not None
    assert state_row.flow_credential_id is None
    assert connection.drive_id == "personal-drive-1"
    assert vault.load(
        organization_id=seeded["organization"].id,
        user_id=seeded["actor"].id,
        credential_id=connection.credential_id,
        purpose="token_cache",
    ) == TOKEN_CACHE_SECRET

    with pytest.raises(HTTPException) as replay:
        complete_onedrive_authorization(
            db,
            auth_response={"state": oauth.state, "code": "authorization-code"},
            oauth_client=oauth,
            graph_gateway=graph,
            credential_vault=vault,
        )
    _assert_error(replay, 400, "onedrive_oauth_state_invalid")
    serialized_audits = repr([row.payload for row in db.query(AuditEvent).all()])
    assert "authorization-code" not in serialized_audits
    assert "refresh-secret" not in serialized_audits
    assert "ephemeral-access-token" not in serialized_audits


def test_authorization_rejects_non_personal_drive_after_consuming_state(
    db: Session,
) -> None:
    seeded = _seed(db)
    oauth = FakeOAuthClient()
    graph = FakeGraphGateway()
    graph.drive = GraphDrive(drive_id="business-drive", drive_type="business")
    vault = _vault(db)
    begin_onedrive_authorization(
        db,
        actor=seeded["actor"],
        user_session=seeded["session"],
        oauth_client=oauth,
        credential_vault=vault,
    )
    with pytest.raises(HTTPException) as rejected:
        complete_onedrive_authorization(
            db,
            auth_response={"state": oauth.state, "code": "authorization-code"},
            oauth_client=oauth,
            graph_gateway=graph,
            credential_vault=vault,
        )
    _assert_error(rejected, 409, "onedrive_account_type_mismatch")
    assert db.query(OneDriveConnection).count() == 0
    assert db.query(M365OAuthState).one().consumed_at is not None


def test_reauthorization_rejects_microsoft_account_switch(db: Session) -> None:
    seeded = _seed(db)
    connection, _, graph = _connect(db, seeded)
    second_oauth = FakeOAuthClient()
    second_oauth.subject = "different-personal-subject"
    vault = _vault(db)
    begin_onedrive_authorization(
        db,
        actor=seeded["actor"],
        user_session=seeded["session"],
        oauth_client=second_oauth,
        credential_vault=vault,
    )
    with pytest.raises(HTTPException) as switched:
        complete_onedrive_authorization(
            db,
            auth_response={"state": second_oauth.state, "code": "authorization-code"},
            oauth_client=second_oauth,
            graph_gateway=graph,
            credential_vault=vault,
        )
    _assert_error(switched, 409, "onedrive_account_switch_forbidden")
    db.refresh(connection)
    assert connection.microsoft_account_subject == "personal-subject-1"


def test_document_creation_is_atomic_idempotent_and_tenant_scoped(db: Session) -> None:
    seeded = _seed(db)
    revision = _document(db, seeded)
    replay = _document(db, seeded)
    assert replay.id == revision.id
    assert db.query(DocumentRecord).count() == 1
    assert db.query(DocumentRevision).count() == 1
    assert db.query(DocumentRevisionCurrentHead).one().current_revision_id == revision.id
    assert db.query(AuditEvent).filter_by(
        event_name="DOCUMENT_REVISION_CREATED"
    ).count() == 1

    with pytest.raises(HTTPException) as conflict:
        create_document_with_first_revision(
            db,
            actor=seeded["actor"],
            organization_id=seeded["organization"].id,
            project_id=seeded["project"].id,
            document_type="valuation_report",
            title="Tên khác",
            data_snapshot_digest_sha256=SNAPSHOT_DIGEST,
            content_checksum_sha256=CONTENT_CHECKSUM,
            idempotency_key="document-command-1",
        )
    _assert_error(conflict, 409, "idempotency_key_reused")

    foreign = _seed(db, suffix="foreign")
    with pytest.raises(HTTPException) as hidden:
        create_document_with_first_revision(
            db,
            actor=foreign["actor"],
            organization_id=foreign["organization"].id,
            project_id=seeded["project"].id,
            document_type="valuation_report",
            title="Cross tenant",
            data_snapshot_digest_sha256=SNAPSHOT_DIGEST,
            content_checksum_sha256=CONTENT_CHECKSUM,
            idempotency_key="foreign-document-command",
        )
    _assert_error(hidden, 404, "project_not_found")


def test_binding_uses_stable_ids_and_idempotency_skips_second_graph_read(
    db: Session,
) -> None:
    seeded = _seed(db)
    connection, oauth, graph = _connect(db, seeded)
    revision = _document(db, seeded)
    kwargs = {
        "actor": seeded["actor"],
        "organization_id": seeded["organization"].id,
        "project_id": seeded["project"].id,
        "document_id": revision.document_id,
        "document_revision_id": revision.id,
        "expected_document_revision": 1,
        "connection_id": connection.id,
        "drive_item_id": "stable-item-id-1",
        "idempotency_key": "binding-command-1",
        "oauth_client": oauth,
        "graph_gateway": graph,
        "credential_vault": _vault(db),
        "correlation_id": "corr-pr05-bind",
    }
    binding = bind_document_revision(db, **kwargs)
    graph.item_name = "Renamed-after-binding.docx"
    graph.item_path = "/drive/root:/Moved/Renamed-after-binding.docx"
    replay = bind_document_revision(db, **kwargs)

    assert replay.id == binding.id
    assert graph.item_calls == 1
    assert binding.drive_id == "personal-drive-1"
    assert binding.drive_item_id == "stable-item-id-1"
    assert binding.name == "Bao-cao.docx"
    assert binding.path == "/drive/root:/Ho-so/Bao-cao.docx"
    assert db.query(M365RevisionBinding).count() == 1
    assert db.query(AuditEvent).filter_by(event_name="M365_REVISION_BOUND").count() == 1

    conflicting = dict(kwargs, drive_item_id="different-item-id")
    with pytest.raises(HTTPException) as conflict:
        bind_document_revision(db, **conflicting)
    _assert_error(conflict, 409, "idempotency_key_reused")


def test_refresh_failure_marks_connection_error_without_leaking_provider_detail(
    db: Session,
) -> None:
    seeded = _seed(db)
    connection, oauth, graph = _connect(db, seeded)
    revision = _document(db, seeded)
    oauth.fail_refresh = True
    with pytest.raises(HTTPException) as unavailable:
        bind_document_revision(
            db,
            actor=seeded["actor"],
            organization_id=seeded["organization"].id,
            project_id=seeded["project"].id,
            document_id=revision.document_id,
            document_revision_id=revision.id,
            expected_document_revision=1,
            connection_id=connection.id,
            drive_item_id="stable-item-id-1",
            idempotency_key="binding-refresh-failure",
            oauth_client=oauth,
            graph_gateway=graph,
            credential_vault=_vault(db),
        )
    _assert_error(unavailable, 502, "onedrive_token_unavailable")
    assert "provider detail" not in str(unavailable.value.detail)
    db.refresh(connection)
    assert connection.status == "error"


class _GraphResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_graph_adapter_fails_closed_for_denied_and_incomplete_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = MicrosoftGraphGateway(timeout_seconds=0.1)

    def denied_get(*args, **kwargs):
        del args, kwargs
        return _GraphResponse(403, {"error": {"message": "provider-sensitive-body"}})

    monkeypatch.setattr("httpx.get", denied_get)
    with pytest.raises(MicrosoftGraphError) as denied:
        gateway.get_default_drive(access_token="secret-access-token")
    assert str(denied.value) == "Microsoft Graph access was denied."
    assert "secret-access-token" not in str(denied.value)
    assert "provider-sensitive-body" not in str(denied.value)

    def incomplete_get(*args, **kwargs):
        del args, kwargs
        return _GraphResponse(
            200,
            {
                "id": "item-1",
                "name": "File.docx",
                "size": 1,
                "file": {},
                "parentReference": {"driveId": "drive-1"},
            },
        )

    monkeypatch.setattr("httpx.get", incomplete_get)
    with pytest.raises(MicrosoftGraphError) as incomplete:
        gateway.get_drive_item(
            access_token="secret-access-token",
            drive_id="drive-1",
            drive_item_id="item-1",
        )
    assert str(incomplete.value) == "Microsoft Graph file metadata is incomplete."


def test_domain_rows_have_no_raw_oauth_secret_columns() -> None:
    forbidden = {
        "access_token",
        "authorization_code",
        "client_secret",
        "refresh_token",
        "token_cache",
    }
    for model in (OneDriveConnection, M365OAuthState, M365RevisionBinding):
        assert forbidden.isdisjoint(model.__table__.columns.keys())


def test_oauth_callback_query_is_redacted_for_access_log_but_reaches_app() -> None:
    callback_query = b"code=authorization-code&client_info=profile&state=oauth-state"
    observed: dict[str, object] = {}

    async def inner_app(scope, receive, send) -> None:
        del receive
        observed["app_query_string"] = scope["query_string"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        del message

    server_scope = {
        "type": "http",
        "path": "/api/v1/m365/onedrive/oauth/callback",
        "query_string": callback_query,
    }
    middleware = OAuthCallbackAccessLogRedactionMiddleware(inner_app)
    asyncio.run(middleware(server_scope, receive, send))

    assert observed["app_query_string"] == callback_query
    assert server_scope["query_string"] == REDACTED_QUERY_STRING
    assert b"authorization-code" not in server_scope["query_string"]
