import { randomUUID } from "node:crypto";

import { z } from "zod";

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | readonly JsonValue[]
  | { readonly [key: string]: JsonValue };

export const AuditOutcomeSchema = z.enum(["success", "denied", "failed"]);
export const AuditRiskLevelSchema = z.enum(["low", "medium", "high", "critical"]);

export type AuditOutcome = z.infer<typeof AuditOutcomeSchema>;
export type AuditRiskLevel = z.infer<typeof AuditRiskLevelSchema>;

export interface AuditTarget {
  type: string;
  id?: string;
}

export interface CreateAuditEventInput {
  eventId?: string;
  tenantId: number;
  actorUserId?: number;
  action: string;
  target: AuditTarget;
  outcome: AuditOutcome;
  riskLevel: AuditRiskLevel;
  reason?: string;
  metadata?: JsonValue;
  occurredAt?: Date;
}

export interface AuditEvent {
  eventId: string;
  tenantId: number;
  actorUserId: number | null;
  action: string;
  target: AuditTarget;
  outcome: AuditOutcome;
  riskLevel: AuditRiskLevel;
  reason?: string;
  metadata: JsonValue;
  occurredAt: string;
}

const ACTION_PATTERN = /^[a-z][a-z0-9_:.-]*$/;
const SENSITIVE_KEY_PATTERN = /^(api[_-]?key|password|secret|token|authorization|cookie|set-cookie)$/i;
const SECRET_VALUE_PATTERN = /sk-[A-Za-z0-9_-]{8,}/g;

function assertPositiveInteger(value: number, field: string): void {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${field} must be a positive integer`);
  }
}

function isRecord(value: JsonValue): value is { readonly [key: string]: JsonValue } {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function redactString(value: string): string {
  return value.replace(SECRET_VALUE_PATTERN, "[REDACTED_SECRET]");
}

export function sanitizeAuditMetadata(value: JsonValue, key = ""): JsonValue {
  if (SENSITIVE_KEY_PATTERN.test(key)) {
    return "[REDACTED_SECRET]";
  }
  if (typeof value === "string") {
    return redactString(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeAuditMetadata(item));
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([entryKey, entryValue]) => [
        entryKey,
        sanitizeAuditMetadata(entryValue, entryKey)
      ])
    );
  }
  return value;
}

export function createAuditEvent(input: CreateAuditEventInput): AuditEvent {
  assertPositiveInteger(input.tenantId, "tenantId");
  if (input.actorUserId !== undefined) {
    assertPositiveInteger(input.actorUserId, "actorUserId");
  }
  if (!ACTION_PATTERN.test(input.action)) {
    throw new Error(`Invalid audit action: ${input.action}`);
  }
  if (!input.target.type) {
    throw new Error("target.type is required");
  }
  AuditOutcomeSchema.parse(input.outcome);
  AuditRiskLevelSchema.parse(input.riskLevel);
  if ((input.outcome === "denied" || input.outcome === "failed") && !input.reason) {
    throw new Error("reason is required for denied and failed audit events");
  }

  return {
    eventId: input.eventId ?? randomUUID(),
    tenantId: input.tenantId,
    actorUserId: input.actorUserId ?? null,
    action: input.action,
    target: input.target,
    outcome: input.outcome,
    riskLevel: input.riskLevel,
    ...(input.reason ? { reason: input.reason } : {}),
    metadata: sanitizeAuditMetadata(input.metadata ?? {}),
    occurredAt: (input.occurredAt ?? new Date()).toISOString()
  };
}
