# Independent read-only Main export review

Reviewer: reduction_impl. Ownership separation: reviewer implemented reduction,
not the reviewed Main repository/migration/composition/export delivery code or
render-pipeline tests. No source edits, recursive delegation or database/remote
operations were performed for this review. Source SHA256 values and evidence-log
integrity checks are in main-export-independent-review.json (seven files).

Conclusion: no additional concrete correctness finding in this bounded review.
This is not a WP-E completion, native Word, cloud, remote CI or real-model PASS.
Final tested_code_sha and later source changes remain Main's responsibility.

Reviewed behavior:

- Repository queries are tenant-scoped and delivery is recorded only inside the
  current identity/source/root transaction. The audit stores actor/session,
  assignments, target revision, template binding and hashes; no document body,
  file path, preview or ExportRecord is added.
- Migration uses compatible BIGINT/MySQL and INTEGER/SQLite key types; composite
  FKs bind actor tenant, saved version and plan/class identity. Required fields,
  authorized-only action/outcome/reason and revision/hash constraints are present.
  UPDATE/DELETE are denied by database triggers; nonempty downgrade refuses.
  Old tables and their immutable history are not rebuilt by this migration.
- Production composition shares the exact authoring instance with reduction and
  export and obtains trusted token state from the current UI session. It does
  not create a new policy/root. Formal qualification remains fail-closed until
  valid independently reviewed native evidence is configured.
- Check consumes only explicitly saved, complete v3 body; rendering runs outside
  DB transactions. After renderer wait, saved target/page/binding/auth and live
  dependencies are rechecked. Final delivery owns page edit lock plus binding
  guard through authorization commit, with cancellation nonce checks before and
  after the final transaction. Current implementations return bytes without a
  further yielding operation after the final check.
- Export never calls AI or saves authoring versions. File cleanup remains inside
  the reviewed Word port TemporaryDirectory/process-finalization implementation.
  Export candidates are transient memory tickets and one-shot; commit-unknown
  reconciliation stores only operation metadata, reads the audit and never
  redelivers the consumed file or retries the operation.
- Actual-render pipeline tests use disposable application data and explicitly
  synthetic qualification, verify ordinary Chinese overflow, confirmed shorter
  candidate, explicit save/recheck, continued overflow with zero delivery, then
  explicit teacher edits and saved successful delivery. They do not claim every
  long plan fits or that LibreOffice is native Word acceptance.

Evidence reviewed, hashes revalidated:

- main/delivery-green: SQLite 24 PASS.
- main/export-migration-mysql: 24 PASS + one migration setup error from disk full;
  recorded exit 1 retained and not counted as business RED/PASS for that node.
- main/migration-mysql-retry: MySQL migration + actual render pipeline 4 PASS.
- main/actual-pipeline-chinese: earlier test AttributeError on wrong candidate
  attribute; correctly retained as test error, not product business RED. Current
  source uses candidate_value and later retry passes.

No independent test rerun was made for this additional review; the results above
retain Main's execution role. The earlier separate Word review did independently
run the 20 Word/layout tests and has its own evidence file.

## Foundation compatibility follow-up

Read-only review of the three-line change in
`specs/agent-foundation/tests/test_f009_zero_persistence_matrix_red.py`:
only exact `shared_weekly_export_audit` is added to the non-Agent business schema
allowlist. The restart test now explicitly requires that table to exist and its
rows to remain empty. Reflection still includes every database table, including
those absent from Base.metadata; snapshot/side-effect comparisons and generic
forbidden Agent schema checks remain intact. No production Agent code, tools or
WRITE permission changed. No finding. This is a schema-test compatibility update;
the earlier 260 PASS/1 failure is not a native business RED claim. The exact
reviewed test-file hash is appended to the accompanying JSON. No tests rerun by
this reviewer in this follow-up.
