import hashlib
import secrets
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.config import get_settings
from app.core.security import verify_password
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
    
    # Secure flag is always True in production, and for local dev it matches SSL config.
    # To run on localhost without SSL, secure can be False in local env if needed,
    # but we follow: "Secure cookie luôn bật ở production, local development policy riêng"
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
    # CSRF cookie is non-HttpOnly so frontend client can read it to send back in header
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


# Validate CSRF Token
def validate_csrf(request: Request, db_session: UserSession):
    # Synchronizer token validation
    client_csrf = request.headers.get("X-CSRF-Token")
    if not client_csrf:
        raise HTTPException(
            status_code=401,
            detail={
                "title": "Thiếu mã xác thực CSRF",
                "message": "Không tìm thấy mã xác thực CSRF hợp lệ.",
                "nextAction": "Vui lòng làm mới trang và thử lại.",
                "severity": "error",
                "retryable": True
            }
        )
    
    if not db_session.csrf_token_hash:
        raise_401("Mã xác thực CSRF của phiên làm việc không tồn tại.")
        
    client_csrf_hash = hash_token(client_csrf)
    if not hmac.compare_digest(client_csrf_hash, db_session.csrf_token_hash):
        raise HTTPException(
            status_code=401,
            detail={
                "title": "Mã xác thực CSRF không hợp lệ",
                "message": "Mã xác thực CSRF gửi lên không khớp với phiên làm việc.",
                "nextAction": "Vui lòng làm mới trang và thử lại.",
                "severity": "error",
                "retryable": True
            }
        )

    # Origin and Referer checks
    origin = request.headers.get("Origin")
    host = request.headers.get("Host")
    if origin and host and host not in origin:
        raise_403("Yêu cầu bị từ chối do nguồn gốc (Origin) không hợp lệ.")
    
    # Fetch Metadata checks (Sec-Fetch-Site should be same-origin)
    sec_fetch_site = request.headers.get("Sec-Fetch-Site")
    if sec_fetch_site and sec_fetch_site not in ["same-origin", "none"]:
        raise_403("Yêu cầu bị từ chối do chính sách bảo mật nguồn gốc.")


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
        absolute_expires_at=now + timedelta(days=7),  # 7 days max absolute lifespan
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )
    db.add(user_session)
    db.flush()  # get session ID
    
    # Create RefreshTokenRecord
    ref_record = RefreshTokenRecord(
        user_session_id=user_session.id,
        token_hash=ref_hash,
        token_family_id=uuid.uuid4(),  # unique family ID
        status="active",
        issued_at=now,
        expires_at=now + timedelta(days=30)
    )
    db.add(ref_record)
    
    # Update user last_login_at
    user.last_login_at = now
    
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
        raise_401("Không tìm thấy token làm mới phiên.")
        
    ref_hash = hash_token(refresh_token)
    
    # Lock the record for concurrent safety
    ref_record = db.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.token_hash == ref_hash
    ).with_for_update().first()
    
    if not ref_record:
        raise_401("Token làm mới phiên không hợp lệ.")
        
    # Check reuse detection
    if ref_record.status != "active":
        # REUSE DETECTED! Revoke the entire session and family
        session = db.query(UserSession).filter(
            UserSession.id == ref_record.user_session_id
        ).with_for_update().first()
        if session:
            session.status = "revoked"
            session.revoked_reason = "Phát hiện sử dụng lại token làm mới phiên cũ."
            session.revoked_at = datetime.now(timezone.utc)
            
        db.query(RefreshTokenRecord).filter(
            RefreshTokenRecord.user_session_id == ref_record.user_session_id
        ).update({
            "status": "revoked",
            "revoked_at": datetime.now(timezone.utc)
        })
        db.commit()
        clear_auth_cookies(response)
        raise_401("Token làm mới phiên đã được sử dụng trước đó. Tất cả các phiên đã bị thu hồi vì lý do bảo mật.")

    # Check expiration
    now = datetime.now(timezone.utc)
    if ref_record.expires_at.replace(tzinfo=timezone.utc) < now:
        ref_record.status = "revoked"
        db.commit()
        clear_auth_cookies(response)
        raise_401("Phiên làm mới đã hết hạn.")
        
    session = db.query(UserSession).filter(
        UserSession.id == ref_record.user_session_id,
        UserSession.status == "active"
    ).with_for_update().first()
    
    if not session:
        clear_auth_cookies(response)
        raise_401("Phiên làm việc của token này đã bị khóa hoặc hết hạn.")
        
    # Verify active status
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or user.status != UserStatus.ACTIVE:
        clear_auth_cookies(response)
        raise_401("Tài khoản của bạn đã bị vô hiệu hóa.")
        
    org = user.organization
    if not org or org.status != OrganizationStatus.ACTIVE:
        clear_auth_cookies(response)
        raise_401("Tổ chức của bạn đã bị vô hiệu hóa.")

    # Validate CSRF during state mutation endpoint /refresh
    validate_csrf(request, session)

    # All checks passed. Perform rotation
    new_access_token = secrets.token_hex(32)
    new_refresh_token = secrets.token_hex(32)
    
    new_acc_hash = hash_token(new_access_token)
    new_ref_hash = hash_token(new_refresh_token)
    
    # Update old record
    ref_record.status = "rotated"
    ref_record.rotated_at = now
    ref_record.consumed_at = now
    
    # Create new record
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
    
    # Update session access token
    session.access_token_hash = new_acc_hash
    session.access_expires_at = now + timedelta(minutes=15)
    session.idle_expires_at = now + timedelta(minutes=30)
    session.last_seen_at = now
    
    db.commit()
    
    # Read existing CSRF from DB to pass along
    # Wait, we can rotate the CSRF token on refresh too or reuse it.
    # Let's rotate CSRF token on refresh for maximum security!
    new_csrf_token = generate_csrf_token()
    session.csrf_token_hash = hash_token(new_csrf_token)
    db.commit()
    
    set_auth_cookies(response, new_access_token, new_refresh_token, new_csrf_token)
    return {"status": "ok", "message": "Làm mới phiên thành công."}


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    session: UserSession = Depends(get_current_session)
):
    # Validate CSRF during logout state mutation
    validate_csrf(request, session)

    # Revoke DB session
    session.status = "revoked"
    session.revoked_at = datetime.now(timezone.utc)
    session.revoked_reason = "Người dùng đăng xuất."
    
    # Revoke tokens associated
    db.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id
    ).update({
        "status": "revoked",
        "revoked_at": datetime.now(timezone.utc)
    })
    
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
    
    # Derive permissions
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
    # Return CSRF token cookie. If user has active session, set/renew it.
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
            # Enforce CSRF token sync in DB
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
