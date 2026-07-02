import type { BackupTargetKind } from "./manifest";

export interface BackupObject {
  path: string;
  data: Uint8Array;
}

export interface BackupObjectTarget {
  kind: BackupTargetKind;
  putObject(object: BackupObject): Promise<void>;
  getObject(path: string): Promise<Uint8Array>;
}

export class BackupTargetAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BackupTargetAuthError";
  }
}

export class BackupTargetUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BackupTargetUnavailableError";
  }
}

export class BackupIntegrityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BackupIntegrityError";
  }
}

export function assertSafeBackupPath(path: string): void {
  if (!path || path.startsWith("/") || path.includes("\\") || path.includes("..")) {
    throw new Error(`Invalid backup object path: ${path}`);
  }
}
