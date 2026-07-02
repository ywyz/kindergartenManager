import { describe, expect, it } from "vitest";

import { InMemoryWorkflowJobQueue, WorkflowJobLockError } from "./job-queue";
import { CLAIM_WORKFLOW_JOB_TRANSACTION_SQL, assertMysqlJobSqlContract } from "./job-sql";

const now = new Date("2026-07-02T12:00:00.000Z");

describe("MySQL workflow job SQL contract", () => {
  it("uses row locking with SKIP LOCKED for atomic worker claims", () => {
    expect(() => assertMysqlJobSqlContract()).not.toThrow();
    expect(CLAIM_WORKFLOW_JOB_TRANSACTION_SQL.join("\n")).toContain(
      "FOR UPDATE SKIP LOCKED"
    );
  });
});

describe("InMemoryWorkflowJobQueue", () => {
  it("allows only one worker to claim a single queued job under concurrency", async () => {
    const queue = new InMemoryWorkflowJobQueue();
    await queue.enqueue({
      workflowSlug: "daily-plan",
      jobType: "ai-generate",
      payload: { recordId: 1 }
    }, now);

    const claims = await Promise.all([
      queue.claimNext("worker-a", now),
      queue.claimNext("worker-b", now),
      queue.claimNext("worker-c", now)
    ]);

    const claimed = claims.filter((job) => job !== null);
    expect(claimed).toHaveLength(1);
    expect(claimed[0]?.lockedBy).toBe("worker-a");
    expect(claims.filter((job) => job === null)).toHaveLength(2);
  });

  it("requeues failed jobs until maxAttempts is reached", async () => {
    const queue = new InMemoryWorkflowJobQueue();
    const job = await queue.enqueue(
      {
        workflowSlug: "game-observation",
        jobType: "vision-ai",
        payload: { recordId: 2 },
        maxAttempts: 2
      },
      now
    );

    const firstClaim = await queue.claimNext("worker-a", now);
    expect(firstClaim?.attempts).toBe(1);

    const failedOnce = await queue.markFailed(
      job.id,
      "worker-a",
      "temporary model error",
      { retryDelayMs: 5000 },
      now
    );
    expect(failedOnce.status).toBe("queued");
    expect(failedOnce.runAt.toISOString()).toBe("2026-07-02T12:00:05.000Z");

    const tooEarly = await queue.claimNext("worker-b", new Date("2026-07-02T12:00:04.000Z"));
    expect(tooEarly).toBeNull();

    const secondClaim = await queue.claimNext(
      "worker-b",
      new Date("2026-07-02T12:00:05.000Z")
    );
    expect(secondClaim?.attempts).toBe(2);

    const failedTwice = await queue.markFailed(
      job.id,
      "worker-b",
      "model still unavailable",
      { retryDelayMs: 5000 },
      new Date("2026-07-02T12:00:05.000Z")
    );
    expect(failedTwice.status).toBe("failed");
    expect(failedTwice.finishedAt?.toISOString()).toBe("2026-07-02T12:00:05.000Z");
  });

  it("only allows the lock holder to write terminal state", async () => {
    const queue = new InMemoryWorkflowJobQueue();
    const job = await queue.enqueue({
      workflowSlug: "course-review",
      jobType: "word-export",
      payload: { recordId: 3 }
    }, now);

    await queue.claimNext("worker-a", now);

    await expect(
      queue.markSucceeded(job.id, "worker-b", { exportId: 9 }, now)
    ).rejects.toBeInstanceOf(WorkflowJobLockError);

    const succeeded = await queue.markSucceeded(job.id, "worker-a", { exportId: 9 }, now);
    expect(succeeded.status).toBe("succeeded");
    expect(succeeded.result).toEqual({ exportId: 9 });
  });
});
