import type { RoleCode } from "@kindergarten/contracts";

import {
  DEFAULT_PROMPT_RELEASE_THRESHOLDS,
  type PromptReleaseThresholds,
  isPromptReleasePassing
} from "./thresholds";

export interface PromptEvalCaseResult {
  caseId: string;
  jsonStructurePassed: boolean;
  requiredFieldsPassed: boolean;
  exportabilityPassed: boolean;
  markdownFreePassed: boolean;
  wordCountPassed: boolean;
}

export interface PromptEvalSummary {
  caseCount: number;
  metrics: PromptReleaseThresholds;
}

export interface PromptReleaseDecision {
  allowed: boolean;
  mode: "standard" | "risk_override" | "blocked";
  blockedReasons: readonly string[];
}

export interface PromptReleaseDecisionInput {
  summary: PromptEvalSummary;
  requestedByRole: RoleCode;
  riskAcceptedReason?: string;
  thresholds?: PromptReleaseThresholds;
}

type MetricKey = keyof PromptReleaseThresholds;

const METRIC_REASON_LABELS: Record<MetricKey, string> = {
  jsonStructurePassRate: "json_structure",
  requiredFieldPassRate: "required_fields",
  exportabilityPassRate: "exportability",
  markdownFreePassRate: "markdown_free",
  wordCountPassRate: "word_count"
};

function passRate(results: readonly PromptEvalCaseResult[], predicate: (item: PromptEvalCaseResult) => boolean): number {
  if (results.length === 0) {
    return 0;
  }
  return results.filter(predicate).length / results.length;
}

export function summarizePromptEvalResults(
  results: readonly PromptEvalCaseResult[]
): PromptEvalSummary {
  return {
    caseCount: results.length,
    metrics: {
      jsonStructurePassRate: passRate(results, (item) => item.jsonStructurePassed),
      requiredFieldPassRate: passRate(results, (item) => item.requiredFieldsPassed),
      exportabilityPassRate: passRate(results, (item) => item.exportabilityPassed),
      markdownFreePassRate: passRate(results, (item) => item.markdownFreePassed),
      wordCountPassRate: passRate(results, (item) => item.wordCountPassed)
    }
  };
}

function blockedReasons(
  metrics: PromptReleaseThresholds,
  thresholds: PromptReleaseThresholds
): readonly string[] {
  return (Object.keys(METRIC_REASON_LABELS) as MetricKey[])
    .filter((key) => metrics[key] < thresholds[key])
    .map((key) => METRIC_REASON_LABELS[key]);
}

function hasRiskOverride(input: PromptReleaseDecisionInput): boolean {
  return (
    input.requestedByRole === "academic_director" &&
    (input.riskAcceptedReason?.trim().length ?? 0) >= 12
  );
}

export function decidePromptRelease(input: PromptReleaseDecisionInput): PromptReleaseDecision {
  const thresholds = input.thresholds ?? DEFAULT_PROMPT_RELEASE_THRESHOLDS;
  const reasons = blockedReasons(input.summary.metrics, thresholds);

  if (input.summary.caseCount === 0) {
    return {
      allowed: false,
      mode: "blocked",
      blockedReasons: ["empty_eval_dataset"]
    };
  }

  if (isPromptReleasePassing(input.summary.metrics, thresholds)) {
    return {
      allowed: true,
      mode: "standard",
      blockedReasons: []
    };
  }

  if (hasRiskOverride(input)) {
    return {
      allowed: true,
      mode: "risk_override",
      blockedReasons: reasons
    };
  }

  return {
    allowed: false,
    mode: "blocked",
    blockedReasons: reasons
  };
}
