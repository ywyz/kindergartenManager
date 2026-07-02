import { describe, expect, it } from "vitest";

import { buildContractViewModel } from "./contract-view-model";

describe("buildContractViewModel", () => {
  it("builds role options from shared role contracts", () => {
    expect(buildContractViewModel().roles).toEqual([
      { code: "teacher", label: "教师" },
      { code: "grade_lead", label: "年级组长" },
      { code: "academic_director", label: "业务园长" },
      { code: "principal", label: "园长" },
      { code: "sys_admin", label: "系统管理员" }
    ]);
  });

  it("separates business and system privileged actions", () => {
    const model = buildContractViewModel();

    expect(model.businessPrivilegedActions).toEqual([
      {
        key: "record:grade-review",
        scope: "grade",
        auditAction: "workflow_record_grade_review",
        requiredRoleLabels: ["年级组长"]
      },
      {
        key: "prompt:release",
        scope: "tenant",
        auditAction: "prompt_release",
        requiredRoleLabels: ["业务园长"]
      }
    ]);
    expect(model.systemPrivilegedActions).toEqual([
      {
        key: "backup:restore",
        scope: "system",
        auditAction: "backup_restore",
        requiredRoleLabels: ["系统管理员"]
      }
    ]);
  });
});
