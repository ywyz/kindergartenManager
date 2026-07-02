import { describe, expect, it } from "vitest";

import { BackupTargetAuthError } from "./target";
import { writeVerifiedBackupObject } from "./verified-transfer";
import { createWebDavBackupTarget } from "./webdav-target";

function createResponse(body: BodyInit | null, init: ResponseInit): Response {
  return new Response(body, init);
}

describe("createWebDavBackupTarget", () => {
  it("uploads and downloads with encoded paths and basic auth", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const data = new TextEncoder().encode("backup-data");
    const fetchImpl = async (url: string | URL | Request, init?: RequestInit) => {
      calls.push({ url: String(url), init: init ?? {} });
      if (init?.method === "PUT") {
        return createResponse(null, { status: 201 });
      }
      return createResponse(data, { status: 200 });
    };

    const target = createWebDavBackupTarget({
      baseUrl: "https://dav.example.com/backups/",
      username: "teacher",
      password: "secret",
      fetchImpl
    });

    const manifest = await writeVerifiedBackupObject(target, {
      path: "班级 A/2026-07-02.sql.gz",
      data
    });

    expect(manifest.bytes).toBe(11);
    expect(calls.map((call) => call.url)).toEqual([
      "https://dav.example.com/backups/%E7%8F%AD%E7%BA%A7%20A/2026-07-02.sql.gz",
      "https://dav.example.com/backups/%E7%8F%AD%E7%BA%A7%20A/2026-07-02.sql.gz"
    ]);
    expect(calls[0]?.init.method).toBe("PUT");
    expect(calls[1]?.init.method).toBe("GET");
    expect((calls[0]?.init.headers as Headers).get("Authorization")).toBe(
      "Basic dGVhY2hlcjpzZWNyZXQ="
    );
  });

  it("maps WebDAV 401 and 403 responses to auth errors", async () => {
    const target = createWebDavBackupTarget({
      baseUrl: "https://dav.example.com/backups",
      bearerToken: "expired",
      fetchImpl: async () => createResponse(null, { status: 401, statusText: "Unauthorized" })
    });

    await expect(
      target.putObject({
        path: "2026-07-02/main.sql.gz",
        data: new Uint8Array()
      })
    ).rejects.toBeInstanceOf(BackupTargetAuthError);
  });
});
