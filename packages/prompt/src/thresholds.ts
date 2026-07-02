export interface PromptReleaseThresholds {
  jsonStructurePassRate: number;
  requiredFieldPassRate: number;
  exportabilityPassRate: number;
}

export const DEFAULT_PROMPT_RELEASE_THRESHOLDS: PromptReleaseThresholds = {
  jsonStructurePassRate: 1,
  requiredFieldPassRate: 1,
  exportabilityPassRate: 1
};

export function isPromptReleasePassing(score: PromptReleaseThresholds): boolean {
  return (
    score.jsonStructurePassRate >= DEFAULT_PROMPT_RELEASE_THRESHOLDS.jsonStructurePassRate &&
    score.requiredFieldPassRate >= DEFAULT_PROMPT_RELEASE_THRESHOLDS.requiredFieldPassRate &&
    score.exportabilityPassRate >= DEFAULT_PROMPT_RELEASE_THRESHOLDS.exportabilityPassRate
  );
}
