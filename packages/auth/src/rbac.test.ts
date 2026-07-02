import { describe, expect, it } from "vitest";

import { authorizeWorkflowAction, type AuthorizationContext } from "./rbac";

const teacher: AuthorizationContext = {
  userId: 10,
  tenantId: 1,
  roles: ["teacher"]
};

const gradeLead: AuthorizationContext = {
  userId: 20,
  tenantId: 1,
  roles: ["grade_lead"],
  managedGradeIds: [2]
};

const academicDirector: AuthorizationContext = {
  userId: 30,
  tenantId: 1,
  roles: ["academic_director"]
};

const principal: AuthorizationContext = {
  userId: 40,
  tenantId: 1,
  roles: ["principal"]
};

const sysAdmin: AuthorizationContext = {
  userId: 50,
  tenantId: 1,
  roles: ["sys_admin"]
};

describe("authorizeWorkflowAction", () => {
  it("allows teachers to create only their own records", () => {
    expect(
      authorizeWorkflowAction(teacher, {
        actionKey: "record:create",
        resourceOwnerId: 10,
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: true, reason: "allowed" });

    expect(
      authorizeWorkflowAction(teacher, {
        actionKey: "record:create",
        resourceOwnerId: 11,
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: false, reason: "scope_denied:self" });
  });

  it("allows grade leads to review only managed grades", () => {
    expect(
      authorizeWorkflowAction(gradeLead, {
        actionKey: "record:grade-review",
        resourceGradeId: 2,
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: true, auditAction: "workflow_record_grade_review" });

    expect(
      authorizeWorkflowAction(gradeLead, {
        actionKey: "record:grade-review",
        resourceGradeId: 3,
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: false, reason: "scope_denied:grade" });

    expect(
      authorizeWorkflowAction(teacher, {
        actionKey: "record:grade-review",
        resourceGradeId: 2,
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: false, reason: "missing_required_role" });
  });

  it("keeps prompt release owned by academic directors", () => {
    expect(
      authorizeWorkflowAction(academicDirector, {
        actionKey: "prompt:release",
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: true, auditAction: "prompt_release" });

    expect(
      authorizeWorkflowAction(principal, {
        actionKey: "prompt:release",
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: false, reason: "missing_required_role" });

    expect(
      authorizeWorkflowAction(sysAdmin, {
        actionKey: "prompt:release",
        resourceTenantId: 1
      })
    ).toMatchObject({ allowed: false, reason: "missing_required_role" });
  });

  it("keeps backup restore owned by system administrators", () => {
    expect(
      authorizeWorkflowAction(sysAdmin, {
        actionKey: "backup:restore"
      })
    ).toMatchObject({ allowed: true, auditAction: "backup_restore" });

    expect(
      authorizeWorkflowAction(principal, {
        actionKey: "backup:restore"
      })
    ).toMatchObject({ allowed: false, reason: "missing_required_role" });
  });

  it("denies cross-tenant resources before checking non-system scopes", () => {
    expect(
      authorizeWorkflowAction(academicDirector, {
        actionKey: "prompt:release",
        resourceTenantId: 2
      })
    ).toMatchObject({ allowed: false, reason: "scope_denied:tenant" });

    expect(
      authorizeWorkflowAction(teacher, {
        actionKey: "record:create",
        resourceOwnerId: 10,
        resourceTenantId: 2
      })
    ).toMatchObject({ allowed: false, reason: "scope_denied:self" });
  });
});
