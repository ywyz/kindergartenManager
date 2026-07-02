import { describe, expect, it } from "vitest";

import { CORE_WORKFLOW_ACTIONS, WorkflowActionSchema, canRolePerform } from "./workflow-action";

describe("workflow action contracts", () => {
  it("declares auditable role-gated actions", () => {
    for (const action of CORE_WORKFLOW_ACTIONS) {
      expect(() => WorkflowActionSchema.parse(action)).not.toThrow();
      expect(action.requiredRoles.length).toBeGreaterThan(0);
      expect(action.auditAction).toBeTruthy();
    }
  });

  it("keeps prompt release owned by the academic director role", () => {
    expect(canRolePerform("academic_director", "prompt:release")).toBe(true);
    expect(canRolePerform("teacher", "prompt:release")).toBe(false);
    expect(canRolePerform("sys_admin", "prompt:release")).toBe(false);
  });

  it("keeps backup restore owned by the system administrator role", () => {
    expect(canRolePerform("sys_admin", "backup:restore")).toBe(true);
    expect(canRolePerform("principal", "backup:restore")).toBe(false);
  });
});
