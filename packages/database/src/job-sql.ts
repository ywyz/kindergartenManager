export const WORKFLOW_JOB_TABLE_SQL = `
CREATE TABLE workflow_job (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  workflow_slug VARCHAR(128) NOT NULL,
  job_type VARCHAR(128) NOT NULL,
  status ENUM('queued', 'running', 'succeeded', 'failed', 'canceled') NOT NULL DEFAULT 'queued',
  payload JSON NOT NULL,
  result JSON NULL,
  attempts INT UNSIGNED NOT NULL DEFAULT 0,
  max_attempts INT UNSIGNED NOT NULL DEFAULT 3,
  run_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  locked_by VARCHAR(128) NULL,
  locked_at DATETIME(3) NULL,
  last_error TEXT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  finished_at DATETIME(3) NULL,
  PRIMARY KEY (id),
  KEY idx_workflow_job_claim (status, run_at, attempts, id),
  KEY idx_workflow_job_worker (locked_by, locked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
`.trim();

export const CLAIM_WORKFLOW_JOB_TRANSACTION_SQL = [
  "START TRANSACTION;",
  `
SELECT id
FROM workflow_job
WHERE status = 'queued'
  AND run_at <= NOW(3)
  AND attempts < max_attempts
ORDER BY run_at ASC, id ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
  `.trim(),
  `
UPDATE workflow_job
SET status = 'running',
    attempts = attempts + 1,
    locked_by = ?,
    locked_at = NOW(3),
    updated_at = NOW(3)
WHERE id = ?;
  `.trim(),
  "SELECT * FROM workflow_job WHERE id = ?;",
  "COMMIT;"
] as const;

export function assertMysqlJobSqlContract(): void {
  const claimSql = CLAIM_WORKFLOW_JOB_TRANSACTION_SQL.join("\n");
  if (!claimSql.includes("FOR UPDATE SKIP LOCKED")) {
    throw new Error("Job claim SQL must use FOR UPDATE SKIP LOCKED");
  }
  if (!WORKFLOW_JOB_TABLE_SQL.includes("ENGINE=InnoDB")) {
    throw new Error("workflow_job table must use InnoDB");
  }
}
