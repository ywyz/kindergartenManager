import { describe, expect, it } from "vitest";

import { createWorkerDispatcher } from "./dispatcher";
import type { WorkflowJob } from "@kindergarten/database";

function createJob(jobType: string): WorkflowJob {
  return {
    id: 1,
    workflowSlug: "daily-plan",
    jobType,
    status: "running",
    payload: { recordId: 7 },
    attempts: 1,
    maxAttempts: 3,
    runAt: new Date("2026-07-02T12:00:00.000Z"),
    lockedBy: "worker-a",
    lockedAt: new Date("2026-07-02T12:00:00.000Z"),
    createdAt: new Date("2026-07-02T12:00:00.000Z"),
    updatedAt: new Date("2026-07-02T12:00:00.000Z")
  };
}

describe("createWorkerDispatcher", () => {
  it("dispatches registered job types to their handlers", async () => {
    const dispatch = createWorkerDispatcher({
      "ai-generate": (job) => ({
        workflowSlug: job.workflowSlug,
        recordId: (job.payload as { recordId: number }).recordId
      })
    });

    await expect(dispatch(createJob("ai-generate"))).resolves.toEqual({
      jobId: 1,
      outcome: "succeeded",
      result: {
        workflowSlug: "daily-plan",
        recordId: 7
      }
    });
  });

  it("returns non-retryable failure for unknown job types", async () => {
    const dispatch = createWorkerDispatcher({});

    await expect(dispatch(createJob("unknown"))).resolves.toEqual({
      jobId: 1,
      outcome: "failed",
      error: "No worker handler registered for job type: unknown",
      retryable: false
    });
  });

  it("returns retryable failure when handlers throw", async () => {
    const dispatch = createWorkerDispatcher({
      "word-export": () => {
        throw new Error("template missing");
      }
    });

    await expect(dispatch(createJob("word-export"))).resolves.toEqual({
      jobId: 1,
      outcome: "failed",
      error: "template missing",
      retryable: true
    });
  });
});
