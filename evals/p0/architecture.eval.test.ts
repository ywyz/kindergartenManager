import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  CORE_WORKFLOW_ACTIONS,
  ROLE_CODES,
  ROLE_LABELS
} from "@kindergarten/contracts";

const root = process.cwd();

function readJson<T>(path: string): T {
  return JSON.parse(readFileSync(join(root, path), "utf8")) as T;
}

describe("dev4.0 P0 architecture eval", () => {
  it("keeps docs, gate tests, and periodic evals wired into the root workflow", () => {
    const packageJson = readJson<{ scripts: Record<string, string> }>("package.json");
    const devPlan = readFileSync(join(root, "memory-bank/dev4.0/p0-dev-plan.md"), "utf8");
    const testPlan = readFileSync(join(root, "memory-bank/dev4.0/p0-test-plan.md"), "utf8");
    const wordPlan = readFileSync(join(root, "memory-bank/dev4.0/p0-word-spike.md"), "utf8");
    const backupPlan = readFileSync(
      join(root, "memory-bank/dev4.0/p0-backup-target-spike.md"),
      "utf8"
    );

    expect(packageJson.scripts["test:gate"]).toContain("vitest.config.ts");
    expect(packageJson.scripts["eval:periodic"]).toContain("vitest.eval.config.ts");
    expect(packageJson.scripts.check).toContain("pnpm eval:periodic");
    expect(devPlan).toContain("dev4.0 monorepo");
    expect(testPlan).toContain("pnpm eval:periodic");
    expect(devPlan).toContain("p0-word-spike.md");
    expect(wordPlan).toContain("generateStyledWordDocument");
    expect(wordPlan).toContain("w:eastAsia");
    expect(devPlan).toContain("p0-backup-target-spike.md");
    expect(backupPlan).toContain("writeVerifiedBackupObject");
    expect(backupPlan).toContain("WebDAV");
  });

  it("preserves the required online role model in the shared contract", () => {
    expect(ROLE_CODES).toEqual([
      "teacher",
      "grade_lead",
      "academic_director",
      "principal",
      "sys_admin"
    ]);
    expect(ROLE_LABELS).toEqual({
      teacher: "教师",
      grade_lead: "年级组长",
      academic_director: "业务园长",
      principal: "园长",
      sys_admin: "系统管理员"
    });
  });

  it("keeps privileged prompt and backup actions permission gated", () => {
    const promptRelease = CORE_WORKFLOW_ACTIONS.find(
      (action) => action.key === "prompt:release"
    );
    const backupRestore = CORE_WORKFLOW_ACTIONS.find(
      (action) => action.key === "backup:restore"
    );

    expect(promptRelease?.requiredRoles).toEqual(["academic_director"]);
    expect(promptRelease?.auditAction).toBe("prompt_release");
    expect(backupRestore?.requiredRoles).toEqual(["sys_admin"]);
    expect(backupRestore?.auditAction).toBe("backup_restore");
  });

  it("keeps CI aligned with P0 validation commands", () => {
    const ci = readFileSync(join(root, ".github/workflows/dev4-ci.yml"), "utf8");

    expect(ci).toContain("pnpm install --frozen-lockfile");
    expect(ci).toContain("pnpm lint");
    expect(ci).toContain("pnpm typecheck");
    expect(ci).toContain("pnpm test:gate");
    expect(ci).toContain("pnpm eval:periodic");
    expect(ci).toContain("pytest tests/test_dev4_planning_contract.py -q");
    expect(ci).toContain("pnpm audit:deps");
    expect(ci).toContain("pnpm run sbom:generate");
  });
});
