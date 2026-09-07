# WMP-9 production prerequisites evidence

## Gate conclusion

This prerequisite implementation gate is **PASS** at tested-code SHA
`72d759fc128b013c2345bd609875bb3e3d623ef1`. It establishes only the production
foundation needed to restart WMP-9. It does not execute or pass WMP-9 business/Office
acceptance, authorize WMP-10, or authorize release/production deployment.

- Start SHA: `0c39743ca4e5a36541347a48593f6206b56216bd`
- Tested-code SHA: `72d759fc128b013c2345bd609875bb3e3d623ef1`
- Evidence-closure SHA: the commit containing this ledger; its exact SHA and CI are recorded in Issue #55/#56/#57 after CI completes.
- Accepted design: ADR-0009 and `specs/wmp9-production-prerequisites/spec.md`
- Alembic head: `3c9f4b2a7d1e`, parent `2b7f3d5e9c8a`
- Final independent read-only Review: High / Medium / Low = **0 / 0 / 0**

## RED to GREEN record

The initial production seam was absent. Design/presence RED, Phase-A persistence and
authorization RED, Phase-B workflow/security RED, and Phase-C application/export/UI RED
were frozen before their corresponding implementation. Every reviewer finding was handled
as an independent failing test before the minimal fix. The review chain covered composite
tenant integrity, monotonic root/grant CAS, immutable-version/tombstone rules, dialect-safe
UTF-8/hash constraints, real SQLite migration triggers, grant revocation TOCTOU, transaction
cleanup, production composition/UI/download, cross-teacher audit, post-export binding drift,
bounded confirmation storage, and list-level fail-closed session/grant/plan revalidation.

## Repeated prerequisite node set

Both final runs used the same tested-code tree and produced:

- run 1: `75 collected / 75 passed`
- run 2: `75 collected / 75 passed`
- node-only SHA-256 for both runs: `8bf5e9b3e25fda30ac498277dfba288a66a2e822dfad05a25fdb5f3c3b18279d`

Complete ordered manifest:

```text
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_application_requires_trusted_session_and_returns_production_detached_snapshot
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_application_export_uses_real_wmp8_and_adapter_owned_exact_delivery[teacher-teacher-weekly_plan_id-weekly_activity_plan]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_application_export_uses_real_wmp8_and_adapter_owned_exact_delivery[teaching_admin-teaching_admin-monthly_plan_id-monthly_theme_activity_plan]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_application_rejects_sys_admin_and_cross_tenant_identity_before_export
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_export_discards_output_after_actor_plan_or_grant_revalidation_drift[actor]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_export_discards_output_after_actor_plan_or_grant_revalidation_drift[auth_epoch]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_export_discards_output_after_actor_plan_or_grant_revalidation_drift[plan]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_export_discards_output_after_actor_plan_or_grant_revalidation_drift[grant]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_active_binding_drift_in_wmp8_is_not_delivered_or_retried
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_export_has_zero_file_preview_or_export_record_persistence
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_weekly_monthly_ui_is_a_protected_callback_and_main_registers_one_route
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_cross_teacher_read_and_export_append_content_free_audit
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_application_and_ui_expose_real_review_and_delete_workflow_entry
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_main_registers_fail_closed_production_composition_startup
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_released_local_word_port_uses_fixed_qualified_template[weekly_activity_plan]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_released_local_word_port_uses_fixed_qualified_template[monthly_theme_activity_plan]
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_application_workflow_entry_runs_archive_and_confirmed_draft_delete
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_review_finding_application_rechecks_binding_after_exporter_returns
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_review_finding_ui_list_and_details_use_authorized_snapshots
specs/wmp9-production-prerequisites/tests/test_application_export_ui_red.py::test_review_finding_list_fails_closed_on_midstream_session_drift
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_h1_archive_uses_the_single_closed_authorization_port
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_m1_delivery_seam_owns_opaque_result_unwrapping
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_m2_draft_delete_retains_root_tombstone_without_audit_fk
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_m3_all_text_limits_use_exact_utf8_byte_units
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_m4_presence_red_cannot_be_used_as_the_functional_green_gate
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_l1_alembic_scope_is_exactly_six_tables
specs/wmp9-production-prerequisites/tests/test_design_review_findings.py::test_m5_every_scalar_narrative_field_has_an_exact_utf8_limit
specs/wmp9-production-prerequisites/tests/test_phase_a_persistence_authorization.py::test_phase_a_migration_is_single_child_of_current_head
specs/wmp9-production-prerequisites/tests/test_phase_a_persistence_authorization.py::test_phase_a_model_constraints_cover_identity_status_order_and_tenant
specs/wmp9-production-prerequisites/tests/test_phase_a_persistence_authorization.py::test_phase_a_repository_is_tenant_scoped_and_uses_exact_root_cas
specs/wmp9-production-prerequisites/tests/test_phase_a_persistence_authorization.py::test_phase_a_scope_grant_is_explicit_and_audit_is_append_only
specs/wmp9-production-prerequisites/tests/test_phase_a_persistence_authorization.py::test_phase_a_authorization_matrix_uses_db_actor_and_exact_grants
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_h1_composite_tenant_foreign_keys_reject_mismatched_version_and_day
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_h2_root_cas_requires_existing_same_tenant_plan_version
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_h4_grant_revision_uses_expected_revision_cas
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_m1_grant_active_state_and_revocation_timestamp_are_xor
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_m3_digest_columns_reject_non_hex_64_character_values
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_h3_repository_exposes_narrow_draft_purge_not_general_delete
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_h5_generic_root_cas_cannot_delete_or_clear_current_pointer
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_m6_draft_purge_removes_all_never_submitted_body_history
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_m6_ever_submitted_history_makes_delete_permanently_ineligible
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_m4_real_sqlite_alembic_round_trip_installs_append_only_triggers
specs/wmp9-production-prerequisites/tests/test_phase_a_review_findings_red.py::test_h6_root_cas_only_advances_to_the_immediate_successor
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.core.models.weekly_monthly_plan-WeeklyMonthlyPlan]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.core.models.weekly_monthly_plan-WeeklyMonthlyPlanVersion]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.core.models.weekly_monthly_plan-WeeklyActivityPlanDay]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.core.models.weekly_monthly_plan-MonthlyThemeActivityItem]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.core.models.weekly_monthly_plan-WeeklyMonthlyScopeGrant]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.core.models.weekly_monthly_plan-WeeklyMonthlyAuditEvent]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.repository.weekly_monthly_plan_repository-SqlAlchemyPlanAggregateReadRepository]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.service.weekly_monthly_plans.authorization-DatabasePlanAuthorizationAdapter]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.service.weekly_monthly_plans.workflow-WeeklyMonthlyWorkflowService]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.service.weekly_monthly_plans.application-WeeklyMonthlyApplicationService]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.service.weekly_monthly_plans.application-build_weekly_monthly_application]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.integration.word_export.weekly_monthly_template_adapter-ReleasedWeeklyMonthlyTemplateAdapter]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_required_production_seam_exists[app.ui.pages.weekly_monthly_plans-weekly_monthly_plans_page]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_alembic_migration_creates_each_approved_table[weekly_monthly_plan]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_alembic_migration_creates_each_approved_table[weekly_monthly_plan_version]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_alembic_migration_creates_each_approved_table[weekly_activity_plan_day]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_alembic_migration_creates_each_approved_table[monthly_theme_activity_item]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_alembic_migration_creates_each_approved_table[weekly_monthly_scope_grant]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_alembic_migration_creates_each_approved_table[weekly_monthly_audit_event]
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_main_registers_the_protected_weekly_monthly_page
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_closed_plan_action_includes_archive_before_workflow_green
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_existing_export_record_schema_is_not_extended_for_wmp9
specs/wmp9-production-prerequisites/tests/test_wmp9_production_prerequisites_red.py::test_design_is_frozen_and_explicitly_authorized
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_legal_state_graph_creates_immutable_versions_and_uses_cas
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_self_review_and_cross_teacher_scope_are_fail_closed
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_draft_delete_consumes_confirmation_and_keeps_tombstone
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_replay_and_stale_callback_do_not_publish_or_audit_success
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_audit_failure_rolls_back_lifecycle_and_audit_is_content_free
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_inactive_role_epoch_and_session_drift_fail_closed
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_review_finding_grant_revoked_after_authorize_fails_closed
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_review_finding_rejection_closes_transaction
specs/wmp9-production-prerequisites/tests/test_workflow_security_red.py::test_review_finding_confirmation_store_is_bounded_and_prunes_expired
```

## Regression evidence

- WMP-5/WMP-6/WMP-7/WMP-8: `155 passed`
- Complete weekly/monthly suite: `272 passed`
- Template Center implemented gates: `239 passed`
- Template Center full directory: `240 passed / 12 expected future RED`; the 12 are the already-recorded, unauthorized T007-T009/template CRUD, preview/export and backup/restore slices.
- Repository `tests/`: `1162 passed / 1 skipped`
- Agent Foundation: `261 passed`
- Permission/session/audit/Word/export targeted regression: `346 passed`
- Unfiltered repository diagnostic after the new F009 table allowlist: `2267 passed / 1 skipped / 15 known pre-existing RED` (12 unauthorized Template Center future RED, two historical W007/W008 documentation RED, and one bootstrap diagnostic wording RED). None was introduced by this gate and none was implemented here.
- Changed Python Ruff check: PASS
- Changed Python Ruff format check: PASS
- `git diff --check`: PASS
- Fresh SQLite Alembic upgrade and append-only trigger behavior: PASS
- Isolated MySQL 8.4.11 Alembic `upgrade -> downgrade -> upgrade` and ORM metadata creation: PASS

## Exact-SHA CI

For tested-code SHA `72d759fc128b013c2345bd609875bb3e3d623ef1`:

- Quality run [34093237305](https://github.com/ywyz/kindergartenManager/actions/runs/34093237305): **success**, exact `headSha` match.
- CodeQL run [34093236646](https://github.com/ywyz/kindergartenManager/actions/runs/34093236646): **success**, exact `headSha` match; actions, JavaScript/TypeScript and Python jobs all succeeded.

## Scope and persistence boundary

The gate adds the approved six-table aggregate/grant/audit schema, the single production
`PlanAuthorizationPort` adapter, immutable lifecycle/CAS/delete workflows, protected
application/UI entries, content-free append-only cross-teacher audit, and the fixed released
weekly/monthly template connection to the WMP-8 exporter. Tests prove no `ExportRecord`,
preview, export file, template asset, or unauthorized business mutation is written by export.
No break-glass path exists; sys_admin daily teaching access remains denied.

Windows Word and Linux LibreOffice external DOCX compatibility acceptance was deliberately not run. These clients do
not host separate KindergartenManager applications; the product itself is the cloud-hosted online Web system.
No release, image build, migration execution against production, or deployment was performed.
