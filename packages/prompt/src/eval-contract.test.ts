import { describe, expect, it } from "vitest";

import {
  decidePromptRelease,
  summarizePromptEvalResults,
  type PromptEvalCaseResult
} from "./eval-contract";

const passingCase: PromptEvalCaseResult = {
  caseId: "case-1",
  jsonStructurePassed: true,
  requiredFieldsPassed: true,
  exportabilityPassed: true,
  markdownFreePassed: true,
  wordCountPassed: true
};

describe("prompt eval contract", () => {
  it("allows release when every eval gate passes", () => {
    const summary = summarizePromptEvalResults([passingCase, { ...passingCase, caseId: "case-2" }]);

    expect(summary.metrics).toEqual({
      jsonStructurePassRate: 1,
      requiredFieldPassRate: 1,
      exportabilityPassRate: 1,
      markdownFreePassRate: 1,
      wordCountPassRate: 1
    });
    expect(
      decidePromptRelease({
        summary,
        requestedByRole: "academic_director"
      })
    ).toEqual({
      allowed: true,
      mode: "standard",
      blockedReasons: []
    });
  });

  it("blocks release and returns concrete reasons when any gate fails", () => {
    const summary = summarizePromptEvalResults([
      passingCase,
      {
        ...passingCase,
        caseId: "case-2",
        requiredFieldsPassed: false,
        markdownFreePassed: false
      }
    ]);

    expect(
      decidePromptRelease({
        summary,
        requestedByRole: "academic_director"
      })
    ).toEqual({
      allowed: false,
      mode: "blocked",
      blockedReasons: ["required_fields", "markdown_free"]
    });
  });

  it("allows only academic directors to risk-override failed evals with a reason", () => {
    const summary = summarizePromptEvalResults([
      {
        ...passingCase,
        exportabilityPassed: false
      }
    ]);

    expect(
      decidePromptRelease({
        summary,
        requestedByRole: "academic_director",
        riskAcceptedReason: "本次只影响低风险说明文本，先发布后补样例。"
      })
    ).toMatchObject({
      allowed: true,
      mode: "risk_override",
      blockedReasons: ["exportability"]
    });

    for (const role of ["teacher", "grade_lead", "principal", "sys_admin"] as const) {
      expect(
        decidePromptRelease({
          summary,
          requestedByRole: role,
          riskAcceptedReason: "本次只影响低风险说明文本，先发布后补样例。"
        })
      ).toMatchObject({
        allowed: false,
        mode: "blocked"
      });
    }
  });

  it("blocks release when eval dataset is empty", () => {
    expect(
      decidePromptRelease({
        summary: summarizePromptEvalResults([]),
        requestedByRole: "academic_director"
      })
    ).toEqual({
      allowed: false,
      mode: "blocked",
      blockedReasons: ["empty_eval_dataset"]
    });
  });
});
