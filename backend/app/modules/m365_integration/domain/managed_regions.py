"""Deterministic, digest-only Managed Region fingerprints for bounded DOCX files."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import posixpath
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


PARSER_CONTRACT_VERSION = "valora-docx-managed-regions-v1"
FINGERPRINT_CONTRACT_VERSION = "valora-managed-region-fingerprint-v1"
MAX_DOCX_BYTES = 25 * 1024 * 1024
MAX_ENTRY_BYTES = 20 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 80 * 1024 * 1024
MAX_ENTRY_COUNT = 1_000
MAX_COMPRESSION_RATIO = 100
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_UNSAFE_XML_DECLARATION_RE = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
_VOLATILE_ATTRIBUTE_NAMES = {"paraId", "textId"}
_IGNORED_CANONICAL_PARTS = {
    "docProps/core.xml",
    "docProps/app.xml",
    "docProps/custom.xml",
}


class ManagedRegionIntegrityError(ValueError):
    """The DOCX cannot be compared under the sealed fingerprint contract."""


@dataclass(frozen=True)
class ManagedRegionDefinition:
    region_key: str
    locator: str
    semantic_type: str
    normalization_contract: str

    def __post_init__(self) -> None:
        if not self.region_key.strip() or len(self.region_key) > 128:
            raise ValueError("Managed Region key is invalid.")
        if not self.locator.strip() or len(self.locator) > 255:
            raise ValueError("Managed Region locator is invalid.")
        if self.semantic_type != "text":
            raise ValueError("Managed Region semantic type is unsupported.")
        if self.normalization_contract != "text-whitespace-v1":
            raise ValueError("Managed Region normalization contract is unsupported.")


@dataclass(frozen=True)
class ManagedRegionDefinitionSet:
    authority_ref: str
    definitions: tuple[ManagedRegionDefinition, ...]

    def __post_init__(self) -> None:
        if not self.authority_ref.strip() or len(self.authority_ref) > 255:
            raise ValueError("Managed Region authority reference is invalid.")
        if not self.definitions:
            raise ValueError("At least one Managed Region definition is required.")
        keys = [definition.region_key for definition in self.definitions]
        locators = [definition.locator for definition in self.definitions]
        if len(set(keys)) != len(keys) or len(set(locators)) != len(locators):
            raise ValueError("Managed Region keys and locators must be unique.")

    @property
    def manifest_digest_sha256(self) -> str:
        payload = {
            "authority_ref": self.authority_ref,
            "definitions": [
                {
                    "locator": definition.locator,
                    "normalization_contract": definition.normalization_contract,
                    "region_key": definition.region_key,
                    "semantic_type": definition.semantic_type,
                }
                for definition in self.definitions
            ],
            "fingerprint_contract": FINGERPRINT_CONTRACT_VERSION,
        }
        return _digest_json(payload)


@dataclass(frozen=True)
class ManagedRegionFingerprint:
    region_key: str
    locator: str
    semantic_type: str
    normalization_contract: str
    normalized_value_digest_sha256: str
    structural_digest_sha256: str


@dataclass(frozen=True)
class DocxFingerprint:
    source_content_sha256: str
    source_size_bytes: int
    parser_contract_version: str
    fingerprint_contract_version: str
    managed_region_manifest_digest_sha256: str
    whole_canonical_digest_sha256: str
    outside_managed_digest_sha256: str
    regions: tuple[ManagedRegionFingerprint, ...]


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _digest_bytes(encoded)


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _safe_entry_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or normalized != posixpath.normpath(normalized)
        or normalized == ".."
        or normalized.startswith("../")
    ):
        raise ManagedRegionIntegrityError("DOCX contains an unsafe package path.")
    return normalized


def _read_entries(content: bytes) -> dict[str, bytes]:
    if not content or len(content) > MAX_DOCX_BYTES:
        raise ManagedRegionIntegrityError("DOCX size is outside the accepted boundary.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ManagedRegionIntegrityError("DOCX package is invalid.") from exc

    entries: dict[str, bytes] = {}
    total_size = 0
    infos = archive.infolist()
    if len(infos) > MAX_ENTRY_COUNT:
        raise ManagedRegionIntegrityError("DOCX contains too many package entries.")
    try:
        for info in infos:
            name = _safe_entry_name(info.filename)
            if name.endswith("/"):
                continue
            if name in entries:
                raise ManagedRegionIntegrityError("DOCX contains duplicate package entries.")
            if info.flag_bits & 0x1:
                raise ManagedRegionIntegrityError("Encrypted DOCX entries are unsupported.")
            if info.file_size > MAX_ENTRY_BYTES:
                raise ManagedRegionIntegrityError("DOCX entry exceeds the accepted size.")
            total_size += info.file_size
            if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ManagedRegionIntegrityError("DOCX expands beyond the accepted size.")
            compressed = max(info.compress_size, 1)
            if info.file_size > 1_024 and info.file_size / compressed > MAX_COMPRESSION_RATIO:
                raise ManagedRegionIntegrityError("DOCX compression ratio is unsafe.")
            entries[name] = archive.read(info)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ManagedRegionIntegrityError("DOCX package cannot be read safely.") from exc
    finally:
        archive.close()

    if "[Content_Types].xml" not in entries or "word/document.xml" not in entries:
        raise ManagedRegionIntegrityError("DOCX package is incomplete.")
    return entries


def _parse_xml(value: bytes) -> ET.Element:
    # OOXML parts are UTF-8 in this parser contract. NUL bytes are rejected
    # before decoding because ElementTree otherwise auto-detects UTF-16 and
    # can expand a DTD that the UTF-8 declaration guard never sees.
    if b"\x00" in value:
        raise ManagedRegionIntegrityError("DOCX XML encoding is unsupported.")
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManagedRegionIntegrityError("DOCX XML encoding is unsupported.") from exc
    if _UNSAFE_XML_DECLARATION_RE.search(decoded):
        raise ManagedRegionIntegrityError("DOCX XML declarations are unsafe.")
    try:
        return ET.fromstring(value)
    except ET.ParseError as exc:
        raise ManagedRegionIntegrityError("DOCX XML is invalid.") from exc


def _validate_relationships(entries: dict[str, bytes]) -> None:
    for name, value in entries.items():
        if not name.endswith(".rels"):
            continue
        root = _parse_xml(value)
        for relationship in root.iter(f"{{{_REL_NS}}}Relationship"):
            if relationship.attrib.get("TargetMode") != "External":
                continue
            target = relationship.attrib.get("Target", "")
            scheme = urlparse(target).scheme.lower()
            if scheme not in {"http", "https", "mailto"}:
                raise ManagedRegionIntegrityError("DOCX contains an unsafe external relationship.")


def _strip_volatile_attributes(root: ET.Element) -> None:
    for element in root.iter():
        for attribute in list(element.attrib):
            local = _local_name(attribute)
            if local.startswith("rsid") or local in _VOLATILE_ATTRIBUTE_NAMES:
                del element.attrib[attribute]


def _region_locator(element: ET.Element) -> str | None:
    properties = element.find(f"{{{_W_NS}}}sdtPr")
    if properties is None:
        return None
    tag = properties.find(f"{{{_W_NS}}}tag")
    if tag is None:
        return None
    return tag.attrib.get(f"{{{_W_NS}}}val")


def _region_content(element: ET.Element) -> ET.Element:
    content = element.find(f"{{{_W_NS}}}sdtContent")
    if content is None:
        raise ManagedRegionIntegrityError("Managed Region content is missing.")
    return content


def _extract_text(content: ET.Element) -> str:
    chunks: list[str] = []
    for element in content.iter():
        local = _local_name(element.tag)
        if local == "t" and element.text:
            chunks.append(element.text)
        elif local == "tab":
            chunks.append("\t")
        elif local in {"br", "cr"}:
            chunks.append("\n")
    return "".join(chunks)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(normalized.split())


def _structural_digest(content: ET.Element) -> str:
    clone = copy.deepcopy(content)
    _strip_volatile_attributes(clone)
    for element in clone.iter():
        if _local_name(element.tag) == "t":
            element.text = "#TEXT#"
    return _digest_bytes(ET.tostring(clone, encoding="utf-8"))


def _canonical_entry(name: str, value: bytes) -> bytes:
    if name.endswith((".xml", ".rels")):
        root = _parse_xml(value)
        _strip_volatile_attributes(root)
        return ET.tostring(root, encoding="utf-8")
    return value


def _package_digest(entries: dict[str, bytes]) -> str:
    payload = [
        (name, _digest_bytes(_canonical_entry(name, entries[name])))
        for name in sorted(entries)
        if name not in _IGNORED_CANONICAL_PARTS
    ]
    return _digest_json(payload)


def fingerprint_docx(
    content: bytes,
    definition_set: ManagedRegionDefinitionSet,
) -> DocxFingerprint:
    """Return deterministic digests without retaining extracted business values."""
    entries = _read_entries(content)
    _validate_relationships(entries)
    locator_map = {definition.locator: definition for definition in definition_set.definitions}
    found: dict[str, ManagedRegionFingerprint] = {}
    masked_entries = dict(entries)

    for name in sorted(entries):
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        root = _parse_xml(entries[name])
        masked_root = copy.deepcopy(root)
        changed = False
        for element in masked_root.iter(f"{{{_W_NS}}}sdt"):
            locator = _region_locator(element)
            definition = locator_map.get(locator or "")
            if definition is None:
                continue
            if definition.region_key in found:
                raise ManagedRegionIntegrityError("Managed Region locator is duplicated.")
            region_content = _region_content(element)
            normalized = _normalize_text(_extract_text(region_content))
            found[definition.region_key] = ManagedRegionFingerprint(
                region_key=definition.region_key,
                locator=definition.locator,
                semantic_type=definition.semantic_type,
                normalization_contract=definition.normalization_contract,
                normalized_value_digest_sha256=_digest_bytes(normalized.encode("utf-8")),
                structural_digest_sha256=_structural_digest(region_content),
            )
            for child in list(region_content):
                region_content.remove(child)
            marker = ET.Element("{urn:valora:managed-region:v1}region")
            marker.attrib["key"] = definition.region_key
            region_content.append(marker)
            changed = True
        if changed:
            _strip_volatile_attributes(masked_root)
            masked_entries[name] = ET.tostring(masked_root, encoding="utf-8")

    missing = [
        definition.region_key
        for definition in definition_set.definitions
        if definition.region_key not in found
    ]
    if missing:
        raise ManagedRegionIntegrityError("One or more Managed Regions are missing.")

    ordered_regions = tuple(
        found[definition.region_key] for definition in definition_set.definitions
    )
    return DocxFingerprint(
        source_content_sha256=_digest_bytes(content),
        source_size_bytes=len(content),
        parser_contract_version=PARSER_CONTRACT_VERSION,
        fingerprint_contract_version=FINGERPRINT_CONTRACT_VERSION,
        managed_region_manifest_digest_sha256=definition_set.manifest_digest_sha256,
        whole_canonical_digest_sha256=_package_digest(entries),
        outside_managed_digest_sha256=_package_digest(masked_entries),
        regions=ordered_regions,
    )
