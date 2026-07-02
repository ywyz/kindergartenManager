import type { BackupFileManifest } from "./manifest";
import { sha256Hex } from "./manifest";
import {
  BackupIntegrityError,
  type BackupObject,
  type BackupObjectTarget,
  assertSafeBackupPath
} from "./target";

function byteLength(data: Uint8Array): number {
  return data.byteLength;
}

function verifyBytes(path: string, data: Uint8Array, expected: BackupFileManifest): void {
  const actualHash = sha256Hex(data);
  if (byteLength(data) !== expected.bytes || actualHash !== expected.sha256) {
    throw new BackupIntegrityError(
      `Backup integrity check failed for ${path}: expected ${expected.sha256}/${expected.bytes}, got ${actualHash}/${byteLength(data)}`
    );
  }
}

export async function writeVerifiedBackupObject(
  target: BackupObjectTarget,
  object: BackupObject
): Promise<BackupFileManifest> {
  assertSafeBackupPath(object.path);

  const manifest = {
    path: object.path,
    bytes: byteLength(object.data),
    sha256: sha256Hex(object.data)
  };

  await target.putObject(object);
  const downloaded = await target.getObject(object.path);
  verifyBytes(object.path, downloaded, manifest);

  return manifest;
}

export async function readVerifiedBackupObject(
  target: BackupObjectTarget,
  manifest: BackupFileManifest
): Promise<Uint8Array> {
  assertSafeBackupPath(manifest.path);

  const downloaded = await target.getObject(manifest.path);
  verifyBytes(manifest.path, downloaded, manifest);

  return downloaded;
}
