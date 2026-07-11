import uuid
import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User,
    Customer,
    CustomerAlias,
    CustomerStatus,
    Supplier,
    SupplierAlias,
    SupplierStatus,
    Country,
    Province,
    ReferenceStatus,
    Brand,
    BrandStatus,
    Manufacturer,
    ManufacturerStatus,
    Unit,
    Currency,
    SignerProfile,
    SignerStatus
)
from app.modules.project_master_data.schemas import (
    CountryCreate, CountryResponse,
    ProvinceCreate, ProvinceResponse,
    UnitCreate, UnitResponse,
    CurrencyCreate, CurrencyResponse,
    BrandCreate, BrandResponse,
    ManufacturerCreate, ManufacturerResponse,
    SignerProfileCreate, SignerProfileUpdate, SignerProfileResponse,
    CustomerCreate, CustomerUpdate, CustomerDeactivate, CustomerMerge, CustomerResponse,
    SupplierCreate, SupplierUpdate, SupplierDeactivate, SupplierMerge, SupplierResponse
)

router = APIRouter(prefix="/api/v1/master-data", tags=["master-data"])


# Normalization helper for name matching
def normalize_name(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r'[^\w\s]', '', n)  # remove punctuation
    n = re.sub(r'\s+', ' ', n)  # collapse spaces
    return n


def get_fuzzy_duplicate_customer_warning(db: Session, org_id: uuid.UUID, name: str, exclude_id: Optional[uuid.UUID] = None) -> Optional[str]:
    normalized_target = normalize_name(name)
    query = db.query(Customer).filter(Customer.organization_id == org_id)
    if exclude_id:
        query = query.filter(Customer.id != exclude_id)
    customers = query.all()
    for cust in customers:
        if normalize_name(cust.legal_name) == normalized_target:
            return f"Fuzzy duplicate customer found: {cust.legal_name}"
    return None


def get_fuzzy_duplicate_supplier_warning(db: Session, org_id: uuid.UUID, name: str, exclude_id: Optional[uuid.UUID] = None) -> Optional[str]:
    normalized_target = normalize_name(name)
    query = db.query(Supplier).filter(Supplier.organization_id == org_id)
    if exclude_id:
        query = query.filter(Supplier.id != exclude_id)
    suppliers = query.all()
    for supp in suppliers:
        if normalize_name(supp.legal_name) == normalized_target:
            return f"Fuzzy duplicate supplier found: {supp.legal_name}"
    return None


# ==========================================
# CUSTOMER ENDPOINTS
# ==========================================

@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:customer:create"))
):
    # 1. Scope to current_user.organization_id
    org_id = current_user.organization_id

    # 2. Check if tax code is unique in org (if provided)
    if payload.tax_code:
        dup = db.query(Customer).filter(
            Customer.organization_id == org_id,
            Customer.tax_code == payload.tax_code
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail="Duplicate record (tax code already exists)")

    # 3. Check if province exists
    if payload.province_id:
        prov = db.query(Province).filter(Province.id == payload.province_id).first()
        if not prov:
            raise HTTPException(status_code=404, detail="Reference record not found (province)")

    # 4. Normalization warning check
    warning = get_fuzzy_duplicate_customer_warning(db, org_id, payload.legal_name)
    warnings_list = [warning] if warning else []

    # 5. Save record
    customer = Customer(
        organization_id=org_id,
        legal_name=payload.legal_name,
        display_name=payload.display_name,
        tax_code=payload.tax_code,
        address=payload.address,
        province_id=payload.province_id,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        notes=payload.notes,
        status=CustomerStatus.ACTIVE,
        created_by=current_user.id
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    # 6. Audit log
    log_audit_event(
        db=db,
        event_name="CustomerCreated",
        entity_type="Customer",
        entity_id=customer.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CreateCustomer",
        payload={"legal_name": customer.legal_name}
    )
    db.commit()

    resp = CustomerResponse.model_validate(customer)
    resp.warnings = warnings_list
    return resp


@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    q: Optional[str] = None,
    status: Optional[CustomerStatus] = None,
    province_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:customer:read"))
):
    org_id = current_user.organization_id
    query = db.query(Customer).filter(Customer.organization_id == org_id)

    if q:
        # Search by legal_name, display_name, tax_code
        query = query.filter(
            or_(
                Customer.legal_name.ilike(f"%{q}%"),
                Customer.display_name.ilike(f"%{q}%"),
                Customer.tax_code.ilike(f"%{q}%")
            )
        )
    if status:
        query = query.filter(Customer.status == status)
    if province_id:
        query = query.filter(Customer.province_id == province_id)

    # Simple pagination
    offset = (page - 1) * page_size
    customers = query.offset(offset).limit(page_size).all()
    return customers


@router.patch("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:customer:update"))
):
    org_id = current_user.organization_id
    customer = db.query(Customer).filter(
        Customer.organization_id == org_id,
        Customer.id == customer_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Record not found")

    if payload.province_id:
        prov = db.query(Province).filter(Province.id == payload.province_id).first()
        if not prov:
            raise HTTPException(status_code=404, detail="Reference record not found (province)")

    # Update values
    if payload.display_name is not None:
        customer.display_name = payload.display_name
    if payload.address is not None:
        customer.address = payload.address
    if payload.province_id is not None:
        customer.province_id = payload.province_id
    if payload.contact_phone is not None:
        customer.contact_phone = payload.contact_phone
    if payload.notes is not None:
        customer.notes = payload.notes

    # Warning warning check
    warning = get_fuzzy_duplicate_customer_warning(db, org_id, customer.legal_name, exclude_id=customer.id)
    warnings_list = [warning] if warning else []

    db.commit()
    db.refresh(customer)

    log_audit_event(
        db=db,
        event_name="CustomerUpdated",
        entity_type="Customer",
        entity_id=customer.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="UpdateCustomer",
        payload={"display_name": customer.display_name}
    )
    db.commit()

    resp = CustomerResponse.model_validate(customer)
    resp.warnings = warnings_list
    return resp


@router.post("/customers/{customer_id}/deactivate", response_model=CustomerResponse)
def deactivate_customer(
    customer_id: uuid.UUID,
    payload: CustomerDeactivate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:customer:deactivate"))
):
    org_id = current_user.organization_id
    customer = db.query(Customer).filter(
        Customer.organization_id == org_id,
        Customer.id == customer_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Record not found")

    customer.status = CustomerStatus.INACTIVE
    db.commit()
    db.refresh(customer)

    log_audit_event(
        db=db,
        event_name="CustomerDeactivated",
        entity_type="Customer",
        entity_id=customer.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="DeactivateCustomer",
        payload={"reason": payload.reason}
    )
    db.commit()

    return customer


@router.post("/customers/merge", response_model=CustomerResponse)
def merge_customers(
    payload: CustomerMerge,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:customer:merge"))
):
    org_id = current_user.organization_id
    source = db.query(Customer).filter(Customer.organization_id == org_id, Customer.id == payload.source_customer_id).first()
    target = db.query(Customer).filter(Customer.organization_id == org_id, Customer.id == payload.target_customer_id).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="Record not found")

    if source.status == CustomerStatus.MERGED or target.status in (CustomerStatus.INACTIVE, CustomerStatus.MERGED):
        raise HTTPException(status_code=422, detail="Merge target invalid (target is inactive or already merged)")

    # Set merged properties
    source.status = CustomerStatus.MERGED
    source.merged_into_customer_id = target.id

    # Preserve alias: insert CustomerAlias pointing to target
    alias = CustomerAlias(
        customer_id=target.id,
        alias_name=source.legal_name,
        confidence_score=1.0
    )
    db.add(alias)
    db.commit()

    log_audit_event(
        db=db,
        event_name="CustomerMerged",
        entity_type="Customer",
        entity_id=source.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="MergeCustomer",
        payload={"target_customer_id": str(target.id), "reason": payload.reason}
    )
    db.commit()

    return target


# ==========================================
# SUPPLIER ENDPOINTS
# ==========================================

@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:supplier:create"))
):
    org_id = current_user.organization_id

    if payload.tax_code:
        dup = db.query(Supplier).filter(
            Supplier.organization_id == org_id,
            Supplier.tax_code == payload.tax_code
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail="Duplicate record (tax code already exists)")

    if payload.province_id:
        prov = db.query(Province).filter(Province.id == payload.province_id).first()
        if not prov:
            raise HTTPException(status_code=404, detail="Reference record not found (province)")

    warning = get_fuzzy_duplicate_supplier_warning(db, org_id, payload.legal_name)
    warnings_list = [warning] if warning else []

    supplier = Supplier(
        organization_id=org_id,
        legal_name=payload.legal_name,
        display_name=payload.display_name,
        tax_code=payload.tax_code,
        province_id=payload.province_id,
        reliability_score=payload.reliability_score,
        status=SupplierStatus.ACTIVE,
        created_by=current_user.id
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    log_audit_event(
        db=db,
        event_name="SupplierCreated",
        entity_type="Supplier",
        entity_id=supplier.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CreateSupplier",
        payload={"legal_name": supplier.legal_name}
    )
    db.commit()

    resp = SupplierResponse.model_validate(supplier)
    resp.warnings = warnings_list
    return resp


@router.get("/suppliers", response_model=List[SupplierResponse])
def list_suppliers(
    q: Optional[str] = None,
    status: Optional[SupplierStatus] = None,
    min_reliability: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:supplier:read"))
):
    org_id = current_user.organization_id
    query = db.query(Supplier).filter(Supplier.organization_id == org_id)

    if q:
        query = query.filter(
            or_(
                Supplier.legal_name.ilike(f"%{q}%"),
                Supplier.display_name.ilike(f"%{q}%"),
                Supplier.tax_code.ilike(f"%{q}%")
            )
        )
    if status:
        query = query.filter(Supplier.status == status)
    if min_reliability is not None:
        query = query.filter(Supplier.reliability_score >= min_reliability)

    offset = (page - 1) * page_size
    suppliers = query.offset(offset).limit(page_size).all()
    return suppliers


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:supplier:update"))
):
    org_id = current_user.organization_id
    supplier = db.query(Supplier).filter(
        Supplier.organization_id == org_id,
        Supplier.id == supplier_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Record not found")

    if payload.display_name is not None:
        supplier.display_name = payload.display_name
    if payload.reliability_score is not None:
        supplier.reliability_score = payload.reliability_score

    warning = get_fuzzy_duplicate_supplier_warning(db, org_id, supplier.legal_name, exclude_id=supplier.id)
    warnings_list = [warning] if warning else []

    db.commit()
    db.refresh(supplier)

    log_audit_event(
        db=db,
        event_name="SupplierUpdated",
        entity_type="Supplier",
        entity_id=supplier.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="UpdateSupplier",
        payload={"display_name": supplier.display_name}
    )
    db.commit()

    resp = SupplierResponse.model_validate(supplier)
    resp.warnings = warnings_list
    return resp


@router.post("/suppliers/{supplier_id}/deactivate", response_model=SupplierResponse)
def deactivate_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierDeactivate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:supplier:deactivate"))
):
    org_id = current_user.organization_id
    supplier = db.query(Supplier).filter(
        Supplier.organization_id == org_id,
        Supplier.id == supplier_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Record not found")

    supplier.status = SupplierStatus.INACTIVE
    db.commit()
    db.refresh(supplier)

    log_audit_event(
        db=db,
        event_name="SupplierDeactivated",
        entity_type="Supplier",
        entity_id=supplier.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="DeactivateSupplier",
        payload={"reason": payload.reason}
    )
    db.commit()

    return supplier


@router.post("/suppliers/merge", response_model=SupplierResponse)
def merge_suppliers(
    payload: SupplierMerge,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:supplier:merge"))
):
    org_id = current_user.organization_id
    source = db.query(Supplier).filter(Supplier.organization_id == org_id, Supplier.id == payload.source_supplier_id).first()
    target = db.query(Supplier).filter(Supplier.organization_id == org_id, Supplier.id == payload.target_supplier_id).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="Record not found")

    if source.status == SupplierStatus.MERGED or target.status in (SupplierStatus.INACTIVE, SupplierStatus.MERGED):
        raise HTTPException(status_code=422, detail="Merge target invalid")

    source.status = SupplierStatus.MERGED
    source.merged_into_supplier_id = target.id

    # Preserve alias
    alias = SupplierAlias(
        supplier_id=target.id,
        alias_name=source.legal_name,
        confidence_score=1.0
    )
    db.add(alias)
    db.commit()

    log_audit_event(
        db=db,
        event_name="SupplierMerged",
        entity_type="Supplier",
        entity_id=source.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="MergeSupplier",
        payload={"target_supplier_id": str(target.id), "reason": payload.reason}
    )
    db.commit()

    return target


# ==========================================
# COUNTRY ENDPOINTS
# ==========================================

@router.post("/countries", response_model=CountryResponse, status_code=201)
def create_country(
    payload: CountryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:reference:create"))
):
    # Check uniqueness of iso2 and iso3 if provided
    if payload.iso2:
        dup = db.query(Country).filter(Country.iso2 == payload.iso2).first()
        if dup:
            raise HTTPException(status_code=409, detail="Duplicate country iso2")
    if payload.iso3:
        dup = db.query(Country).filter(Country.iso3 == payload.iso3).first()
        if dup:
            raise HTTPException(status_code=409, detail="Duplicate country iso3")

    country = Country(
        iso2=payload.iso2,
        iso3=payload.iso3,
        name_vi=payload.name_vi,
        name_en=payload.name_en,
        status=ReferenceStatus.ACTIVE
    )
    db.add(country)
    db.commit()
    db.refresh(country)

    log_audit_event(
        db=db,
        event_name="CountryCreated",
        entity_type="Country",
        entity_id=country.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        command_name="CreateCountry"
    )
    db.commit()

    return country


@router.get("/countries", response_model=List[CountryResponse])
def list_countries(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:reference:read"))
):
    return db.query(Country).all()


# ==========================================
# PROVINCE ENDPOINTS
# ==========================================

@router.post("/provinces", response_model=ProvinceResponse, status_code=201)
def create_province(
    payload: ProvinceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:reference:create"))
):
    # Check if country exists
    c = db.query(Country).filter(Country.id == payload.country_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Reference country not found")

    prov = Province(
        country_id=payload.country_id,
        name=payload.name,
        code=payload.code,
        status=ReferenceStatus.ACTIVE
    )
    db.add(prov)
    db.commit()
    db.refresh(prov)

    log_audit_event(
        db=db,
        event_name="ProvinceCreated",
        entity_type="Province",
        entity_id=prov.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        command_name="CreateProvince"
    )
    db.commit()

    return prov


@router.get("/provinces", response_model=List[ProvinceResponse])
def list_provinces(
    country_id: Optional[uuid.UUID] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:reference:read"))
):
    query = db.query(Province)
    if country_id:
        query = query.filter(Province.country_id == country_id)
    if q:
        query = query.filter(Province.name.ilike(f"%{q}%"))
    return query.all()


# ==========================================
# BRAND ENDPOINTS
# ==========================================

@router.post("/brands", response_model=BrandResponse, status_code=201)
def create_brand(
    payload: BrandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:brand:create"))
):
    # Check duplicate brand name (case-insensitive)
    dup = db.query(Brand).filter(text("lower(name) = :name")).params(name=payload.name.lower()).first()
    if dup:
        raise HTTPException(status_code=409, detail="Duplicate record (brand name already exists)")

    # Check country
    if payload.country_id:
        c = db.query(Country).filter(Country.id == payload.country_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Reference country not found")

    # Check manufacturer
    if payload.manufacturer_id:
        m = db.query(Manufacturer).filter(Manufacturer.id == payload.manufacturer_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Reference manufacturer not found")

    brand = Brand(
        name=payload.name,
        country_id=payload.country_id,
        manufacturer_id=payload.manufacturer_id,
        status=BrandStatus.ACTIVE
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)

    log_audit_event(
        db=db,
        event_name="BrandCreated",
        entity_type="Brand",
        entity_id=brand.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        command_name="CreateBrand"
    )
    db.commit()

    return brand


@router.get("/brands", response_model=List[BrandResponse])
def list_brands(
    q: Optional[str] = None,
    country_id: Optional[uuid.UUID] = None,
    status: Optional[BrandStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:brand:read"))
):
    query = db.query(Brand)
    if q:
        query = query.filter(Brand.name.ilike(f"%{q}%"))
    if country_id:
        query = query.filter(Brand.country_id == country_id)
    if status:
        query = query.filter(Brand.status == status)
    return query.all()


# ==========================================
# MANUFACTURER ENDPOINTS
# ==========================================

@router.post("/manufacturers", response_model=ManufacturerResponse, status_code=201)
def create_manufacturer(
    payload: ManufacturerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:manufacturer:create"))
):
    # Check country
    if payload.country_id:
        c = db.query(Country).filter(Country.id == payload.country_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Reference country not found")

    mfg = Manufacturer(
        legal_name=payload.legal_name,
        country_id=payload.country_id,
        website=payload.website,
        status=ManufacturerStatus.ACTIVE
    )
    db.add(mfg)
    db.commit()
    db.refresh(mfg)

    log_audit_event(
        db=db,
        event_name="ManufacturerCreated",
        entity_type="Manufacturer",
        entity_id=mfg.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        command_name="CreateManufacturer"
    )
    db.commit()

    return mfg


@router.get("/manufacturers", response_model=List[ManufacturerResponse])
def list_manufacturers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:manufacturer:read"))
):
    return db.query(Manufacturer).all()


# ==========================================
# UNIT ENDPOINTS
# ==========================================

@router.post("/units", response_model=UnitResponse, status_code=201)
def create_unit(
    payload: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:unit:create"))
):
    # Check code uniqueness
    dup = db.query(Unit).filter(Unit.code == payload.code).first()
    if dup:
        raise HTTPException(status_code=409, detail="Duplicate unit code")

    unit = Unit(
        code=payload.code,
        display_name=payload.display_name,
        symbol=payload.symbol,
        unit_type=payload.unit_type,
        status=ReferenceStatus.ACTIVE
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    log_audit_event(
        db=db,
        event_name="UnitCreated",
        entity_type="Unit",
        entity_id=unit.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        command_name="CreateUnit"
    )
    db.commit()

    return unit


@router.get("/units", response_model=List[UnitResponse])
def list_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:unit:read"))
):
    return db.query(Unit).all()


# ==========================================
# CURRENCY ENDPOINTS
# ==========================================

@router.post("/currencies", response_model=CurrencyResponse, status_code=201)
def create_currency(
    payload: CurrencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:currency:create"))
):
    # Check code uniqueness
    dup = db.query(Currency).filter(Currency.code == payload.code).first()
    if dup:
        raise HTTPException(status_code=409, detail="Duplicate currency code")

    curr = Currency(
        code=payload.code,
        display_name=payload.display_name,
        symbol=payload.symbol,
        decimal_places=payload.decimal_places,
        status=ReferenceStatus.ACTIVE
    )
    db.add(curr)
    db.commit()
    db.refresh(curr)

    log_audit_event(
        db=db,
        event_name="CurrencyCreated",
        entity_type="Currency",
        entity_id=curr.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        command_name="CreateCurrency"
    )
    db.commit()

    return curr


@router.get("/currencies", response_model=List[CurrencyResponse])
def list_currencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:reference:read"))
):
    return db.query(Currency).all()


# ==========================================
# SIGNER ENDPOINTS
# ==========================================

@router.post("/signers", response_model=SignerProfileResponse, status_code=201)
def create_signer_profile(
    payload: SignerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:signer:create"))
):
    org_id = current_user.organization_id

    # If this profile is default, unset any other defaults in the same organization
    if payload.is_default:
        db.query(SignerProfile).filter(
            SignerProfile.organization_id == org_id,
            SignerProfile.is_default == True
        ).update({"is_default": False})

    signer = SignerProfile(
        organization_id=org_id,
        full_name=payload.full_name,
        title=payload.title,
        certificate_number=payload.certificate_number,
        is_default=payload.is_default,
        status=SignerStatus.ACTIVE
    )
    db.add(signer)
    db.commit()
    db.refresh(signer)

    log_audit_event(
        db=db,
        event_name="SignerProfileCreated",
        entity_type="SignerProfile",
        entity_id=signer.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CreateSignerProfile"
    )
    db.commit()

    return signer


@router.get("/signers", response_model=List[SignerProfileResponse])
def list_signer_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:reference:read"))
):
    org_id = current_user.organization_id
    return db.query(SignerProfile).filter(SignerProfile.organization_id == org_id).all()


@router.patch("/signers/{signer_profile_id}", response_model=SignerProfileResponse)
def update_signer_profile(
    signer_profile_id: uuid.UUID,
    payload: SignerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data:signer:update"))
):
    org_id = current_user.organization_id
    signer = db.query(SignerProfile).filter(
        SignerProfile.organization_id == org_id,
        SignerProfile.id == signer_profile_id
    ).first()

    if not signer:
        raise HTTPException(status_code=404, detail="Record not found")

    if payload.is_default is not None:
        if payload.is_default:
            db.query(SignerProfile).filter(
                SignerProfile.organization_id == org_id,
                SignerProfile.is_default == True
            ).update({"is_default": False})
        signer.is_default = payload.is_default

    if payload.title is not None:
        signer.title = payload.title

    db.commit()
    db.refresh(signer)

    log_audit_event(
        db=db,
        event_name="SignerProfileUpdated",
        entity_type="SignerProfile",
        entity_id=signer.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="UpdateSignerProfile"
    )
    db.commit()

    return signer
