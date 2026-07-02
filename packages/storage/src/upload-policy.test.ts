import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";

import { createStoredObjectMetadata } from "./upload-policy";

const png = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1]);
const jpeg = Uint8Array.from([0xff, 0xd8, 0xff, 0xdb, 1]);
const zip = Uint8Array.from([0x50, 0x4b, 0x03, 0x04, 1]);

describe("createStoredObjectMetadata", () => {
  it("creates metadata without using the original filename in the object key", () => {
    const metadata = createStoredObjectMetadata({
      tenantId: 7,
      assetKind: "image",
      originalFilename: "../../幼儿照片.png",
      mimeType: "image/png",
      data: png,
      objectId: "asset-001",
      now: new Date("2026-07-02T00:00:00Z")
    });

    expect(metadata).toEqual({
      tenantId: 7,
      assetKind: "image",
      key: "tenant-7/uploads/2026/07/asset-001.png",
      bytes: 9,
      sha256: createHash("sha256").update(png).digest("hex"),
      mimeType: "image/png",
      extension: "png",
      originalFilename: "../../幼儿照片.png"
    });
    expect(metadata.key).not.toContain("幼儿照片");
    expect(metadata.key).not.toContain("..");
  });

  it("canonicalizes jpeg extension to jpg when the MIME and signature match", () => {
    const metadata = createStoredObjectMetadata({
      tenantId: 1,
      assetKind: "image",
      originalFilename: "photo.jpeg",
      mimeType: "image/jpeg",
      data: jpeg,
      objectId: "asset-002",
      now: new Date("2026-07-02T00:00:00Z")
    });

    expect(metadata.extension).toBe("jpg");
    expect(metadata.key).toBe("tenant-1/uploads/2026/07/asset-002.jpg");
  });

  it("accepts docx and xlsx zip signatures with strict MIME types", () => {
    const docx = createStoredObjectMetadata({
      tenantId: 1,
      assetKind: "word-template",
      originalFilename: "template.docx",
      mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      data: zip,
      objectId: "template-001",
      now: new Date("2026-07-02T00:00:00Z")
    });
    const xlsx = createStoredObjectMetadata({
      tenantId: 1,
      assetKind: "excel",
      originalFilename: "import.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      data: zip,
      objectId: "excel-001",
      now: new Date("2026-07-02T00:00:00Z")
    });

    expect(docx.key).toBe("tenant-1/templates/2026/07/template-001.docx");
    expect(xlsx.key).toBe("tenant-1/uploads/2026/07/excel-001.xlsx");
  });

  it("rejects MIME, extension, signature, and size mismatches", () => {
    expect(() =>
      createStoredObjectMetadata({
        tenantId: 1,
        assetKind: "image",
        originalFilename: "photo.png",
        mimeType: "image/jpeg",
        data: png
      })
    ).toThrow("Image MIME type does not match file signature");

    expect(() =>
      createStoredObjectMetadata({
        tenantId: 1,
        assetKind: "word-template",
        originalFilename: "template.docx",
        mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data: png
      })
    ).toThrow("word-template file signature does not match policy");

    expect(() =>
      createStoredObjectMetadata({
        tenantId: 1,
        assetKind: "excel",
        originalFilename: "import.xls",
        mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        data: zip
      })
    ).toThrow("Unsupported excel extension");

    expect(() =>
      createStoredObjectMetadata({
        tenantId: 1,
        assetKind: "image",
        originalFilename: "large.png",
        mimeType: "image/png",
        data: new Uint8Array(10 * 1024 * 1024 + 1)
      })
    ).toThrow("exceeds");
  });
});
