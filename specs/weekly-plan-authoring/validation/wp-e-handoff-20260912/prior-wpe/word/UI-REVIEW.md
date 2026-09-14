# Independent UI / page projection review

Reviewer: word_impl. Scope: UI callbacks, page_application/page_repository and home/menu/route wiring. Read-only application review; reviewer did not implement these modules. Excludes reviewer's own Word implementation. Not a full-repository independent review, not native browser or Word acceptance.

## Initial findings and follow-up

- P1 export wait accepted unflushed browser edits: fixed at WeeklyEditor.export by presentation_stamp before await and verification after final live validation. mark_dirty increments ui_revision. Late export results do not reach ui.download.
- Late check/generation/reduction results: check_saved verifies stamp and cancels the check; generated and reduction candidates are cancelled before entering UI proposal state when stamp drifted. Reviewed source, no additional finding in these result-publication branches.
- Late save/adopt service wait: revision check prevents immediate render after late widget input; save retains dirty state. This does not yet cover the subsequent async render window described below.
- Explicit failure feedback: LAYOUT_MESSAGES covers qualification, renderer/font, geometry/overflow, required fields and reduction limits. Earlier generic-feedback finding resolved.
- Source localization: source_check now includes source reference date and field label for each status. Earlier localization finding resolved.
- Tenant/current assignment choices and last-editor: scoped repository queries, last-editor preceded by authorized root read. No additional cross-tenant finding found in inspected scope.
- Real entry chain: /weekly-plan registered through weekly_monthly_plans; home/menu connect teacher route; callbacks use composition authoring/page/exporting/reduction. Five/six columns come from authoritative display; holiday morning labels come from authoring body and disabled controls. Existing two-teacher callback test covers no overwrite on reopen.

## OPEN P1: async render can still erase late input

app/ui/pages/shared_weekly_plan.py render() awaits authoring.header and page.last_editor, then host.clear() and recreates widgets from editor.edit.body without a presentation stamp check. save/adopt call render only after their earlier ui_revision checks, but user input during these subsequent header/last-editor awaits increments ui_revision and remains only in widgets. render then clears those widgets and replaces late values with the saved/adopted body.

Reproduction recommendation: in actual page-callback test, pause page.last_editor during the render invoked after save/adopt; mutate a textarea and invoke its on_change; release the wait; assert host.clear was not called and the late value remains visible. Hold this as an unmet late-input gate until double business RED/minimal fix and independent follow-up review. Main notified before code freeze.

## Evidence limits

ui/epoch-final-sqlite and epoch-final-mysql belong to implementer evidence. tests/test_wpe_ui_callbacks.py explicitly uses widget shims; these are native page callbacks with application/database behavior, not controlled browser acceptance. Main must retain separate exact-source browser evidence and final integration/reviewer roles. No new tests executed by this read-only reviewer.

## Exact reviewed file SHA256

- `app/ui/pages/shared_weekly_plan.py`: `4112f05c0f8ee75c8f112661ac2c022e6613da0c1cbc68a7a65595413e9146d9`
- `app/service/shared_weekly/page_application.py`: `fb4d3ba4cd23f0a9e2446193b57ab615e6a0c47d74a990bdb4fe27baf5425905`
- `app/repository/weekly_page_repository.py`: `7863379082b43cc47b64fed8882cae07e0f23a97bb48ba14ec9b817ddfdf1ff7`
- `app/ui/pages/home.py`: `69259a9c66aa34ea9edc20c82e85ce98ea01f8dce4bacdb37eeedfadc1d88e00`
- `app/ui/components/app_shell.py`: `d23825859ef1bd0c9ca616333f41d0afd611dd8aae7fafdddc572e5c5d549260`
- `app/ui/pages/weekly_monthly_plans.py`: `e1b12b67e13d6a2acc6e6bd8dc0917599e210eb4e7ae09e2aceae483fcce2bce`
- `tests/test_wpe_ui_callbacks.py`: `2c6c6d1e74a221a18174540d742073d21dc3799e98630eddec0a50e334c6cece`
- `tests/test_wpe_ui_navigation.py`: `ecf148ba2e55ba733e370bf85cb8ed4f3798c2661fa48fa30003d04830fb8d63`

## Additional OPEN P1 window in the same late-input gate

`WeeklyEditor.manual(values, slots)` receives values already captured by `flush`, but first awaits `live()` and only then captures `ui_revision`. Input during authentication changes the widgets/revision while the already-passed values remain stale; the post-auth revision is then accepted as baseline, so manual/save/render can overwrite the late input. `save`/`adopt` also capture revision after their first auth await. Freeze UI epochs before the first await where input snapshots already exist, and verify after auth before application mutation. Suggested native callback case: hold `require_bound_ui_session`, edit a textarea through its on_change, release auth, and verify the old snapshot is not accepted as current.

## Final follow-up on render/auth/label fixes

Independent source inspection confirms the requested three fixes:

1. `WeeklyEditor.live()` freezes presentation before the authentication await and validates immediately afterwards. `manual` can no longer accept old sampled widget values using a post-auth revision when input changed during that await.
2. `render()` freezes presentation before `header` / `last_editor` awaits and validates before `host.clear`; the identified late-input destruction in save/adopt's subsequent render is prevented.
3. `slot_label` accepts `TargetPath` directly and renders date plus the Chinese field label; `days.*` receives the same readable projection. `proposal_dialog` no longer converts `TargetPath` to repr. Test assertion verifies a real import dialog label and excludes `TargetPath(`.

Reviewed implementer `ui/last-review-sqlite.log`: 18 passed in 6.77s. This is source review plus inspected callback-test evidence, not a reviewer rerun or browser acceptance. The above three findings are CLOSED for the exact hashes below.

Remaining separately identified navigation window: `WeeklyEditor.open` and `reload` do not freeze/revalidate presentation across calendar/create/begin_authoring waits before replacing `self.edit`. If an already-open, initially clean page receives input while opening another week or reloading, later `render` captures the already-replaced edit state and can clear that input. Suggested callback probe: hold `begin_authoring` during open/reload, invoke a previous textarea's on_change, release, assert no late value is overwritten. This is outside the three requested fixes but means this review does not assert all possible UI await windows are closed. Main notified.

Exact current source hashes:

- `app/ui/pages/shared_weekly_plan.py`: `4d5c7fe04089db7fca91436555cd84f3b156b31f5d628d1d5bf785cd6d51e7a0`
- `tests/test_wpe_ui_callbacks.py`: `2d046c7bc88603e9ab22f5a9d78e85acd7ea46e251e7d120e7532647459e036c`
- `ui/last-review-sqlite.log`: `b8afbcd579eb6185a3cb40df32fd00978bd67e6186f20b5421310e02d1adc321`
- `ui/last-review-sqlite.json`: `4c7123fd187398e587f1995c8d653bf303f9f18177f0609cfd59749da2824bd3`

## Final navigation follow-up — inspected UI findings OPEN 0

Reviewed the frozen navigation fix and re-scanned every `self.edit` replacement, the sole `host.clear`, and success-view refresh call sites. `open`/`reload` now freeze presentation before their first await; open checks after calendar/creation; both acquire fresh editors then call `_replace_navigation`. That synchronous helper validates the original presentation before discarding the old editor or changing current UI state; on drift or old-editor rejection it discards the fresh editor and leaves the old current page unchanged. No await lies between the final validation and replacement. The previously reported navigation loss/leak finding is CLOSED.

The sole host.clear remains behind render's metadata-await presentation validation. Manual/save/adopt retain their revision checks and do not invoke success render after a late-input rejection; render independently covers its own subsequent awaited metadata. `live` covers auth awaits; result-publication guards remain on check/export/generation/reduction. Chinese TargetPath/date labels and explicit failure/source-location messages remain present. No additional finding was identified in this final scoped source review.

**Scoped conclusion: OPEN 0 for the UI/page-projection findings identified by word_impl, at the hashes below.** This is not a claim of exhaustive verification, not review of word_impl's own Word code, not remote CI, controlled cloud browser, real-model or Microsoft Word acceptance, and not WP-E COMPLETE. Main owns integration and final tested_code_sha binding.

Inspected native-callback regression: navigation cases hold begin_authoring for both open/reload, inject textarea change, then assert late widget content and old page-ticket set remain unchanged; final delivery SQLite log reports 18 passed. Implementer-run evidence, not reviewer rerun.

Final exact hashes:

- `app/ui/pages/shared_weekly_plan.py`: `7573551a942ce24e886ccf2a3a33c6fc0814d380fa2bda901cfd05183057859e`
- `tests/test_wpe_ui_callbacks.py`: `b3f70d3c64e02b86685c387dc17922e0f85ac95aa7b751d9b6f3975805910b00`
- `app/service/shared_weekly/page_application.py`: `fb4d3ba4cd23f0a9e2446193b57ab615e6a0c47d74a990bdb4fe27baf5425905`
- `app/repository/weekly_page_repository.py`: `7863379082b43cc47b64fed8882cae07e0f23a97bb48ba14ec9b817ddfdf1ff7`
- `ui/navigation-await-delivery-source.tar.gz`: `cec64f247f514dca67c564286d1a02a6e6b08301558e4f11310aebbcc3b9ce96`
- `ui/navigation-await-delivery-source.json`: `c73028e3332acd7335307d8c4c218815fb337e089bffaf6208d64a521cd69a49`
- `ui/navigation-await-delivery-sqlite.log`: `49cdf08f72be4b375cd90ef7a3f3f9bb24cd96c68c2efc21cfb55dfdebb07872`
- `ui/navigation-await-delivery-sqlite.json`: `24f7d938cc7a97a0916abfe87cfffa01c3144e21bdf9253a40f5b00cde3debd8`

## Final visible renderer status follow-up — OPEN 0 retained

Independently reviewed the final `fits` mapping and `tests/test_wpe_ui_actual_renderer.py`. `LAYOUT_MESSAGES["fits"]` now maps the actual successful WordPort reason to the same explicit Chinese success message as the retained `ok` alias; error and unknown reasons keep their failure messages. No authorization, export result, or layout gate was relaxed.

The new test constructs the real saved application/exporter with SharedWeeklyWordPort and actual LibreOffice rendering, using separately marked local-synthetic qualification. It invokes the real registered page callbacks through widget shims, checks that the application result is fits=True/pages=1/reason=fits, then checks the visible notice reports success and contains no failure statement. This supports the UI protocol mapping and avoids relying on a fake renderer result. It remains a widget-shim callback test, not native browser or Word evidence.

Inspected implementer evidence: ui/actual-fits-red1 and red2 record the visible mapping failure following actual successful rendering; ui/actual-fits-green reports 19 passed in 8.99s. No code changes or test rerun by this reviewer. **No new open finding in this final change; scoped UI review OPEN 0 retained.**

Exact latest hashes:

- `app/ui/pages/shared_weekly_plan.py`: `ae2227c1fdd431dc16e223697dbea19326b6f3321f654ea5ac061f1e7562f549`
- `tests/test_wpe_ui_actual_renderer.py`: `2e4ddc2cb61dcd97856298c2b5c2359c0ccdb90a927efbe977ddefe9da33b9c1`
- `tests/test_wpe_render_pipeline.py`: `2cab89d491ff67dffa26c1ee2bb92f43c6d0af3eb5d3b706130bf4a49b107f48`
- `ui/actual-fits-before.tar.gz`: `c4eee9fe96f83d66f9e4362d38f389f8a7237ceec04a618799fb3f30ea7d4fc7`
- `ui/actual-fits-red1.log`: `b0be4a68b1d06f9f3564f063b912845af22cfc69f666b71e65592a11dfc9c496`
- `ui/actual-fits-red2.log`: `d954033094f9dd372820748c229d7e0b7f0fe1a68a195d2ad89175bf0c7e65fd`
- `ui/actual-fits-green.log`: `541dbb469416b031fc4cc25ee794b86f150cae4f52a6cdc8c4f35f4e90869af5`
- `ui/actual-fits-green.json`: `78bb57e90cbe8ab1d3fb9886c5361c2d86cdd7ff97faac515d32c7eefd8dcf38`
- `ui/actual-fits-green-source.tar.gz`: `d8a8fadf77c7bf7f83d482786f17704dff1463b51eccdf23e0c99cd234ef196b`
