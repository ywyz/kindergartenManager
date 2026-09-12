# WP-E qualification and Word evidence review

Reviewer role: independent, read-only cross-module review. Reviewed at docs
successor `7c0acb9337534d0db60b9ff6d9e1abd09e382643`; the inspected product subset
is byte-identical to tested-code SHA
`9cde71655c30cafdc6ac4e99ed22509ad989b121`. No product source, catalog, remote
resource, or application configuration was changed. This report is not a
Microsoft Word qualification, catalog installation, remote CI result, or WP-E
completion claim.

## Correction to the initial review

The initial version of this report incorrectly treated `client` and `renderer`
as one identity. They are deliberately separate in the local contract:
`client` is the Microsoft Word product/version used for native acceptance, and
`renderer` is the actual Linux LibreOffice runtime checker. Thus the
LibreOffice-only branch in `SharedWeeklyWordPort.render_check`
(`app/integration/word_export/shared_weekly_word.py:369-377`) is compatible
with a production-role manifest whose client is Microsoft Word and whose
runtime renderer is LibreOffice.

The earlier temporary manifest that set `renderer` to Microsoft Word exercised
an unsupported configuration. It is not a business RED or a product finding;
the initial P1 conclusion is withdrawn.

I re-ran the control-flow probe with the identities correctly modelled: a
hash-valid `word-native` manifest with client `Microsoft Word for Microsoft 365
16.0` and renderer `LibreOffice 26.2.5.2 620(Build:2)` activated as
`qualified:native:1`; `render_check` returned `fits=True`, `pages=1`,
`reason=fits`. Its artifacts were synthetic and establish only the wiring,
never a Word qualification.

## Current supported behavior and unmet delivery inputs

No material source correctness finding was found in the separation of native
Word evidence from the local runtime checker. `LayoutAuthority` rejects a
synthetic role in production, requires a Microsoft Word client name in a
production manifest, content-verifies the manifest/artifacts, binds the
released UUID/version/contract/hash, and rechecks them at resolve/guard
(`app/service/shared_weekly/layout_authority.py:60-86, 138-223, 253-283`).

The default application calls `configure_shared_weekly_production` with no
injected port (`app/main.py:64-68`) and therefore uses
`SharedWeeklyWordPort()` (`app/service/shared_weekly/production_composition.py:29-56`).
It returns `qualification_required` until trusted application assembly supplies
a catalog and activates a binding. This is the specified fail-closed default,
not an independently established code defect or a basis to invent a production
operator model. The supported injection seam already accepts a trusted
`word_port`, and it exposes no teacher/UI activation API.

It is nevertheless an **unmet delivery input**: no actual Word-native catalog
manifest path/digest, selected tenant binding, activation record, or native
evidence bundle was supplied or installed during this authorized local review.
This reviewer did not perform an installation or make deployment/configuration
changes. A later separately authorized operator action must use the trusted
assembly seam, perform the documented activation with the then-current released
binding, and retain its own restart/reload evidence. Default fail-closed
behavior is not a formal export PASS.

## Evidence-matrix limit

The current catalog schema accepts exactly two fixtures, one for five and one
for six columns (`layout_authority.py:156-223`). Each fixture binds a body hash
and `docx`, `pdf`, `page-1.png`, and native-report hashes. It does not name
normal/long Chinese, multiple names, spaces, book-title marks, quantities,
dates, holiday cells, or newline scenarios.

Whether those cases are added to the manifest schema or separately bound in an
operator-reviewed checklist is a future qualification-contract choice; this
review does not require a source redesign without a specific installation
package. A separate checklist would need a recorded digest and explicit
association with catalog activation: the present authority validates only its
manifest and declared artifacts.

What is presently decisive is material absence. The available 829-item local
bundle contains LibreOffice `word/final-visual/5.*` and `6.*` artifacts and no
Microsoft Word native qualification manifest. It cannot supply the required
Word acceptance. A future separately authorized Word run must provide, and an
independent reviewer must verify:

- the exact `templates/weekplan.docx` SHA256
  `f6c17c137f04e29a68524ed400eb395984e93a16c234a065b5794d9f49a9347b`,
  profile `shared-weekly-v3.v1`, and generated DOCX byte hashes;
- the current target-tenant released weekly UUID, version, contract ID/version,
  and content hash;
- concrete Microsoft Word product/full version and its native-rendering
  context, plus the separately recorded actual runtime-renderer identity;
- for five and six columns, normal and long Chinese cases covering multi-name,
  space, `《》`, quantity, date, holiday, and newline inputs; their body,
  DOCX/PDF/screenshot hashes; and all native preview pages;
- an independent record opening every page in that specified Word product and
  checking SimSun resolution, clipping/font substitution, fixed counts, and
  the exact artifact hashes.

The historical three long two-page FAILs and compact synthetic candidates remain
historical evidence and must not be used to fill these inputs.

## Evidence checked

- Product subset SHA256 at tested code: `layout_authority.py`
  `0be1516a4abbdb9c72406140cd12579ac0186a177091248f0985f175b48b750a`,
  `layout_contracts.py`
  `d5d8617dd3c81076e59938d7ca290e048ec3e6aa0b00c89b3c561763b15a3aef`,
  `production_composition.py`
  `f1cb994c7b71b9c956fb06c4698b7c2bd2190fe012ce98a5aa0340d91a510177`,
  `shared_weekly_word.py`
  `7b690a24f6476d4965fb750a81a98790b0edad3c14ae154b94f7fbcbd0524bb7`,
  and `test_wpe_word_authority.py`
  `aa336b000b979c4c914212fa89f3cdc7a0d977e6abd966f9fe3bfb37c6707bb8`.
- Repository delivery manifest SHA256:
  `320fa1d244008a85070808937386de23be1bddedf508bcab236a882970274e2b`;
  it names 829 external local artifacts and tested-code SHA `9cde716…`.
- Current independent rerun:
  `/home/ywyz/code/kindergartenManager/.venv/bin/python -m pytest
  tests/test_wpe_word_layout.py tests/test_wpe_word_authority.py -q` →
  `20 passed in 8.48s`. This validates local/synthetic paths only.
- Earlier external `reduction/word-independent-review.json` records `20 passed`
  but its recorded Git HEAD is `3fcefdf08a4b6aa6d3d7d5eb674cac2fce180713`,
  not final tested code. It remains historical execution evidence, not an
  exact-SHA final review.

## Conclusion

No Word-native qualification is installed or evidenced. The production default
is appropriately fail closed and the reviewed client/renderer separation is
supported. WP-E remains `BLOCKED / NOT COMPLETE` until actual Microsoft Word
material and a separately authorized trusted catalog activation are completed.
No remote, release, Word, or Issue conclusion follows from this review.
