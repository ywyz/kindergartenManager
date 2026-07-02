export type WorkflowJobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";

export interface WorkflowJob {
  id: number;
  workflowSlug: string;
  jobType: string;
  status: WorkflowJobStatus;
  payload: unknown;
  result?: unknown;
  attempts: number;
  maxAttempts: number;
  runAt: Date;
  lockedBy?: string;
  lockedAt?: Date;
  lastError?: string;
  createdAt: Date;
  updatedAt: Date;
  finishedAt?: Date;
}

export interface EnqueueWorkflowJobInput {
  workflowSlug: string;
  jobType: string;
  payload: unknown;
  maxAttempts?: number;
  runAt?: Date;
}

export class WorkflowJobLockError extends Error {
  constructor(jobId: number, workerId: string) {
    super(`Worker ${workerId} does not hold lock for job ${jobId}`);
    this.name = "WorkflowJobLockError";
  }
}

function copyDate(value: Date | undefined): Date | undefined {
  return value ? new Date(value.getTime()) : undefined;
}

function copyRequiredDate(value: Date): Date {
  return new Date(value.getTime());
}

function copyJob(job: WorkflowJob): WorkflowJob {
  const copy: WorkflowJob = {
    ...job,
    runAt: copyRequiredDate(job.runAt),
    createdAt: copyRequiredDate(job.createdAt),
    updatedAt: copyRequiredDate(job.updatedAt)
  };
  const lockedAt = copyDate(job.lockedAt);
  if (lockedAt) {
    copy.lockedAt = lockedAt;
  }
  const finishedAt = copyDate(job.finishedAt);
  if (finishedAt) {
    copy.finishedAt = finishedAt;
  }
  return copy;
}

function isClaimable(job: WorkflowJob, now: Date): boolean {
  return (
    job.status === "queued" &&
    job.runAt.getTime() <= now.getTime() &&
    job.attempts < job.maxAttempts
  );
}

export class InMemoryWorkflowJobQueue {
  private readonly jobs = new Map<number, WorkflowJob>();
  private nextId = 1;
  private lockTail: Promise<void> = Promise.resolve();

  async enqueue(input: EnqueueWorkflowJobInput, now = new Date()): Promise<WorkflowJob> {
    return this.withLock(() => {
      const job: WorkflowJob = {
        id: this.nextId,
        workflowSlug: input.workflowSlug,
        jobType: input.jobType,
        status: "queued",
        payload: input.payload,
        attempts: 0,
        maxAttempts: input.maxAttempts ?? 3,
        runAt: copyDate(input.runAt) ?? copyDate(now) ?? new Date(),
        createdAt: copyDate(now) ?? new Date(),
        updatedAt: copyDate(now) ?? new Date()
      };
      this.nextId += 1;
      this.jobs.set(job.id, job);
      return copyJob(job);
    });
  }

  async claimNext(workerId: string, now = new Date()): Promise<WorkflowJob | null> {
    return this.withLock(() => {
      const selected = [...this.jobs.values()]
        .filter((job) => isClaimable(job, now))
        .sort((left, right) => {
          const runAtDiff = left.runAt.getTime() - right.runAt.getTime();
          return runAtDiff === 0 ? left.id - right.id : runAtDiff;
        })[0];

      if (!selected) {
        return null;
      }

      selected.status = "running";
      selected.attempts += 1;
      selected.lockedBy = workerId;
      selected.lockedAt = copyRequiredDate(now);
      selected.updatedAt = copyRequiredDate(now);
      return copyJob(selected);
    });
  }

  async markSucceeded(
    jobId: number,
    workerId: string,
    result: unknown,
    now = new Date()
  ): Promise<WorkflowJob> {
    return this.withLock(() => {
      const job = this.requireLockedJob(jobId, workerId);
      job.status = "succeeded";
      job.result = result;
      job.updatedAt = copyRequiredDate(now);
      job.finishedAt = copyRequiredDate(now);
      return copyJob(job);
    });
  }

  async markFailed(
    jobId: number,
    workerId: string,
    error: string,
    options: { retryDelayMs: number },
    now = new Date()
  ): Promise<WorkflowJob> {
    return this.withLock(() => {
      const job = this.requireLockedJob(jobId, workerId);
      job.lastError = error;
      delete job.lockedBy;
      delete job.lockedAt;
      job.updatedAt = copyRequiredDate(now);

      if (job.attempts >= job.maxAttempts) {
        job.status = "failed";
        job.finishedAt = copyRequiredDate(now);
      } else {
        job.status = "queued";
        job.runAt = new Date(now.getTime() + options.retryDelayMs);
      }

      return copyJob(job);
    });
  }

  async get(jobId: number): Promise<WorkflowJob | null> {
    return this.withLock(() => {
      const job = this.jobs.get(jobId);
      return job ? copyJob(job) : null;
    });
  }

  private requireLockedJob(jobId: number, workerId: string): WorkflowJob {
    const job = this.jobs.get(jobId);
    if (!job || job.status !== "running" || job.lockedBy !== workerId) {
      throw new WorkflowJobLockError(jobId, workerId);
    }
    return job;
  }

  private async withLock<T>(operation: () => T | Promise<T>): Promise<T> {
    const previous = this.lockTail;
    let releaseLock: () => void = () => undefined;
    this.lockTail = new Promise<void>((resolve) => {
      releaseLock = resolve;
    });

    await previous;
    try {
      return await operation();
    } finally {
      releaseLock();
    }
  }
}
