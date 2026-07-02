import type { WorkflowJob } from "@kindergarten/database";

export interface WorkerJobSuccess {
  jobId: number;
  outcome: "succeeded";
  result: unknown;
}

export interface WorkerJobFailure {
  jobId: number;
  outcome: "failed";
  error: string;
  retryable: boolean;
}

export type WorkerJobResult = WorkerJobSuccess | WorkerJobFailure;

export type WorkerJobHandler = (job: WorkflowJob) => Promise<unknown> | unknown;

export type WorkerHandlerRegistry = Readonly<Record<string, WorkerJobHandler>>;

export function createWorkerDispatcher(handlers: WorkerHandlerRegistry) {
  return async function dispatchWorkflowJob(job: WorkflowJob): Promise<WorkerJobResult> {
    const handler = handlers[job.jobType];
    if (!handler) {
      return {
        jobId: job.id,
        outcome: "failed",
        error: `No worker handler registered for job type: ${job.jobType}`,
        retryable: false
      };
    }

    try {
      return {
        jobId: job.id,
        outcome: "succeeded",
        result: await handler(job)
      };
    } catch (error) {
      return {
        jobId: job.id,
        outcome: "failed",
        error: error instanceof Error ? error.message : "Unknown worker error",
        retryable: true
      };
    }
  };
}
