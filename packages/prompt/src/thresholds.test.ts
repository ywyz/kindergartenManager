import { describe, expect, it } from "vitest";

import { DEFAULT_PROMPT_RELEASE_THRESHOLDS, isPromptReleasePassing } from "./thresholds";

describe("prompt release thresholds", () => {
  it("defaults to all structural gates passing before release", () => {
    expect(DEFAULT_PROMPT_RELEASE_THRESHOLDS).toEqual({
      jsonStructurePassRate: 1,
      requiredFieldPassRate: 1,
      exportabilityPassRate: 1,
      markdownFreePassRate: 1,
      wordCountPassRate: 1
    });
  });

  it("blocks prompt release when any structural gate fails", () => {
    expect(
      isPromptReleasePassing({
        jsonStructurePassRate: 1,
        requiredFieldPassRate: 0.99,
        exportabilityPassRate: 1,
        markdownFreePassRate: 1,
        wordCountPassRate: 1
      })
    ).toBe(false);
  });
});
