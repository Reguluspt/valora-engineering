import hashlib
import secrets
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.config import get_settings
from app.core.security import verify_password
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User,
    OrganizationProfile,
    UserSession,
    RefreshTokenRecord,
    OrganizationStatus,
    UserStatus
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()

class LoginRequest(BaseModel):
    organization_slug: str
    email: str
    password: str

class UserMeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    organization_id: str
    organization_slug: str
    status: str
    roles: list[str]
    permissions: list[str]

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_cookie_keys():
    if settings.valora_env == "production":
        return "__Host-Access-Token", "__Host-Refresh-Token"
    return "access_token", "refresh_token"

def raise_401(message: str = "Phiên làm việc hết hạn hoặc không hợp lệ."):
    raise HTTPException(
        status_code=401,
        detail={
            "title": "Phiên làm việc hết hạn",
            "message": message,
            "nextAction": "Vui lòng đăng nhập lại để tiếp tục sử dụng hệ thống.",
            "severity": "blocking",
            "retryable": False
        }
    )

def raise_403(message: str = "Tài khoản của bạn không được cấp quyền thực hiện thao tác này."):
    raise HTTPException(
        status_code=403,
        detail={
            "code": "CSRF_ERROR",
            "title": "Không có quyền thực hiện",
            "message": message,
            "nextAction": "Vui lòng liên hệ với Quản trị viên để được hỗ trợ.",
            "severity": "error",
            "retryable": False
        }
    )

def generate_csrf_token() -> str:
    return secrets.token_hex(32)

def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str
):
    acc_key, ref_key = get_cookie_keys()
    is_prod = settings.valora_env == "production"
    secure_cookie = True if is_prod else False

    response.set_cookie(
        key=acc_key,
        value=access_token,
        max_age=900,  # 15m
        httponly=True,
        secure=secure_cookie,
        samesite="strict",
        path="/"
    )
    response.set_cookie(
        key=ref_key,
        value=refresh_token,
        max_age=2592000,  # 30d
        httponly=True,
        secure=secure_cookie,
        samesite="strict",
        path="/"
    )
    response.set_cookie(
        key="XSRF-TOKEN",
        value=csrf_token,
        max_age=2592000,
        httponly=False,
        secure=secure_cookie,
        samesite="strict",
        path="/"
    )

def clear_auth_cookies(response: Response):
    acc_key, ref_key = get_cookie_keys()
    is_prod = settings.valora_env == "production"
    secure_cookie = True if is_prod else False

    response.delete_cookie(key=acc_key, path="/", samesite="strict", secure=secure_cookie, httponly=True)
    response.delete_cookie(key=ref_key, path="/", samesite="strict", secure=secure_cookie, httponly=True)
    response.delete_cookie(key="XSRF-TOKEN", path="/", samesite="strict", secure=secure_cookie, httponly=False)

def make_cookie_clearing_response(message: str) -> JSONResponse:
    res = JSONResponse(
        status_code=401,
        content={
            "detail": {
                "title": "Phiên làm việc hết hạn",
                "message": message,
                "nextAction": "Vui lòng đăng nhập lại để tiếp tục sử dụng hệ thống.",
                "severity": "blocking",
                "retryable": False
            }
        }
    )
    clear_auth_cookies(res)
    return res

def verify_origin(origin_str: str, allowed_origins: list[str]) -> bool:
    if not origin_str:
        return False
    try:
        parsed_incoming = urlparse(origin_str)
        # Handle case where scheme or hostname is empty due to malformed URLs
        if not parsed_incoming.scheme or not parsed_incoming.hostname:
            return False
        incoming_key = (parsed_incoming.scheme, parsed_incoming.hostname, parsed_incoming.port)
        
        for allowed in allowed_origins:
            parsed_allowed = urlparse(allowed)
            allowed_key = (parsed_allowed.scheme, parsed_allowed.hostname, parsed_allowed.port)
            if incoming_key == allowed_key:
                return True
    except Exception:
        pass
    return False

# Validate CSRF Token
def validate_csrf(request: Request, db_session: UserSession):
    # Enforce stable application error code for missing/invalid CSRF
    client_csrf = request.headers.get("X-CSRF-Token")
    if not client_csrf:
        raise_403("Thiếu mã xác thực CSRF.")
    
    if not db_session.csrf_token_hash:
        raise_403("Mã xác thực CSRF của phiên làm việc không tồn tại.")
        
    client_csrf_hash = hash_token(client_csrf)
    if not hmac.compare_digest(client_csrf_hash, db_session.csrf_token_hash):
        raise_403("Mã xác thực CSRF không hợp lệ.")

    # Parse and compare scheme, hostname, port exactly against CORS allowed origins
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    
    allowed_origins = settings.parsed_cors_origins
    
    if origin:
        if not verify_origin(origin, allowed_origins):
            raise_403("Yêu cầu bị từ chối do nguồn gốc (Origin) không hợp lệ.")
    elif referer:
        if not verify_origin(referer, allowed_origins):
            raise_403("Yêu cầu bị từ chối do nguồn tham chiếu (Referer) không hợp lệ.")
    else:
        # Fail-closed policy: unsafe browsers mutating requests must provide origin or referer
        raise_403("Yêu cầu bị từ chối do thiếu thông tin nguồn gốc yêu cầu.")

    # Fetch Metadata check as defense-in-depth only
    sec_fetch_site = request.headers.get("Sec-Fetch-Site")
    if sec_fetch_site and sec_fetch_site not in ["same-origin", "none"]:
        raise_403("Yêu cầu bị từ chối do chính sách bảo mật nguồn gốc.")

# Central CSRF Gate dependency for POST/PUT/PATCH/DELETE protected routes
async def csrf_gate(request: Request, db: Session = Depends(get_db)):
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return
        
    path = request.url.path
    # Exempt login and health/read endpoints
    if path in [
        "/api/v1/auth/login",
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc"
    ]:
        return

    acc_key, _ = get_cookie_keys()
    access_token = request.cookies.get(acc_key)
    if not access_token:
        # No access token -> let authentication gate handle it via 401
        return

    acc_hash = hash_token(access_token)
    session = db.query(UserSession).filter(
        UserSession.access_token_hash == acc_hash,
        UserSession.status == "active"
    ).first()
    
    if not session:
        return

    validate_csrf(request, session)

# Dependency to resolve current active user session
def get_current_session(
    request: Request,
    db: Session = Depends(get_db)
) -> UserSession:
    acc_key, _ = get_cookie_keys()
    access_token = request.cookies.get(acc_key)
    
    if not access_token:
        raise_401("Không tìm thấy thông tin đăng nhập.")
        
    acc_hash = hash_token(access_token)
    
    session = db.query(UserSession).filter(
        UserSession.access_token_hash == acc_hash,
        UserSession.status == "active"
    ).first()
    
    if not session:
        raise_401("Phiên làm việc không tồn tại hoặc đã bị thu hồi.")
        
    now = datetime.now(timezone.utc)
    if session.access_expires_at.replace(tzinfo=timezone.utc) < now:
        raise_401("Phiên đăng nhập đã hết hạn.")
        
    if session.idle_expires_at.replace(tzinfo=timezone.utc) < now:
        session.status = "expired"
        db.commit()
        raise_401("Phiên làm việc đã hết hạn do không hoạt động.")
        
    if session.absolute_expires_at.replace(tzinfo=timezone.utc) < now:
        session.status = "expired"
        db.commit()
        raise_401("Thời gian phiên làm việc tối đa đã hết hạn.")

    # Validate active user & organization status
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or user.status != UserStatus.ACTIVE:
        raise_401("Tài khoản của bạn đã bị vô hiệu hóa hoặc không tồn tại.")
        
    org = user.organization
    if not org or org.status != OrganizationStatus.ACTIVE:
        raise_401("Tổ chức của bạn đã bị vô hiệu hóa.")

    # Update last_seen_at and idle_expires_at (sliding window)
    session.last_seen_at = now
    session.idle_expires_at = now + timedelta(minutes=30)
    db.commit()
    
    return session


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    # Lookup org
    org = db.query(OrganizationProfile).filter(
        OrganizationProfile.organization_slug == payload.organization_slug,
        OrganizationProfile.status == OrganizationStatus.ACTIVE
    ).first()
    if not org:
        raise_401("Tên tổ chức hoặc thông tin đăng nhập không chính xác.")
        
    # Lookup user
    user = db.query(User).filter(
        User.organization_id == org.id,
        User.email == payload.email,
        User.status == UserStatus.ACTIVE
    ).first()
    if not user:
        raise_401("Tên tổ chức hoặc thông tin đăng nhập không chính xác.")
        
    # Verify password
    if not verify_password(payload.password, user.password_hash):
        raise_401("Tên tổ chức hoặc thông tin đăng nhập không chính xác.")
        
    # User authenticated. Generate tokens
    access_token = secrets.token_hex(32)
    refresh_token = secrets.token_hex(32)
    csrf_token = generate_csrf_token()
    
    acc_hash = hash_token(access_token)
    ref_hash = hash_token(refresh_token)
    csrf_hash = hash_token(csrf_token)
    
    now = datetime.now(timezone.utc)
    
    # Create UserSession
    user_session = UserSession(
        user_id=user.id,
        organization_id=org.id,
        access_token_hash=acc_hash,
        csrf_token_hash=csrf_hash,
        status="active",
        created_at=now,
        last_seen_at=now,
        access_expires_at=now + timedelta(minutes=15),
        idle_expires_at=now + timedelta(minutes=30),
        absolute_expires_at=now + timedelta(days=7),
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(user_session)
    db.flush()
    
    # Create RefreshTokenRecord
    ref_record = RefreshTokenRecord(
        user_session_id=user_session.id,
        token_hash=ref_hash,
        token_family_id=uuid.uuid4(),
        status="active",
        issued_at=now,
        expires_at=now + timedelta(days=30)
    )
    db.add(ref_record)
    
    # Update user last_login_at
    user.last_login_at = now
    
    # Audit log session creation
    log_audit_event(
        db=db,
        event_name="auth.session.created",
        entity_type="UserSession",
        entity_id=user_session.id,
        organization_id=org.id,
        actor_user_id=user.id,
        payload={"session_id": str(user_session.id)}
    )
    
    db.commit()
    
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    return {"status": "ok", "message": "Đăng nhập thành công."}


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    _, ref_key = get_cookie_keys()
    refresh_token = request.cookies.get(ref_key)
    if not refresh_token:
        return make_cookie_clearing_response("Không tìm thấy token làm mới phiên.")
        
    ref_hash = hash_token(refresh_token)
    
    # Start atomic transaction block
    try:
        # Lock current refresh token for concurrency safety
        ref_record = db.query(RefreshTokenRecord).filter(
            RefreshTokenRecord.token_hash == ref_hash
        ).with_for_update().first()
        
        if not ref_record:
            return make_cookie_clearing_response("Token làm mới phiên không hợp lệ.")
            
        # Check reuse detection
        if ref_record.status != "active":
            # REUSE DETECTED!
            # Revoke correct token_family_id and session
            session = db.query(UserSession).filter(
                UserSession.id == ref_record.user_session_id
            ).with_for_update().first()
            if session:
                session.status = "revoked"
                session.revoked_reason = "Phát hiện sử dụng lại token làm mới phiên cũ."
                session.revoked_at = datetime.now(timezone.utc)
                
            db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.user_session_id == ref_record.user_session_id,
                RefreshTokenRecord.token_family_id == ref_record.token_family_id
            ).update({
                "status": "revoked",
                "revoked_at": datetime.now(timezone.utc)
            })
            
            # Set reuse detected at
            ref_record.reuse_detected_at = datetime.now(timezone.utc)
            ref_record.status = "reused_detected"
            
            log_audit_event(
                db=db,
                event_name="auth.refresh.reuse_detected",
                entity_type="RefreshTokenRecord",
                entity_id=ref_record.id,
                organization_id=session.organization_id if session else None,
                actor_user_id=session.user_id if session else None,
                payload={"token_family_id": str(ref_record.token_family_id)}
            )
            
            db.commit()
            return make_cookie_clearing_response("Token làm mới phiên đã được sử dụng trước đó. Tất cả phiên đã bị thu hồi.")

        # Validate session and expiry timeouts
        session = db.query(UserSession).filter(
            UserSession.id == ref_record.user_session_id,
            UserSession.status == "active"
        ).with_for_update().first()
        
        now = datetime.now(timezone.utc)
        is_expired = False
        expire_reason = ""
        
        if not session:
            is_expired = True
            expire_reason = "Phiên làm việc không tồn tại hoặc đã bị thu hồi."
        elif session.idle_expires_at.replace(tzinfo=timezone.utc) < now:
            is_expired = True
            expire_reason = "Phiên làm việc đã hết hạn do không hoạt động (idle timeout)."
            session.status = "expired"
        elif session.absolute_expires_at.replace(tzinfo=timezone.utc) < now:
            is_expired = True
            expire_reason = "Thời gian phiên làm việc tối đa đã hết (absolute timeout)."
            session.status = "expired"
            
        if ref_record.expires_at.replace(tzinfo=timezone.utc) < now:
            is_expired = True
            expire_reason = "Token làm mới phiên đã hết hạn."
            ref_record.status = "revoked"
            
        user = None
        if session:
            user = db.query(User).filter(User.id == session.user_id).first()
            if not user or user.status != UserStatus.ACTIVE:
                is_expired = True
                expire_reason = "Tài khoản của bạn đã bị vô hiệu hóa."
            else:
                org = user.organization
                if not org or org.status != OrganizationStatus.ACTIVE:
                    is_expired = True
                    expire_reason = "Tổ chức của bạn đã bị vô hiệu hóa."
                    
        if is_expired:
            if session:
                session.status = "revoked"
                session.revoked_at = now
                session.revoked_reason = expire_reason
            ref_record.status = "revoked"
            ref_record.revoked_at = now
            
            db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.user_session_id == ref_record.user_session_id,
                RefreshTokenRecord.token_family_id == ref_record.token_family_id
            ).update({
                "status": "revoked",
                "revoked_at": now
            })
            db.commit()
            return make_cookie_clearing_response(expire_reason)

        # CSRF check
        validate_csrf(request, session)

        # Perform atomic rotation
        new_access_token = secrets.token_hex(32)
        new_refresh_token = secrets.token_hex(32)
        new_csrf_token = generate_csrf_token()
        
        new_acc_hash = hash_token(new_access_token)
        new_ref_hash = hash_token(new_refresh_token)
        new_csrf_hash = hash_token(new_csrf_token)
        
        # Update old token
        ref_record.status = "rotated"
        ref_record.rotated_at = now
        ref_record.consumed_at = now
        
        # Create new token record
        new_ref_record = RefreshTokenRecord(
            user_session_id=session.id,
            token_hash=new_ref_hash,
            token_family_id=ref_record.token_family_id,
            parent_token_id=ref_record.id,
            status="active",
            issued_at=now,
            expires_at=now + timedelta(days=30)
        )
        db.add(new_ref_record)
        db.flush()
        
        # Set parent reference to replacement token
        ref_record.replaced_by_token_id = new_ref_record.id
        
        # Rotate session
        session.access_token_hash = new_acc_hash
        session.csrf_token_hash = new_csrf_hash
        session.access_expires_at = now + timedelta(minutes=15)
        session.idle_expires_at = now + timedelta(minutes=30)
        session.last_seen_at = now
        
        # Log audit event auth.session.refreshed
        log_audit_event(
            db=db,
            event_name="auth.session.refreshed",
            entity_type="UserSession",
            entity_id=session.id,
            organization_id=session.organization_id,
            actor_user_id=session.user_id,
            payload={"session_id": str(session.id)}
        )
        
        db.commit()
        
        res = JSONResponse(content={"status": "ok", "message": "Làm mới phiên thành công."})
        set_auth_cookies(res, new_access_token, new_refresh_token, new_csrf_token)
        return res
        
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        return make_cookie_clearing_response("Lỗi xử lý hệ thống trong quá trình làm mới phiên.")


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    session: UserSession = Depends(get_current_session)
):
    validate_csrf(request, session)

    session.status = "revoked"
    session.revoked_at = datetime.now(timezone.utc)
    session.revoked_reason = "Người dùng đăng xuất."
    
    db.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id
    ).update({
        "status": "revoked",
        "revoked_at": datetime.now(timezone.utc)
    })
    
    log_audit_event(
        db=db,
        event_name="auth.session.revoked",
        entity_type="UserSession",
        entity_id=session.id,
        organization_id=session.organization_id,
        actor_user_id=session.user_id,
        payload={"session_id": str(session.id), "reason": "User logged out"}
    )
    
    db.commit()
    clear_auth_cookies(response)
    return {"status": "ok", "message": "Đăng xuất thành công."}


@router.get("/me", response_model=UserMeResponse)
def me(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == session.user_id).first()
    org = user.organization
    
    from app.core.rbac import derive_effective_permissions
    perms = derive_effective_permissions(user, db)
    
    roles_list = [ur.role.code for ur in user.roles if ur.is_active and ur.revoked_at is None and ur.role]
    
    return UserMeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        organization_id=str(org.id),
        organization_slug=org.organization_slug,
        status=user.status.value if hasattr(user.status, "value") else user.status,
        roles=roles_list,
        permissions=list(perms)
    )


@router.get("/csrf")
def get_csrf(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    acc_key, _ = get_cookie_keys()
    access_token = request.cookies.get(acc_key)
    
    csrf_token = generate_csrf_token()
    
    if access_token:
        acc_hash = hash_token(access_token)
        session = db.query(UserSession).filter(
            UserSession.access_token_hash == acc_hash,
            UserSession.status == "active"
        ).first()
        if session:
            session.csrf_token_hash = hash_token(csrf_token)
            db.commit()
            
    is_prod = settings.valora_env == "production"
    secure_cookie = True if is_prod else False
    
    response.set_cookie(
        key="XSRF-TOKEN",
        value=csrf_token,
        max_age=2592000,
        httponly=False,
        secure=secure_cookie,
        samesite="strict",
        path="/"
    )
    
    return {"csrfToken": csrf_token}
