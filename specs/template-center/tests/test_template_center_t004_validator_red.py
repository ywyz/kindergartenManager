"""T004 stable RED for the public, side-effect-free upload validator.

Every package in this file is assembled from synthetic OOXML bytes.  The tests
do not read repository templates, touch persistence ports, or cross into T005.
"""

from __future__ import annotations

import builtins
from dataclasses import FrozenInstanceError
from hashlib import sha256
from importlib import import_module
from io import BytesIO
from pathlib import Path
import socket
import unicodedata
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _api():
    return import_module("app.service.template_center")


def _contract(*, tokens=(), anchors=("part:word/document.xml",)):
    api = _api()
    return api.TemplateContractManifest(
        contract_id="kg.template.daily_plan.synthetic",
        contract_version=1,
        placeholder_contract_version=1,
        structural_profile_id="synthetic.daily_plan.v1",
        structural_profile_version=1,
        renderer_id="kg.renderer.daily_plan.synthetic.v1",
        parser_id="kg.parser.daily_plan.synthetic.v1",
        allowed_parts=("word/document.xml",),
        required_anchors=anchors,
        tokens=tokens,
    )


def _token(
    token_id: str = "kg.daily_plan.title",
    *,
    required: bool = True,
    occurrence: str = "single",
):
    api = _api()
    return api.TemplateTokenDescriptor(
        token_id=token_id,
        value_kind="text",
        required=required,
        occurrence=occurrence,
        allowed_parts=("word/document.xml",),
    )


def _paragraph(*runs: str) -> str:
    return (
        "<w:p>"
        + "".join(f'<w:r><w:t xml:space="preserve">{run}</w:t></w:r>' for run in runs)
        + "</w:p>"
    )


def _table(rows: int = 2, columns: int = 2) -> str:
    cells = "".join(f"<w:tc>{_paragraph('cell')}</w:tc>" for _ in range(columns))
    return (
        "<w:tbl>" + "".join(f"<w:tr>{cells}</w:tr>" for _ in range(rows)) + "</w:tbl>"
    )


def _document_xml(*body: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>'
        + "".join(body)
        + "<w:sectPr/></w:body></w:document>"
    ).encode("utf-8")


def _content_types(
    *, macro_enabled: bool = False, extra_overrides: tuple[str, ...] = ()
) -> bytes:
    main_type = (
        "application/vnd.ms-word.document.macroEnabled.main+xml"
        if macro_enabled
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'<Override PartName="/word/document.xml" ContentType="{main_type}"/>'
        + "".join(extra_overrides)
        + "</Types>"
    ).encode("utf-8")


def _root_relationships(
    *, target: str = "word/document.xml", external: bool = False
) -> bytes:
    mode = ' TargetMode="External"' if external else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        f'Target="{target}"{mode}/></Relationships>'
    ).encode("utf-8")


def _empty_relationships() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    ).encode("utf-8")


def _docx(
    document: bytes | None = None,
    *,
    extra: tuple[tuple[str | ZipInfo, bytes], ...] = (),
    content_types: bytes | None = None,
    root_relationships: bytes | None = None,
    document_relationships: bytes | None = None,
    compression: int = ZIP_DEFLATED,
) -> bytes:
    members: tuple[tuple[str | ZipInfo, bytes], ...] = (
        ("[Content_Types].xml", content_types or _content_types()),
        ("_rels/.rels", root_relationships or _root_relationships()),
        ("word/document.xml", document or _document_xml(_paragraph("safe"))),
        (
            "word/_rels/document.xml.rels",
            document_relationships or _empty_relationships(),
        ),
    ) + extra
    output = BytesIO()
    with ZipFile(output, "w", compression=compression) as archive:
        for name, value in members:
            archive.writestr(name, value)
    return output.getvalue()


def _validate(
    content: bytes,
    *,
    filename: str = "candidate.docx",
    content_type: str = DOCX_MIME,
    contract=None,
):
    api = _api()
    return api.validate_upload(
        content=content,
        filename=filename,
        content_type=content_type,
        contract=contract or _contract(),
    )


def _assert_rejected(content: bytes, **kwargs) -> None:
    api = _api()
    with pytest.raises(api.TemplateCenterError) as caught:
        _validate(content, **kwargs)
    assert caught.value.code in {
        api.TemplateErrorCode.INPUT_INVALID,
        api.TemplateErrorCode.VALIDATION_FAILED,
    }
    assert repr(content[:64]) not in repr(caught.value)


def test_t004_valid_receipt_is_frozen_sanitized_and_content_bound():
    api = _api()
    token = _token()
    content = _docx(
        _document_xml(
            _paragraph("prefix ", "{{kg.daily_", "plan.title}}", " suffix"), _table()
        )
    )

    receipt = _validate(
        content,
        contract=_contract(
            tokens=(token,),
            anchors=("part:word/document.xml", "table:word/document.xml:2x2"),
        ),
    )

    assert type(receipt) is api.TemplateValidationReceipt
    assert receipt.content_sha256 == sha256(content).hexdigest()
    assert receipt.size_bytes == len(content)
    assert receipt.mime_type == DOCX_MIME
    assert receipt.extension == ".docx"
    assert receipt.contract_id == "kg.template.daily_plan.synthetic"
    assert receipt.contract_version == 1
    assert receipt.structural_profile_id == "synthetic.daily_plan.v1"
    assert receipt.structural_profile_version == 1
    assert len(receipt.structure_summary_sha256) == 64
    assert receipt.validator_version == "template-upload-validator.v1"
    assert len(receipt.token_occurrences) == 1
    occurrence = receipt.token_occurrences[0]
    assert type(occurrence) is api.TemplateTokenOccurrence
    assert occurrence.token_id == "kg.daily_plan.title"
    assert occurrence.value_kind == "text"
    assert occurrence.part_name == "word/document.xml"
    assert occurrence.location == "paragraph:0"
    assert "prefix" not in repr(receipt)
    assert "suffix" not in repr(receipt)
    with pytest.raises(FrozenInstanceError):
        receipt.size_bytes = 1


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("../escape.docx", DOCX_MIME),
        ("/tmp/escape.docx", DOCX_MIME),
        (r"nested\\escape.docx", DOCX_MIME),
        ("nested/escape.docx", DOCX_MIME),
        ("candidate.docm", DOCX_MIME),
        ("candidate.dotm", DOCX_MIME),
        (".~lock.candidate.docx#", DOCX_MIME),
        ("candidate\x00.docx", DOCX_MIME),
        ("candidate\n.docx", DOCX_MIME),
        ("candidate:payload.docx", DOCX_MIME),
        (unicodedata.normalize("NFD", "café.docx"), DOCX_MIME),
        ("candidate.docx", "application/zip"),
        ("candidate.docx", DOCX_MIME.upper()),
    ],
)
def test_t004_rejects_unsafe_filename_or_non_exact_mime(filename, content_type):
    _assert_rejected(_docx(), filename=filename, content_type=content_type)


@pytest.mark.parametrize(
    "overrides",
    [
        {"content": bytearray(b"not-bytes")},
        {"filename": b"candidate.docx"},
        {"content_type": None},
        {"contract": object()},
    ],
    ids=["content", "filename", "content-type", "contract"],
)
def test_t004_rejects_wrong_public_input_types(overrides):
    values = {
        "content": _docx(),
        "filename": "candidate.docx",
        "content_type": DOCX_MIME,
        "contract": _contract(),
    }
    values.update(overrides)
    api = _api()
    with pytest.raises(api.TemplateCenterError) as caught:
        api.validate_upload(**values)
    assert caught.value.code is api.TemplateErrorCode.INPUT_INVALID


def test_t004_is_side_effect_free_and_does_not_mutate_candidate(monkeypatch):
    content = _docx()
    original = bytes(content)

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "validator crossed a forbidden filesystem/network boundary"
        )

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    receipt = _validate(content)
    assert content == original
    assert receipt.content_sha256 == sha256(original).hexdigest()


def test_t004_rejects_non_zip_and_truncated_zip():
    _assert_rejected(b"not an OOXML ZIP")
    _assert_rejected(_docx()[:-9])


def test_t004_rejects_missing_or_invalid_mandatory_ooxml_parts():
    malformed_types = b"<Types>"
    _assert_rejected(_docx(content_types=malformed_types))
    _assert_rejected(_docx(root_relationships=b"<Relationships>"))
    _assert_rejected(
        _docx(root_relationships=_root_relationships(target="word/missing.xml"))
    )
    _assert_rejected(_docx(content_types=_content_types(macro_enabled=True)))


@pytest.mark.parametrize(
    ("member_name", "member_bytes"),
    [
        ("word/vbaProject.bin", b"macro"),
        ("word/activeX/activeX1.bin", b"active-x"),
        ("word/embeddings/oleObject1.bin", b"ole"),
        ("customUI/customUI.xml", b"<customUI/>"),
        ("word/../escape.xml", b"<escape/>"),
        (r"word\\escape.xml", b"<escape/>"),
        ("/absolute.xml", b"<escape/>"),
        ("word/payload:alt.xml", b"<escape/>"),
    ],
)
def test_t004_rejects_active_or_unsafe_zip_members(member_name, member_bytes):
    _assert_rejected(_docx(extra=((member_name, member_bytes),)))


def test_t004_rejects_duplicate_directory_symlink_and_too_many_members():
    with pytest.warns(UserWarning, match="Duplicate name"):
        duplicate = _docx(
            extra=(("word/document.xml", _document_xml(_paragraph("duplicate"))),)
        )
    _assert_rejected(duplicate)

    directory = ZipInfo("word/fake/")
    _assert_rejected(_docx(extra=((directory, b""),)))

    symlink = ZipInfo("word/link.xml")
    symlink.create_system = 3
    symlink.external_attr = (0o120777 & 0xFFFF) << 16
    _assert_rejected(_docx(extra=((symlink, b"/etc/passwd"),)))

    extras = tuple((f"customXml/item{index}.xml", b"<root/>") for index in range(253))
    _assert_rejected(_docx(extra=extras))


def test_t004_rejects_part_over_compression_ratio_limit():
    _assert_rejected(_docx(extra=(("customXml/large.xml", b"A" * 200_000),)))


@pytest.mark.parametrize(
    "xml",
    [
        b"<w:document",
        (
            b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
            + _document_xml(_paragraph("&e;"))
        ),
        _document_xml('<w:altChunk xmlns:r="urn:r" r:id="rId9"/>'),
        _document_xml(
            '<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="file:///etc/passwd"/>'
        ),
    ],
    ids=["malformed", "doctype-entity", "alt-chunk", "xinclude"],
)
def test_t004_rejects_unsafe_or_malformed_xml(xml):
    _assert_rejected(_docx(document=xml))


@pytest.mark.parametrize(
    "field",
    [
        (
            '<w:p><w:fldSimple w:instr="INCLUDETEXT &quot;https://example.invalid/remote.docx&quot;">'
            "<w:r><w:t>remote</w:t></w:r></w:fldSimple></w:p>"
        ),
        (
            "<w:p><w:r><w:instrText>"
            "DDEAUTO c:\\\\windows\\\\system32\\\\cmd.exe"
            "</w:instrText></w:r></w:p>"
        ),
    ],
    ids=["include-text-attribute", "dde-auto-instr-text"],
)
def test_t004_rejects_active_word_field_instructions(field):
    _assert_rejected(_docx(_document_xml(field)))


@pytest.mark.parametrize(
    "target",
    [
        "https://example.invalid/payload",
        "file:///etc/passwd",
        r"\\server\\share\\payload",
        "C:/payload",
        "/absolute/payload",
    ],
)
def test_t004_rejects_external_or_absolute_relationship_targets(target):
    relationships = _root_relationships(target=target, external=True)
    _assert_rejected(_docx(root_relationships=relationships))


def test_t004_requires_declared_parts_and_table_shape_anchors():
    good_contract = _contract(
        anchors=("part:word/document.xml", "table:word/document.xml:2x2")
    )
    assert _validate(
        _docx(_document_xml(_paragraph("safe"), _table(2, 2))), contract=good_contract
    )

    _assert_rejected(
        _docx(_document_xml(_paragraph("safe"), _table(1, 2))),
        contract=good_contract,
    )
    _assert_rejected(_docx(), contract=_contract(anchors=("part:word/header1.xml",)))


def test_t004_accepts_declared_tokens_split_across_runs_in_one_paragraph():
    contract = _contract(tokens=(_token(),))
    content = _docx(_document_xml(_paragraph("{{kg.daily_", "plan.title}}")))
    receipt = _validate(content, contract=contract)
    assert tuple(item.token_id for item in receipt.token_occurrences) == (
        "kg.daily_plan.title",
    )


@pytest.mark.parametrize(
    "body",
    [
        (_paragraph("{{kg.daily_plan.unknown}}"),),
        (_paragraph("{{kg.daily_plan.title"),),
        (_paragraph("{{kg.daily_plan.title}}", "{{kg.daily_plan.title}}"),),
        (_paragraph("{{kg.daily_plan."), _paragraph("title}}")),
        (
            f'<w:tbl xmlns:w="{W_NS}"><w:tr><w:tc>{_paragraph("{{kg.daily_plan.")}</w:tc><w:tc>{_paragraph("title}}")}</w:tc></w:tr></w:tbl>',
        ),
        (_paragraph("{{kg.daily_plan.title|upper}}"),),
        (_paragraph("{% include '/tmp/value' %}"),),
    ],
    ids=[
        "unknown",
        "unclosed",
        "duplicate-single",
        "cross-paragraph",
        "cross-cell",
        "expression",
        "template-control",
    ],
)
def test_t004_rejects_unknown_malformed_cross_boundary_or_executable_tokens(body):
    _assert_rejected(
        _docx(_document_xml(*body)), contract=_contract(tokens=(_token(),))
    )


def test_t004_enforces_required_optional_and_repeatable_occurrence_contracts():
    required = _contract(tokens=(_token(),))
    _assert_rejected(_docx(), contract=required)

    optional = _contract(tokens=(_token(required=False),))
    assert _validate(_docx(), contract=optional)

    repeatable = _contract(tokens=(_token(occurrence="repeatable"),))
    receipt = _validate(
        _docx(
            _document_xml(
                _paragraph("{{kg.daily_plan.title}}"),
                _paragraph("{{kg.daily_plan.title}}"),
            )
        ),
        contract=repeatable,
    )
    assert len(receipt.token_occurrences) == 2


def test_t004_rejects_token_in_part_not_allowed_by_its_descriptor():
    api = _api()
    token = api.TemplateTokenDescriptor(
        token_id="kg.daily_plan.title",
        value_kind="text",
        required=True,
        occurrence="single",
        allowed_parts=("word/header1.xml",),
    )
    contract = api.TemplateContractManifest(
        contract_id="kg.template.daily_plan.synthetic",
        contract_version=1,
        placeholder_contract_version=1,
        structural_profile_id="synthetic.daily_plan.v1",
        structural_profile_version=1,
        renderer_id="kg.renderer.daily_plan.synthetic.v1",
        parser_id="kg.parser.daily_plan.synthetic.v1",
        allowed_parts=("word/document.xml", "word/header1.xml"),
        required_anchors=("part:word/document.xml",),
        tokens=(token,),
    )
    _assert_rejected(
        _docx(_document_xml(_paragraph("{{kg.daily_plan.title}}"))),
        contract=contract,
    )


def test_t004_rejects_undeclared_text_bearing_word_part():
    header = (
        f'<w:hdr xmlns:w="{W_NS}">'
        + _paragraph("{{kg.daily_plan.unknown}}")
        + "</w:hdr>"
    ).encode("utf-8")
    header_override = (
        '<Override PartName="/word/header1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
    )
    document_relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdHeader" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" '
        'Target="header1.xml"/></Relationships>'
    ).encode("utf-8")
    content = _docx(
        content_types=_content_types(extra_overrides=(header_override,)),
        document_relationships=document_relationships,
        extra=(("word/header1.xml", header),),
    )
    _assert_rejected(content)


def test_t004_rejects_token_inside_unsupported_text_box_boundary():
    text_box = (
        "<w:p><w:r><w:drawing><w:txbxContent>"
        + _paragraph("{{kg.daily_plan.title}}")
        + "</w:txbxContent></w:drawing></w:r></w:p>"
    )
    _assert_rejected(
        _docx(_document_xml(text_box)),
        contract=_contract(tokens=(_token(occurrence="repeatable"),)),
    )


def test_t004_allows_safe_internal_custom_xml_but_never_scans_it_for_tokens():
    custom_xml = (
        b'<?xml version="1.0"?><root><value>{{kg.daily_plan.unknown}}</value></root>'
    )
    content = _docx(extra=(("customXml/item1.xml", custom_xml),))
    receipt = _validate(content)
    assert receipt.token_occurrences == ()
