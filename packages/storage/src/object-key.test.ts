import { describe, expect, it } from "vitest";

import { createObjectKey, normalizeExtension } from "./object-key";

describe("object key generation", () => {
  it("creates deterministic tenant-scoped keys for managed objects", () => {
    const key = createObjectKey({
      tenantId: 1,
      category: "uploads",
      extension: ".JPG",
      objectId: "asset-001",
      now: new Date("2026-07-02T00:00:00Z")
    });

    expect(key).toBe("tenant-1/uploads/2026/07/asset-001.jpg");
  });

  it("rejects path-like extensions instead of accepting user filenames", () => {
    expect(() => normalizeExtension("../secret/docx")).toThrow("Unsupported file extension");
    expect(() => normalizeExtension("docx#bad")).toThrow("Unsupported file extension");
  });

  it("rejects path-like object ids", () => {
    expect(() =>
      createObjectKey({
        tenantId: 1,
        category: "uploads",
        extension: "jpg",
        objectId: "../avatar"
      })
    ).toThrow("Invalid object id");
  });
});
