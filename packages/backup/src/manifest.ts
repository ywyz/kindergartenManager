import { createHash } from "node:crypto";

export type BackupTargetKind = "s3" | "webdav";

export interface BackupFileManifest {
  path: string;
  bytes: number;
  sha256: string;
}

export interface BackupManifest {
  backupId: string;
  createdAt: string;
  target: BackupTargetKind;
  files: BackupFileManifest[];
}

export function sha256Hex(data: string | Uint8Array): string {
  return createHash("sha256").update(data).digest("hex");
}

export function createBackupManifest(input: BackupManifest): BackupManifest {
  if (!["s3", "webdav"].includes(input.target)) {
    throw new Error(`Unsupported backup target: ${input.target}`);
  }
  for (const file of input.files) {
    if (!/^[a-f0-9]{64}$/.test(file.sha256)) {
      throw new Error(`Invalid sha256 for ${file.path}`);
    }
    if (!Number.isInteger(file.bytes) || file.bytes < 0) {
      throw new Error(`Invalid byte count for ${file.path}`);
    }
  }
  return {
    ...input,
    files: [...input.files].sort((left, right) => left.path.localeCompare(right.path))
  };
}
