import { describe, expect, it } from "vitest";

import type { BackupObjectTarget } from "./target";
import { BackupIntegrityError } from "./target";
import { readVerifiedBackupObject, writeVerifiedBackupObject } from "./verified-transfer";

class MemoryBackupTarget implements BackupObjectTarget {
  readonly kind = "s3";
  private readonly objects = new Map<string, Uint8Array>();

  async putObject(object: { path: string; data: Uint8Array }): Promise<void> {
    this.objects.set(object.path, object.data);
  }

  async getObject(path: string): Promise<Uint8Array> {
    const data = this.objects.get(path);
    if (!data) {
      throw new Error(`Missing object ${path}`);
    }
    return data;
  }
}

describe("verified backup transfer", () => {
  it("writes, reads back, and returns a stable manifest", async () => {
    const target = new MemoryBackupTarget();
    const data = new TextEncoder().encode("kindergarten-backup");

    const manifest = await writeVerifiedBackupObject(target, {
      path: "2026-07-02/main.sql.gz",
      data
    });

    expect(manifest).toEqual({
      path: "2026-07-02/main.sql.gz",
      bytes: 19,
      sha256: "23d84c3036007fe12b70d081bdd98db3bf10115b1ac8efb46d3252122a633c5f"
    });
    await expect(readVerifiedBackupObject(target, manifest)).resolves.toEqual(data);
  });

  it("fails when downloaded bytes do not match the manifest", async () => {
    const target = new MemoryBackupTarget();
    const data = new TextEncoder().encode("original");
    const manifest = await writeVerifiedBackupObject(target, {
      path: "2026-07-02/main.sql.gz",
      data
    });

    await target.putObject({
      path: manifest.path,
      data: new TextEncoder().encode("tampered")
    });

    await expect(readVerifiedBackupObject(target, manifest)).rejects.toBeInstanceOf(
      BackupIntegrityError
    );
  });

  it("rejects unsafe object paths", async () => {
    const target = new MemoryBackupTarget();

    await expect(
      writeVerifiedBackupObject(target, {
        path: "../main.sql.gz",
        data: new Uint8Array()
      })
    ).rejects.toThrow("Invalid backup object path");
  });
});
