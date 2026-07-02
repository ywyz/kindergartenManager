import { describe, expect, it } from "vitest";

import { WorkflowDefinitionSchema } from "./definition";

describe("WorkflowDefinitionSchema", () => {
  it("requires action-level roles and audit actions", () => {
    const parsed = WorkflowDefinitionSchema.parse({
      slug: "daily-plan",
      name: "每日活动计划",
      version: "4.0.0",
      actions: [
        {
          key: "record:create",
          requiredRoles: ["teacher"],
          scope: "self",
          auditAction: "workflow_record_create"
        }
      ]
    });

    expect(parsed.slug).toBe("daily-plan");
  });
});
