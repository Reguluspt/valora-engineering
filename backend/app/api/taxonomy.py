import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, TaxonomyNode, TaxonomyNodeLevel, TaxonomyStatus,
    AssetFamily, AssetFamilyStatus, AssetDNA, AssetDNAStatus,
    AssetAttributeDefinition, AssetAttributeScope, AssetAttributeDataType
)
from app.modules.project_master_data.taxonomy_schemas import (
    TaxonomyNodeCreate, TaxonomyNodeUpdate, TaxonomyNodeResponse,
    AssetFamilyCreate, AssetFamilyUpdate, AssetFamilyResponse,
    AssetDNACreate, AssetDNAUpdate, AssetDNAResponse,
    AssetAttributeDefinitionCreate, AssetAttributeDefinitionUpdate, AssetAttributeDefinitionResponse
)

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])

# Helper to validate node hierarchy
def validate_node_hierarchy(db: Session, parent_id: Optional[uuid.UUID], level: TaxonomyNodeLevel):
    if level == TaxonomyNodeLevel.DOMAIN:
        if parent_id is not None:
            raise HTTPException(
                status_code=422,
                detail="Root domain node cannot have a parent"
            )
    else:
        if parent_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"Non-root node of level {level} requires a parent"
            )
        parent = db.query(TaxonomyNode).filter(TaxonomyNode.id == parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=422,
                detail="Parent node not found"
            )
        
        # Verify parent status is active
        if parent.status in [TaxonomyStatus.DEPRECATED, TaxonomyStatus.REJECTED]:
            raise HTTPException(
                status_code=422,
                detail="Cannot create node under deprecated or rejected parent"
            )

        # Level ordering validation
        expected_parent_level = {
            TaxonomyNodeLevel.CATEGORY: TaxonomyNodeLevel.DOMAIN,
            TaxonomyNodeLevel.SUBCATEGORY: TaxonomyNodeLevel.CATEGORY,
            TaxonomyNodeLevel.GROUP: TaxonomyNodeLevel.SUBCATEGORY
        }
        if parent.level != expected_parent_level.get(level):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid parent level {parent.level} for node level {level}"
            )


# ==========================================
# TAXONOMY NODE ENDPOINTS
# ==========================================

@router.post("/nodes", response_model=TaxonomyNodeResponse, status_code=201)
def create_node(
    payload: TaxonomyNodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:create"))
):
    # Check duplicate code
    dup = db.query(TaxonomyNode).filter(TaxonomyNode.code == payload.code).first()
    if dup:
        raise HTTPException(status_code=409, detail="TaxonomyNode code already exists")

    validate_node_hierarchy(db, payload.parent_id, payload.level)

    node = TaxonomyNode(
        parent_id=payload.parent_id,
        level=payload.level,
        code=payload.code,
        name_vi=payload.name_vi,
        name_en=payload.name_en,
        status=TaxonomyStatus.DRAFT,
        created_by=current_user.id
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="TAXONOMY_NODE_CREATE",
        entity_type="TaxonomyNode",
        entity_id=node.id,
        payload={"code": node.code, "level": node.level}
    )
    return node


@router.get("/nodes", response_model=List[TaxonomyNodeResponse])
def list_nodes(db: Session = Depends(get_db)):
    return db.query(TaxonomyNode).all()


@router.get("/nodes/{node_id}", response_model=TaxonomyNodeResponse)
def get_node(node_id: uuid.UUID, db: Session = Depends(get_db)):
    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="TaxonomyNode not found")
    return node


@router.put("/nodes/{node_id}", response_model=TaxonomyNodeResponse)
def update_node(
    node_id: uuid.UUID,
    payload: TaxonomyNodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:update"))
):
    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="TaxonomyNode not found")

    if payload.name_vi is not None:
        node.name_vi = payload.name_vi
    if payload.name_en is not None:
        node.name_en = payload.name_en

    db.commit()
    db.refresh(node)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="TAXONOMY_NODE_UPDATE",
        entity_type="TaxonomyNode",
        entity_id=node.id,
        payload={"code": node.code}
    )
    return node


@router.post("/nodes/{node_id}/submit-review", response_model=TaxonomyNodeResponse)
def submit_review(
    node_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:update"))
):
    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="TaxonomyNode not found")

    if node.status != TaxonomyStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT nodes can be submitted for review")

    node.status = TaxonomyStatus.PENDING_REVIEW
    db.commit()
    db.refresh(node)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="TAXONOMY_NODE_SUBMIT_REVIEW",
        entity_type="TaxonomyNode",
        entity_id=node.id,
        payload={"code": node.code}
    )
    return node


@router.post("/nodes/{node_id}/approve", response_model=TaxonomyNodeResponse)
def approve_node(
    node_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:approve"))
):
    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="TaxonomyNode not found")

    node.status = TaxonomyStatus.ACTIVE
    node.approved_by = current_user.id
    node.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(node)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="TAXONOMY_NODE_APPROVE",
        entity_type="TaxonomyNode",
        entity_id=node.id,
        payload={"code": node.code}
    )
    return node


@router.post("/nodes/{node_id}/deprecate", response_model=TaxonomyNodeResponse)
def deprecate_node(
    node_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:deprecate"))
):
    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="TaxonomyNode not found")

    node.status = TaxonomyStatus.DEPRECATED
    db.commit()
    db.refresh(node)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="TAXONOMY_NODE_DEPRECATE",
        entity_type="TaxonomyNode",
        entity_id=node.id,
        payload={"code": node.code}
    )
    return node


# ==========================================
# ASSET FAMILY ENDPOINTS
# ==========================================

@router.post("/families", response_model=AssetFamilyResponse, status_code=201)
def create_family(
    payload: AssetFamilyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:create"))
):
    dup = db.query(AssetFamily).filter(AssetFamily.code == payload.code).first()
    if dup:
        raise HTTPException(status_code=409, detail="AssetFamily code already exists")

    node = db.query(TaxonomyNode).filter(TaxonomyNode.id == payload.taxonomy_node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Parent TaxonomyNode not found")

    if node.status != TaxonomyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="AssetFamily can only be created under active TaxonomyNode")

    family = AssetFamily(
        taxonomy_node_id=payload.taxonomy_node_id,
        code=payload.code,
        name_vi=payload.name_vi,
        default_unit_id=payload.default_unit_id,
        status=AssetFamilyStatus.DRAFT
    )
    db.add(family)
    db.commit()
    db.refresh(family)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_FAMILY_CREATE",
        entity_type="AssetFamily",
        entity_id=family.id,
        payload={"code": family.code}
    )
    return family


@router.get("/families", response_model=List[AssetFamilyResponse])
def list_families(db: Session = Depends(get_db)):
    return db.query(AssetFamily).all()


@router.get("/families/{family_id}", response_model=AssetFamilyResponse)
def get_family(family_id: uuid.UUID, db: Session = Depends(get_db)):
    fam = db.query(AssetFamily).filter(AssetFamily.id == family_id).first()
    if not fam:
        raise HTTPException(status_code=404, detail="AssetFamily not found")
    return fam


@router.put("/families/{family_id}", response_model=AssetFamilyResponse)
def update_family(
    family_id: uuid.UUID,
    payload: AssetFamilyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:update"))
):
    fam = db.query(AssetFamily).filter(AssetFamily.id == family_id).first()
    if not fam:
        raise HTTPException(status_code=404, detail="AssetFamily not found")

    if payload.name_vi is not None:
        fam.name_vi = payload.name_vi
    if payload.default_unit_id is not None:
        fam.default_unit_id = payload.default_unit_id

    db.commit()
    db.refresh(fam)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_FAMILY_UPDATE",
        entity_type="AssetFamily",
        entity_id=fam.id,
        payload={"code": fam.code}
    )
    return fam


# ==========================================
# ASSET DNA ENDPOINTS
# ==========================================

@router.post("/dna", response_model=AssetDNAResponse, status_code=201)
def create_dna(
    payload: AssetDNACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:create"))
):
    fam = db.query(AssetFamily).filter(AssetFamily.id == payload.asset_family_id).first()
    if not fam:
        raise HTTPException(status_code=404, detail="AssetFamily not found")

    dna = AssetDNA(
        asset_family_id=payload.asset_family_id,
        version=payload.version,
        name=payload.name,
        status=AssetDNAStatus.DRAFT
    )
    db.add(dna)
    db.commit()
    db.refresh(dna)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_DNA_CREATE",
        entity_type="AssetDNA",
        entity_id=dna.id,
        payload={"family_id": str(dna.asset_family_id), "version": dna.version}
    )
    return dna


@router.get("/dna", response_model=List[AssetDNAResponse])
def list_dna(db: Session = Depends(get_db)):
    return db.query(AssetDNA).all()


@router.get("/dna/{dna_id}", response_model=AssetDNAResponse)
def get_dna(dna_id: uuid.UUID, db: Session = Depends(get_db)):
    dna = db.query(AssetDNA).filter(AssetDNA.id == dna_id).first()
    if not dna:
        raise HTTPException(status_code=404, detail="AssetDNA not found")
    return dna


@router.put("/dna/{dna_id}", response_model=AssetDNAResponse)
def update_dna(
    dna_id: uuid.UUID,
    payload: AssetDNAUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:update"))
):
    dna = db.query(AssetDNA).filter(AssetDNA.id == dna_id).first()
    if not dna:
        raise HTTPException(status_code=404, detail="AssetDNA not found")

    if payload.name is not None:
        dna.name = payload.name

    db.commit()
    db.refresh(dna)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_DNA_UPDATE",
        entity_type="AssetDNA",
        entity_id=dna.id,
        payload={"version": dna.version}
    )
    return dna


@router.post("/dna/{dna_id}/activate", response_model=AssetDNAResponse)
def activate_dna(
    dna_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:approve"))
):
    dna = db.query(AssetDNA).filter(AssetDNA.id == dna_id).first()
    if not dna:
        raise HTTPException(status_code=404, detail="AssetDNA not found")

    # Enforce only one active DNA version per family
    active_dnas = db.query(AssetDNA).filter(
        AssetDNA.asset_family_id == dna.asset_family_id,
        AssetDNA.status == AssetDNAStatus.ACTIVE,
        AssetDNA.id != dna.id
    ).all()
    for active_dna in active_dnas:
        active_dna.status = AssetDNAStatus.DEPRECATED
    db.flush()

    dna.status = AssetDNAStatus.ACTIVE
    dna.approved_by = current_user.id
    dna.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dna)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_DNA_ACTIVATE",
        entity_type="AssetDNA",
        entity_id=dna.id,
        payload={"version": dna.version}
    )
    return dna


# ==========================================
# ATTRIBUTE DEFINITION ENDPOINTS
# ==========================================

@router.post("/attribute-definitions", response_model=AssetAttributeDefinitionResponse, status_code=201)
def create_attribute_definition(
    payload: AssetAttributeDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:create"))
):
    # key must be unique per DNA
    dup = db.query(AssetAttributeDefinition).filter(
        AssetAttributeDefinition.asset_dna_id == payload.asset_dna_id,
        AssetAttributeDefinition.key == payload.key
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="Attribute key already exists in this DNA")

    # Validation: If is_variant_defining = True, then scope must be variant or both
    if payload.is_variant_defining and payload.scope == AssetAttributeScope.CANONICAL:
        raise HTTPException(
            status_code=422,
            detail="Variant-defining attributes cannot have canonical scope (VAL_TAX_DNA_002)"
        )

    # Validation: if data_type is enum, enum_values must be provided
    if payload.data_type == AssetAttributeDataType.ENUM and not payload.enum_values:
        raise HTTPException(
            status_code=422,
            detail="Enum attribute type requires enum_values"
        )

    attr = AssetAttributeDefinition(
        asset_dna_id=payload.asset_dna_id,
        key=payload.key,
        label_vi=payload.label_vi,
        data_type=payload.data_type,
        unit_id=payload.unit_id,
        scope=payload.scope,
        is_required=payload.is_required,
        is_variant_defining=payload.is_variant_defining,
        is_searchable=payload.is_searchable,
        enum_values=payload.enum_values,
        validation_rule=payload.validation_rule
    )
    db.add(attr)
    db.commit()
    db.refresh(attr)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_ATTRIBUTE_DEFINITION_CREATE",
        entity_type="AssetAttributeDefinition",
        entity_id=attr.id,
        payload={"key": attr.key}
    )
    return attr


@router.get("/attribute-definitions", response_model=List[AssetAttributeDefinitionResponse])
def list_attribute_definitions(db: Session = Depends(get_db)):
    return db.query(AssetAttributeDefinition).all()


@router.get("/attribute-definitions/{attribute_id}", response_model=AssetAttributeDefinitionResponse)
def get_attribute_definition(attribute_id: uuid.UUID, db: Session = Depends(get_db)):
    attr = db.query(AssetAttributeDefinition).filter(AssetAttributeDefinition.id == attribute_id).first()
    if not attr:
        raise HTTPException(status_code=404, detail="AssetAttributeDefinition not found")
    return attr


@router.put("/attribute-definitions/{attribute_id}", response_model=AssetAttributeDefinitionResponse)
def update_attribute_definition(
    attribute_id: uuid.UUID,
    payload: AssetAttributeDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("taxonomy:node:update"))
):
    attr = db.query(AssetAttributeDefinition).filter(AssetAttributeDefinition.id == attribute_id).first()
    if not attr:
        raise HTTPException(status_code=404, detail="AssetAttributeDefinition not found")

    if payload.label_vi is not None:
        attr.label_vi = payload.label_vi
    if payload.unit_id is not None:
        attr.unit_id = payload.unit_id
    if payload.scope is not None:
        attr.scope = payload.scope
    if payload.is_required is not None:
        attr.is_required = payload.is_required
    if payload.is_variant_defining is not None:
        attr.is_variant_defining = payload.is_variant_defining
    if payload.is_searchable is not None:
        attr.is_searchable = payload.is_searchable
    if payload.enum_values is not None:
        attr.enum_values = payload.enum_values
    if payload.validation_rule is not None:
        attr.validation_rule = payload.validation_rule

    # Validation: If is_variant_defining = True, then scope must be variant or both
    if attr.is_variant_defining and attr.scope == AssetAttributeScope.CANONICAL:
        raise HTTPException(
            status_code=422,
            detail="Variant-defining attributes cannot have canonical scope (VAL_TAX_DNA_002)"
        )

    db.commit()
    db.refresh(attr)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="ASSET_ATTRIBUTE_DEFINITION_UPDATE",
        entity_type="AssetAttributeDefinition",
        entity_id=attr.id,
        payload={"key": attr.key}
    )
    return attr
