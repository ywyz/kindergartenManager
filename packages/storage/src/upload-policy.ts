import { createHash } from "node:crypto";

import { createObjectKey } from "./object-key";

export type UploadAssetKind = "image" | "word-template" | "excel";

export interface UploadCandidate {
  tenantId: number;
  assetKind: UploadAssetKind;
  originalFilename: string;
  mimeType: string;
  data: Uint8Array;
  now?: Date;
  objectId?: string;
}

export interface StoredObjectMetadata {
  tenantId: number;
  assetKind: UploadAssetKind;
  key: string;
  bytes: number;
  sha256: string;
  mimeType: string;
  extension: string;
  originalFilename: string;
}

interface UploadPolicy {
  extensions: readonly string[];
  mimeTypes: readonly string[];
  maxBytes: number;
  signature: (data: Uint8Array) => boolean;
}

const tenMb = 10 * 1024 * 1024;
const twentyMb = 20 * 1024 * 1024;

const UPLOAD_POLICIES: Record<UploadAssetKind, UploadPolicy> = {
  image: {
    extensions: ["png", "jpg", "jpeg"],
    mimeTypes: ["image/png", "image/jpeg"],
    maxBytes: tenMb,
    signature: (data) => isPng(data) || isJpeg(data)
  },
  "word-template": {
    extensions: ["docx"],
    mimeTypes: [
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    maxBytes: twentyMb,
    signature: isZip
  },
  excel: {
    extensions: ["xlsx"],
    mimeTypes: [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ],
    maxBytes: twentyMb,
    signature: isZip
  }
};

function extensionFromFilename(filename: string): string {
  const baseName = filename.split(/[\\/]/).pop() ?? "";
  const dotIndex = baseName.lastIndexOf(".");
  if (dotIndex <= 0 || dotIndex === baseName.length - 1) {
    throw new Error(`Missing file extension: ${filename}`);
  }
  return baseName.slice(dotIndex + 1).toLowerCase();
}

function isPng(data: Uint8Array): boolean {
  return (
    data.length >= 8 &&
    data[0] === 0x89 &&
    data[1] === 0x50 &&
    data[2] === 0x4e &&
    data[3] === 0x47 &&
    data[4] === 0x0d &&
    data[5] === 0x0a &&
    data[6] === 0x1a &&
    data[7] === 0x0a
  );
}

function isJpeg(data: Uint8Array): boolean {
  return data.length >= 3 && data[0] === 0xff && data[1] === 0xd8 && data[2] === 0xff;
}

function isZip(data: Uint8Array): boolean {
  return data.length >= 4 && data[0] === 0x50 && data[1] === 0x4b && data[2] === 0x03 && data[3] === 0x04;
}

function sha256Hex(data: Uint8Array): string {
  return createHash("sha256").update(data).digest("hex");
}

function expectedImageExtension(mimeType: string, data: Uint8Array): "png" | "jpg" {
  if (mimeType === "image/png" && isPng(data)) {
    return "png";
  }
  if (mimeType === "image/jpeg" && isJpeg(data)) {
    return "jpg";
  }
  throw new Error("Image MIME type does not match file signature");
}

function canonicalExtension(candidate: UploadCandidate, extension: string): string {
  if (candidate.assetKind === "image") {
    const expected = expectedImageExtension(candidate.mimeType, candidate.data);
    if (extension === "jpeg") {
      extension = "jpg";
    }
    if (extension !== expected) {
      throw new Error(`File extension .${extension} does not match ${candidate.mimeType}`);
    }
    return expected;
  }
  return extension;
}

export function createStoredObjectMetadata(candidate: UploadCandidate): StoredObjectMetadata {
  const policy = UPLOAD_POLICIES[candidate.assetKind];
  if (candidate.data.byteLength > policy.maxBytes) {
    throw new Error(
      `Uploaded ${candidate.assetKind} exceeds ${policy.maxBytes} byte limit`
    );
  }

  const extension = canonicalExtension(candidate, extensionFromFilename(candidate.originalFilename));

  if (!policy.extensions.includes(extension)) {
    throw new Error(`Unsupported ${candidate.assetKind} extension: ${extension}`);
  }
  if (!policy.mimeTypes.includes(candidate.mimeType)) {
    throw new Error(`Unsupported ${candidate.assetKind} MIME type: ${candidate.mimeType}`);
  }
  if (!policy.signature(candidate.data)) {
    throw new Error(`${candidate.assetKind} file signature does not match policy`);
  }
  const keyInput = {
    tenantId: candidate.tenantId,
    category: candidate.assetKind === "word-template" ? "templates" : "uploads",
    extension
  } as const;
  const key = createObjectKey({
    ...keyInput,
    ...(candidate.objectId ? { objectId: candidate.objectId } : {}),
    ...(candidate.now ? { now: candidate.now } : {})
  });

  return {
    tenantId: candidate.tenantId,
    assetKind: candidate.assetKind,
    key,
    bytes: candidate.data.byteLength,
    sha256: sha256Hex(candidate.data),
    mimeType: candidate.mimeType,
    extension,
    originalFilename: candidate.originalFilename
  };
}
