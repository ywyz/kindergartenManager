import { randomUUID } from "node:crypto";

const CATEGORY_PATTERN = /^[a-z][a-z0-9-]*$/;
const EXTENSION_PATTERN = /^[a-z0-9]{1,12}$/;
const OBJECT_ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/;

export type StorageCategory = "uploads" | "exports" | "templates" | "backups";

export interface CreateObjectKeyInput {
  tenantId: number;
  category: StorageCategory;
  extension: string;
  now?: Date;
  objectId?: string;
}

export function normalizeExtension(extension: string): string {
  const normalized = extension.trim().toLowerCase().replace(/^\./, "");
  if (!EXTENSION_PATTERN.test(normalized)) {
    throw new Error(`Unsupported file extension: ${extension}`);
  }
  return normalized;
}

export function createObjectKey(input: CreateObjectKeyInput): string {
  if (!Number.isInteger(input.tenantId) || input.tenantId <= 0) {
    throw new Error("tenantId must be a positive integer");
  }
  if (!CATEGORY_PATTERN.test(input.category)) {
    throw new Error(`Invalid storage category: ${input.category}`);
  }

  const now = input.now ?? new Date();
  const year = String(now.getUTCFullYear());
  const month = String(now.getUTCMonth() + 1).padStart(2, "0");
  const objectId = input.objectId ?? randomUUID();
  const extension = normalizeExtension(input.extension);

  if (!OBJECT_ID_PATTERN.test(objectId)) {
    throw new Error(`Invalid object id: ${objectId}`);
  }

  return `tenant-${input.tenantId}/${input.category}/${year}/${month}/${objectId}.${extension}`;
}
