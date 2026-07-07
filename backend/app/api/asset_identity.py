import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db import get_db
from app.core.rbac import require_permission, get_current_user
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, CanonicalAsset, AssetVariant, AssetAlias,
    AssetFamily, TaxonomyNode, CanonicalAssetStatus,
    AssetVariantStatus, AssetAliasStatus, AssetAliasScope,
    normalize_alias_helper
)
from app.modules.project_master_data.asset_identity_schemas import (
    CanonicalAssetCreate, CanonicalAssetUpdate, CanonicalAssetResponse,
    AssetVariantCreate, AssetVariantUpdate, AssetVariantResponse,
    AssetAliasCreate, AssetAliasUpdate, AssetAliasResponse
)

router = APIRouter(prefix="/api/v1/asset-identity", tags=["asset-identity"])

# ==========================================
# CANONICAL ASSET ENDPOINTS
# ==========================================

@router.post("/assets", response_model=CanonicalAssetResponse, status_code=201)
def create_canonical_asset(
    payload: CanonicalAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:asset:create"))
):
    # Validate family
    fam = db.query(AssetFamily).filter(AssetFamily.id == payload.asset_family_id).first()
    if not fam:
        raise HTTPException(status_code=422, detail="AssetFamily not found")

    # Validate taxonomy node
    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == payload.primary_taxonomy_node_id).first()
    if not node:
        raise HTTPException(status_code=422, detail="TaxonomyNode not found")

    asset = CanonicalAsset(
        asset_family_id=payload.asset_family_id,
        primary_taxonomy_node_id=payload.primary_taxonomy_node_id,
        standard_name=payload.standard_name,
        short_name=payload.short_name,
        brand_id=payload.brand_id,
        manufacturer_id=payload.manufacturer_id,
        country_id=payload.country_id,
        model_code=payload.model_code,
        maturity_level=payload.maturity_level,
        status=CanonicalAssetStatus.DRAFT
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="CANONICAL_ASSET_CREATE",
        entity_type="CanonicalAsset",
        entity_id=asset.id,
        payload={"standard_name": asset.standard_name}
    )
    return asset


@router.get("/assets", response_model=List[CanonicalAssetResponse])
def list_canonical_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:asset:read"))
):
    return db.query(CanonicalAsset).all()


@router.get("/assets/{asset_id}", response_model=CanonicalAssetResponse)
def get_canonical_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:asset:read"))
):
    asset = db.query(CanonicalAsset).filter(CanonicalAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="CanonicalAsset not found")
    return asset


@router.patch("/assets/{asset_id}", response_model=CanonicalAssetResponse)
def update_canonical_asset(
    asset_id: uuid.UUID,
    payload: CanonicalAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:asset:update"))
):
    asset = db.query(CanonicalAsset).filter(CanonicalAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="CanonicalAsset not found")

    if payload.standard_name is not None:
        asset.standard_name = payload.standard_name
    if payload.short_name is not None:
        asset.short_name = payload.short_name
    if payload.brand_id is not None:
        asset.brand_id = payload.brand_id
    if payload.manufacturer_id is not None:
        asset.manufacturer_id = payload.manufacturer_id
    if payload.country_id is not None:
        asset.country_id = payload.country_id
    if payload.model_code is not None:
        asset.model_code = payload.model_code
    if payload.maturity_level is not None:
        asset.maturity_level = payload.maturity_level
    if payload.status is not None:
        asset.status = payload.status

    db.commit()
    db.refresh(asset)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="CANONICAL_ASSET_UPDATE",
        entity_type="CanonicalAsset",
        entity_id=asset.id,
        payload={"standard_name": asset.standard_name}
    )
    return asset


# ==========================================
# ASSET VARIANT ENDPOINTS
# ==========================================

@router.post("/assets/{asset_id}/variants", response_model=AssetVariantResponse, status_code=201)
def create_asset_variant(
    asset_id: uuid.UUID,
    payload: AssetVariantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:variant:create"))
):
    asset = db.query(CanonicalAsset).filter(CanonicalAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="CanonicalAsset not found")

    # Uniqueness check: canonical_asset_id + code
    dup = db.query(AssetVariant).filter(
        AssetVariant.canonical_asset_id == asset_id,
        AssetVariant.code == payload.code
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="AssetVariant code already exists under this asset")

    variant = AssetVariant(
        canonical_asset_id=asset_id,
        asset_family_id=payload.asset_family_id,
        code=payload.code,
        display_name=payload.display_name,
        status=AssetVariantStatus.DRAFT
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_VARIANT_CREATE",
        entity_type="AssetVariant",
        entity_id=variant.id,
        payload={"code": variant.code}
    )
    return variant


@router.get("/assets/{asset_id}/variants", response_model=List[AssetVariantResponse])
def list_asset_variants_under_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:variant:read"))
):
    return db.query(AssetVariant).filter(AssetVariant.canonical_asset_id == asset_id).all()


@router.get("/variants/{variant_id}", response_model=AssetVariantResponse)
def get_asset_variant(
    variant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:variant:read"))
):
    variant = db.query(AssetVariant).filter(AssetVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="AssetVariant not found")
    return variant


@router.patch("/variants/{variant_id}", response_model=AssetVariantResponse)
def update_asset_variant(
    variant_id: uuid.UUID,
    payload: AssetVariantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:variant:update"))
):
    variant = db.query(AssetVariant).filter(AssetVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="AssetVariant not found")

    if payload.display_name is not None:
        variant.display_name = payload.display_name
    if payload.status is not None:
        variant.status = payload.status

    db.commit()
    db.refresh(variant)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_VARIANT_UPDATE",
        entity_type="AssetVariant",
        entity_id=variant.id,
        payload={"code": variant.code}
    )
    return variant


# ==========================================
# ASSET ALIAS ENDPOINTS
# ==========================================

@router.post("/assets/{asset_id}/aliases", response_model=AssetAliasResponse, status_code=201)
def create_canonical_alias(
    asset_id: uuid.UUID,
    payload: AssetAliasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:alias:create"))
):
    asset = db.query(CanonicalAsset).filter(CanonicalAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="CanonicalAsset not found")

    # Scope validation
    if payload.alias_scope == AssetAliasScope.VARIANT:
        if not payload.asset_variant_id:
            raise HTTPException(
                status_code=422,
                detail="Variant alias requires asset_variant_id (VAL_ID_011)"
            )
        # Verify variant belongs to canonical asset
        variant = db.query(AssetVariant).filter(
            AssetVariant.id == payload.asset_variant_id,
            AssetVariant.canonical_asset_id == asset_id
        ).first()
        if not variant:
            raise HTTPException(
                status_code=422,
                detail="Variant does not belong to this canonical asset"
            )
    else:
        if payload.asset_variant_id is not None:
            raise HTTPException(
                status_code=422,
                detail="Canonical alias must not have asset_variant_id"
            )

    normalized = normalize_alias_helper(payload.raw_alias)

    # Check uniqueness
    if payload.alias_scope == AssetAliasScope.VARIANT:
        dup = db.query(AssetAlias).filter(
            AssetAlias.asset_variant_id == payload.asset_variant_id,
            AssetAlias.normalized_alias == normalized
        ).first()
    else:
        dup = db.query(AssetAlias).filter(
            AssetAlias.canonical_asset_id == asset_id,
            AssetAlias.normalized_alias == normalized
        ).first()

    if dup:
        raise HTTPException(status_code=409, detail="Duplicate alias found")

    alias = AssetAlias(
        canonical_asset_id=asset_id,
        asset_variant_id=payload.asset_variant_id,
        alias_scope=payload.alias_scope,
        raw_alias=payload.raw_alias,
        normalized_alias=normalized,
        status=AssetAliasStatus.ACTIVE
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_ALIAS_CREATE",
        entity_type="AssetAlias",
        entity_id=alias.id,
        payload={"raw_alias": alias.raw_alias}
    )
    return alias


@router.post("/variants/{variant_id}/aliases", response_model=AssetAliasResponse, status_code=201)
def create_variant_alias(
    variant_id: uuid.UUID,
    payload: AssetAliasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:alias:create"))
):
    variant = db.query(AssetVariant).filter(AssetVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="AssetVariant not found")

    normalized = normalize_alias_helper(payload.raw_alias)

    # Check uniqueness
    dup = db.query(AssetAlias).filter(
        AssetAlias.asset_variant_id == variant_id,
        AssetAlias.normalized_alias == normalized
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="Duplicate alias found")

    alias = AssetAlias(
        canonical_asset_id=variant.canonical_asset_id,
        asset_variant_id=variant_id,
        alias_scope=AssetAliasScope.VARIANT,
        raw_alias=payload.raw_alias,
        normalized_alias=normalized,
        status=AssetAliasStatus.ACTIVE
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_ALIAS_CREATE",
        entity_type="AssetAlias",
        entity_id=alias.id,
        payload={"raw_alias": alias.raw_alias}
    )
    return alias


@router.get("/aliases", response_model=List[AssetAliasResponse])
def list_aliases(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:alias:read"))
):
    return db.query(AssetAlias).all()


@router.get("/aliases/{alias_id}", response_model=AssetAliasResponse)
def get_alias(
    alias_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:alias:read"))
):
    alias = db.query(AssetAlias).filter(AssetAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="AssetAlias not found")
    return alias


@router.patch("/aliases/{alias_id}", response_model=AssetAliasResponse)
def update_alias(
    alias_id: uuid.UUID,
    payload: AssetAliasUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset_identity:alias:update"))
):
    alias = db.query(AssetAlias).filter(AssetAlias.id == alias_id).first()
    if not alias:
        raise HTTPException(status_code=404, detail="AssetAlias not found")

    if payload.status is not None:
        alias.status = payload.status

    db.commit()
    db.refresh(alias)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_ALIAS_UPDATE",
        entity_type="AssetAlias",
        entity_id=alias.id,
        payload={"raw_alias": alias.raw_alias}
    )
    return alias
