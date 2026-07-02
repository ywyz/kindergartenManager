export interface PromptReleaseThresholds {
  jsonStructurePassRate: number;
  requiredFieldPassRate: number;
  exportabilityPassRate: number;
  markdownFreePassRate: number;
  wordCountPassRate: number;
}

export const DEFAULT_PROMPT_RELEASE_THRESHOLDS: PromptReleaseThresholds = {
  jsonStructurePassRate: 1,
  requiredFieldPassRate: 1,
  exportabilityPassRate: 1,
  markdownFreePassRate: 1,
  wordCountPassRate: 1
};

export function isPromptReleasePassing(
  score: PromptReleaseThresholds,
  threshold: PromptReleaseThresholds = DEFAULT_PROMPT_RELEASE_THRESHOLDS
): boolean {
  return (
    score.jsonStructurePassRate >= threshold.jsonStructurePassRate &&
    score.requiredFieldPassRate >= threshold.requiredFieldPassRate &&
    score.exportabilityPassRate >= threshold.exportabilityPassRate &&
    score.markdownFreePassRate >= threshold.markdownFreePassRate &&
    score.wordCountPassRate >= threshold.wordCountPassRate
  );
}
