import { describe, expect, it } from "vitest";

import { createBackupManifest, sha256Hex } from "./manifest";

describe("backup manifest", () => {
  it("builds hash-verified S3/WebDAV manifests", () => {
    const hash = sha256Hex("dev4-backup");
    const manifest = createBackupManifest({
      backupId: "backup-20260702",
      createdAt: "2026-07-02T00:00:00.000Z",
      target: "s3",
      files: [{ path: "mysql/full.sql.gz", bytes: 12, sha256: hash }]
    });

    expect(manifest.files[0]?.sha256).toBe(hash);
  });

  it("rejects malformed file hashes", () => {
    expect(() =>
      createBackupManifest({
        backupId: "backup-20260702",
        createdAt: "2026-07-02T00:00:00.000Z",
        target: "webdav",
        files: [{ path: "mysql/full.sql.gz", bytes: 12, sha256: "not-a-hash" }]
      })
    ).toThrow("Invalid sha256");
  });
});
