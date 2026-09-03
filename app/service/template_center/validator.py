"""Pure, bounded DOCX upload validation for template-center slice T004."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
import posixpath
import re
import stat
import unicodedata
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from lxml import etree

from app.service.template_center.contracts import (
    DOCX_MIME_TYPE,
    MAX_TEMPLATE_BYTES,
    TemplateCenterError,
    TemplateContractManifest,
    TemplateErrorCode,
    TemplateTokenOccurrence,
    TemplateValidationReceipt,
)


VALIDATOR_VERSION = "template-upload-validator.v1"
MAX_ZIP_MEMBERS = 256
MAX_PART_BYTES = 16 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100

_CONTENT_TYPES = "[Content_Types].xml"
_ROOT_RELS = "_rels/.rels"
_MAIN_PART = "word/document.xml"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT_TYPE_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MAIN_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
_OFFICE_DOCUMENT_REL = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
)
_OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_HEADER_REL = f"{_OFFICE_REL_NS}/header"
_FOOTER_REL = f"{_OFFICE_REL_NS}/footer"
_HEADER_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
)
_FOOTER_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
)
_TOKEN = re.compile(r"\{\{(.*?)\}\}")
_TOKEN_ID = re.compile(r"kg\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_.]*")
_TABLE_ANCHOR = re.compile(
    r"table:(?P<part>[^:]+):(?P<rows>[1-9][0-9]*)x(?P<columns>[1-9][0-9]*)"
)
_DRIVE_PATH = re.compile(r"^[A-Za-z]:")
_ACTIVE_PARTS = (
    "vbaproject",
    "activex/",
    "embeddings/",
    "customui/",
)
_ACTIVE_RELATIONSHIP_SUFFIXES = (
    "/attachedtemplate",
    "/control",
    "/externallinkpath",
    "/oleobject",
    "/package",
    "/vbaproject",
)
_ACTIVE_XML_TAGS = {
    f"{{{_WORD_NS}}}altChunk",
    f"{{{_WORD_NS}}}fldChar",
    f"{{{_WORD_NS}}}fldSimple",
    f"{{{_WORD_NS}}}instrText",
    f"{{{_WORD_NS}}}txbxContent",
    "{http://www.w3.org/2001/XInclude}include",
}


class _Rejected(Exception):
    pass


def _reject() -> None:
    raise _Rejected


def _validate_public_inputs(
    content: object,
    filename: object,
    content_type: object,
    contract: object,
) -> None:
    if (
        type(content) is not bytes
        or not content
        or len(content) > MAX_TEMPLATE_BYTES
        or type(filename) is not str
        or type(content_type) is not str
        or type(contract) is not TemplateContractManifest
    ):
        raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)
    try:
        filename.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID) from error
    if (
        filename != unicodedata.normalize("NFC", filename)
        or filename in {"", ".", ".."}
        or "/" in filename
        or "\\" in filename
        or ":" in filename
        or _DRIVE_PATH.match(filename) is not None
        or filename.startswith(".~lock.")
        or filename.endswith("#")
        or any(
            unicodedata.category(character).startswith("C") for character in filename
        )
        or not filename.casefold().endswith(".docx")
        or content_type != DOCX_MIME_TYPE
    ):
        raise TemplateCenterError(TemplateErrorCode.INPUT_INVALID)


def _safe_member_name(info: ZipInfo, normalized_names: set[str]) -> str:
    name = info.filename
    normalized = unicodedata.normalize("NFC", name)
    if (
        type(name) is not str
        or not name
        or name != normalized
        or name.startswith("/")
        or "\\" in name
        or ":" in name
        or _DRIVE_PATH.match(name) is not None
        or any(unicodedata.category(character).startswith("C") for character in name)
        or info.is_dir()
        or name.endswith("/")
    ):
        _reject()
    components = name.split("/")
    if any(component in {"", ".", ".."} for component in components):
        _reject()
    canonical = posixpath.normpath(name)
    if canonical != name or canonical in normalized_names:
        _reject()
    normalized_names.add(canonical)
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if file_type not in {0, stat.S_IFREG} or stat.S_ISLNK(mode):
        _reject()
    if info.flag_bits & 0x1 or info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
        _reject()
    if info.file_size > MAX_PART_BYTES:
        _reject()
    if (
        info.file_size
        and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO
    ):
        _reject()
    lowered = name.casefold()
    if any(marker in lowered for marker in _ACTIVE_PARTS):
        _reject()
    if lowered.endswith((".exe", ".dll", ".com", ".js", ".vbs", ".bin")):
        _reject()
    return canonical


def _read_members(content: bytes) -> tuple[dict[str, bytes], list[dict[str, object]]]:
    if not content.startswith(b"PK\x03\x04"):
        _reject()
    retained: dict[str, bytes] = {}
    summaries: list[dict[str, object]] = []
    normalized_names: set[str] = set()
    total = 0
    with ZipFile(BytesIO(content), "r") as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_ZIP_MEMBERS:
            _reject()
        for info in infos:
            name = _safe_member_name(info, normalized_names)
            total += info.file_size
            if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
                _reject()
            digest = sha256()
            chunks: list[bytes] = []
            actual_size = 0
            with archive.open(info, "r") as source:
                while True:
                    chunk = source.read(64 * 1024)
                    if not chunk:
                        break
                    actual_size += len(chunk)
                    if actual_size > info.file_size or actual_size > MAX_PART_BYTES:
                        _reject()
                    digest.update(chunk)
                    chunks.append(chunk)
            if actual_size != info.file_size:
                _reject()
            summaries.append(
                {"name": name, "size": actual_size, "sha256": digest.hexdigest()}
            )
            retained[name] = b"".join(chunks)
    if {_CONTENT_TYPES, _ROOT_RELS, _MAIN_PART} - normalized_names:
        _reject()
    return retained, summaries


def _parse_xml(value: bytes) -> etree._Element:
    upper = value.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        _reject()
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        recover=False,
        huge_tree=False,
        remove_comments=False,
    )
    root = etree.fromstring(value, parser=parser)
    if any(element.tag in _ACTIVE_XML_TAGS for element in root.iter()):
        _reject()
    return root


def _resolved_relationship_target(rels_name: str, target: str) -> str:
    if (
        not target
        or target.startswith(("/", "\\"))
        or "\\" in target
        or _DRIVE_PATH.match(target) is not None
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) is not None
    ):
        _reject()
    if rels_name == _ROOT_RELS:
        base = ""
    else:
        owner_directory = posixpath.dirname(posixpath.dirname(rels_name))
        base = owner_directory
    resolved = posixpath.normpath(posixpath.join(base, target))
    if resolved.startswith("../") or resolved in {"", ".", ".."}:
        _reject()
    return resolved


def _relationship_owner(rels_name: str) -> str | None:
    if rels_name == _ROOT_RELS:
        return None
    directory, filename = posixpath.split(rels_name)
    if posixpath.basename(directory) != "_rels" or not filename.casefold().endswith(
        ".rels"
    ):
        _reject()
    owner_directory = posixpath.dirname(directory)
    owner_name = filename[:-5]
    owner = posixpath.join(owner_directory, owner_name)
    if not owner:
        _reject()
    return owner


def _content_type_overrides(
    content_types: etree._Element, member_names: set[str]
) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for element in content_types:
        if element.tag != f"{{{_CONTENT_TYPE_NS}}}Override":
            continue
        part_name = element.get("PartName") or ""
        content_type = element.get("ContentType") or ""
        normalized_part_name = part_name.removeprefix("/")
        if (
            not part_name.startswith("/")
            or part_name == "/"
            or part_name.count("/") < 1
            or normalized_part_name
            != unicodedata.normalize("NFC", normalized_part_name)
            or "\\" in normalized_part_name
            or ":" in normalized_part_name
            or any(
                component in {"", ".", ".."}
                for component in normalized_part_name.split("/")
            )
            or posixpath.normpath(normalized_part_name) != normalized_part_name
            or normalized_part_name not in member_names
            or normalized_part_name in overrides
            or not content_type
        ):
            _reject()
        overrides[normalized_part_name] = content_type
    return overrides


def _validate_relationship_references(
    roots: dict[str, etree._Element],
    relationships: dict[str | None, dict[str, tuple[str, str]]],
) -> None:
    for part_name, root in roots.items():
        if part_name.casefold().endswith(".rels") or part_name == _CONTENT_TYPES:
            continue
        available = relationships.get(part_name, {})
        for element in root.iter():
            for attribute_name, relationship_id in element.attrib.items():
                attribute = etree.QName(attribute_name)
                if attribute.namespace != _OFFICE_REL_NS:
                    continue
                if attribute.localname not in {"id", "embed", "link"}:
                    continue
                if not relationship_id or relationship_id not in available:
                    _reject()


def _validate_header_footer_parts(
    roots: dict[str, etree._Element],
    allowed_parts: tuple[str, ...],
    overrides: dict[str, str],
    relationships: dict[str | None, dict[str, tuple[str, str]]],
) -> None:
    document_relationships = relationships.get(_MAIN_PART, {})
    document = roots[_MAIN_PART]
    part_contracts = (
        ("hdr", _HEADER_CONTENT_TYPE, _HEADER_REL, "headerReference"),
        ("ftr", _FOOTER_CONTENT_TYPE, _FOOTER_REL, "footerReference"),
    )
    for (
        root_name,
        content_type,
        relationship_type,
        reference_name,
    ) in part_contracts:
        candidate_parts = {
            part_name
            for part_name, root in roots.items()
            if root.tag == f"{{{_WORD_NS}}}{root_name}"
        }
        candidate_parts.update(
            part_name
            for part_name, declared_content_type in overrides.items()
            if declared_content_type == content_type
        )
        candidate_parts.update(
            target
            for found_type, target in document_relationships.values()
            if found_type == relationship_type
        )
        for part_name in candidate_parts:
            root = roots.get(part_name)
            if (
                part_name not in allowed_parts
                or root is None
                or root.tag != f"{{{_WORD_NS}}}{root_name}"
                or overrides.get(part_name) != content_type
            ):
                _reject()
            matching_relationship_ids = {
                relationship_id
                for relationship_id, (
                    found_type,
                    target,
                ) in document_relationships.items()
                if found_type == relationship_type and target == part_name
            }
            referenced_ids = {
                element.get(f"{{{_OFFICE_REL_NS}}}id")
                for element in document.iter(f"{{{_WORD_NS}}}{reference_name}")
            }
            if not matching_relationship_ids or not (
                matching_relationship_ids & referenced_ids
            ):
                _reject()


def _validate_ooxml(
    parts: dict[str, bytes],
    member_names: set[str],
    allowed_parts: tuple[str, ...],
) -> dict[str, etree._Element]:
    content_types = _parse_xml(parts[_CONTENT_TYPES])
    if content_types.tag != f"{{{_CONTENT_TYPE_NS}}}Types":
        _reject()
    overrides = _content_type_overrides(content_types, member_names)
    if overrides.get(_MAIN_PART) != _MAIN_CONTENT_TYPE:
        _reject()
    if any(
        marker in (element.get("ContentType") or "").casefold()
        for element in content_types
        for marker in ("macroenabled", "activex", "oleobject")
    ):
        _reject()

    xml_content_types = {
        "application/xml",
        "application/vnd.openxmlformats-package.relationships+xml",
    }
    roots: dict[str, etree._Element] = {_CONTENT_TYPES: content_types}
    for name, value in parts.items():
        if name == _CONTENT_TYPES:
            continue
        declared_content_type = overrides.get(name, "").casefold()
        if (
            name.casefold().endswith((".xml", ".rels"))
            or declared_content_type in xml_content_types
            or declared_content_type.endswith("+xml")
        ):
            roots[name] = _parse_xml(value)

    root_office_targets: list[str] = []
    relationships: dict[str | None, dict[str, tuple[str, str]]] = {}
    for name, root in roots.items():
        if not name.casefold().endswith(".rels"):
            continue
        if root.tag != f"{{{_REL_NS}}}Relationships":
            _reject()
        owner = _relationship_owner(name)
        if owner is not None and owner not in member_names:
            _reject()
        owner_relationships = relationships.setdefault(owner, {})
        for relationship in root:
            if relationship.tag != f"{{{_REL_NS}}}Relationship":
                _reject()
            relationship_id = relationship.get("Id") or ""
            relationship_type = relationship.get("Type") or ""
            target_mode = relationship.get("TargetMode") or ""
            if (
                not relationship_id
                or not relationship_type
                or relationship_id in owner_relationships
                or target_mode not in {"", "Internal"}
                or relationship_type.casefold().endswith(_ACTIVE_RELATIONSHIP_SUFFIXES)
            ):
                _reject()
            resolved = _resolved_relationship_target(
                name, relationship.get("Target") or ""
            )
            if resolved not in member_names:
                _reject()
            owner_relationships[relationship_id] = (relationship_type, resolved)
            if name == _ROOT_RELS and relationship_type == _OFFICE_DOCUMENT_REL:
                root_office_targets.append(resolved)
    if root_office_targets != [_MAIN_PART]:
        _reject()

    document = roots[_MAIN_PART]
    if document.tag != f"{{{_WORD_NS}}}document":
        _reject()
    bodies = document.findall(f"{{{_WORD_NS}}}body")
    if len(bodies) != 1:
        _reject()
    _validate_relationship_references(roots, relationships)
    _validate_header_footer_parts(roots, allowed_parts, overrides, relationships)
    for part_name, root in roots.items():
        if (
            part_name.casefold().startswith("word/")
            and part_name not in allowed_parts
            and any(
                type(element.tag) is str
                and etree.QName(element.tag).namespace == _WORD_NS
                for element in root.iter()
            )
        ):
            _reject()
    return roots


def _table_shapes(root: etree._Element) -> tuple[tuple[int, tuple[int, ...]], ...]:
    shapes = []
    for table in root.iter(f"{{{_WORD_NS}}}tbl"):
        rows = table.findall(f"{{{_WORD_NS}}}tr")
        shapes.append(
            (
                len(rows),
                tuple(len(row.findall(f"{{{_WORD_NS}}}tc")) for row in rows),
            )
        )
    return tuple(shapes)


def _validate_anchors(
    contract: TemplateContractManifest, roots: dict[str, etree._Element]
) -> dict[str, tuple[tuple[int, tuple[int, ...]], ...]]:
    shapes = {
        part: _table_shapes(root)
        for part, root in roots.items()
        if part in contract.allowed_parts
    }
    for anchor in contract.required_anchors:
        if anchor.startswith("part:"):
            if anchor.removeprefix("part:") not in roots:
                _reject()
            continue
        table_match = _TABLE_ANCHOR.fullmatch(anchor)
        if table_match is not None:
            part = table_match.group("part")
            rows = int(table_match.group("rows"))
            columns = int(table_match.group("columns"))
            if not any(
                row_count == rows and column_counts == (columns,) * rows
                for row_count, column_counts in shapes.get(part, ())
            ):
                _reject()
            continue
        if re.fullmatch(r"legacy:[a-z][a-z0-9_]*:root", anchor) is not None:
            if _MAIN_PART not in roots:
                _reject()
            continue
        _reject()
    return shapes


def _token_occurrences(
    contract: TemplateContractManifest, roots: dict[str, etree._Element]
) -> tuple[TemplateTokenOccurrence, ...]:
    descriptors = {token.token_id: token for token in contract.tokens}
    occurrences: list[TemplateTokenOccurrence] = []
    counts: Counter[str] = Counter()
    for part_name in contract.allowed_parts:
        root = roots.get(part_name)
        if root is None:
            continue
        for paragraph_index, paragraph in enumerate(root.iter(f"{{{_WORD_NS}}}p")):
            text = "".join(
                node.text or "" for node in paragraph.iter(f"{{{_WORD_NS}}}t")
            )
            matches = list(_TOKEN.finditer(text))
            remainder = _TOKEN.sub("", text)
            if (
                "{{" in remainder
                or "}}" in remainder
                or "{%" in remainder
                or "%}" in remainder
            ):
                _reject()
            for match in matches:
                token_id = match.group(1)
                if _TOKEN_ID.fullmatch(token_id) is None:
                    _reject()
                descriptor = descriptors.get(token_id)
                if descriptor is None or part_name not in descriptor.allowed_parts:
                    _reject()
                counts[token_id] += 1
                occurrences.append(
                    TemplateTokenOccurrence(
                        token_id=token_id,
                        value_kind=descriptor.value_kind,
                        part_name=part_name,
                        location=f"paragraph:{paragraph_index}",
                    )
                )
    for descriptor in contract.tokens:
        count = counts[descriptor.token_id]
        if descriptor.required and count == 0:
            _reject()
        if descriptor.occurrence == "single" and count > 1:
            _reject()
    return tuple(occurrences)


def validate_upload(
    content: bytes,
    filename: str,
    content_type: str,
    contract: TemplateContractManifest,
) -> TemplateValidationReceipt:
    """Validate one in-memory DOCX candidate without persistence or I/O side effects."""

    _validate_public_inputs(content, filename, content_type, contract)
    try:
        retained, member_summaries = _read_members(content)
        member_names = {item["name"] for item in member_summaries}
        roots = _validate_ooxml(retained, member_names, contract.allowed_parts)
        shapes = _validate_anchors(contract, roots)
        occurrences = _token_occurrences(contract, roots)
        structure_summary = sha256(
            json.dumps(
                {
                    "members": member_summaries,
                    "tables": {part: shape for part, shape in sorted(shapes.items())},
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("ascii")
        ).hexdigest()
    except TemplateCenterError:
        raise
    except (
        BadZipFile,
        etree.XMLSyntaxError,
        OSError,
        RuntimeError,
        ValueError,
        _Rejected,
    ) as error:
        raise TemplateCenterError(TemplateErrorCode.VALIDATION_FAILED) from error
    return TemplateValidationReceipt(
        content_sha256=sha256(content).hexdigest(),
        size_bytes=len(content),
        mime_type=DOCX_MIME_TYPE,
        extension=".docx",
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        structural_profile_id=contract.structural_profile_id,
        structural_profile_version=contract.structural_profile_version,
        structure_summary_sha256=structure_summary,
        token_occurrences=occurrences,
        validator_version=VALIDATOR_VERSION,
    )
