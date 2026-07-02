import { describe, expect, it } from "vitest";

import { buildApp } from "./app";

describe("buildApp", () => {
  it("serves live health checks", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/health/live" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({ status: "ok" });
  });

  it("serves ready health checks", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/health/ready" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({ status: "ok" });
  });

  it("serves role contracts without stale browser caching", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "GET",
      url: "/api/v1/contracts/roles"
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers["cache-control"]).toBe("no-store");
    expect(response.json()).toEqual({
      roles: [
        { code: "teacher", label: "教师" },
        { code: "grade_lead", label: "年级组长" },
        { code: "academic_director", label: "业务园长" },
        { code: "principal", label: "园长" },
        { code: "sys_admin", label: "系统管理员" }
      ]
    });
  });

  it("serves workflow action contracts with audit actions", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "GET",
      url: "/api/v1/contracts/workflow-actions"
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers["cache-control"]).toBe("no-store");
    expect(response.json()).toEqual({
      actions: [
        {
          key: "record:create",
          requiredRoles: ["teacher", "grade_lead", "academic_director", "principal"],
          scope: "self",
          auditAction: "workflow_record_create"
        },
        {
          key: "record:grade-review",
          requiredRoles: ["grade_lead"],
          scope: "grade",
          auditAction: "workflow_record_grade_review"
        },
        {
          key: "prompt:release",
          requiredRoles: ["academic_director"],
          scope: "tenant",
          auditAction: "prompt_release"
        },
        {
          key: "backup:restore",
          requiredRoles: ["sys_admin"],
          scope: "system",
          auditAction: "backup_restore"
        }
      ]
    });
  });
});
