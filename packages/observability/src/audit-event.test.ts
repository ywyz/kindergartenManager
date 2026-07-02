import { describe, expect, it } from "vitest";

import { createAuditEvent, sanitizeAuditMetadata } from "./audit-event";

describe("createAuditEvent", () => {
  it("creates stable structured audit events", () => {
    const event = createAuditEvent({
      eventId: "evt-001",
      tenantId: 1,
      actorUserId: 7,
      action: "prompt_release",
      target: {
        type: "prompt_template",
        id: "template-1"
      },
      outcome: "success",
      riskLevel: "high",
      metadata: {
        workflowSlug: "daily-plan"
      },
      occurredAt: new Date("2026-07-02T12:00:00.000Z")
    });

    expect(event).toEqual({
      eventId: "evt-001",
      tenantId: 1,
      actorUserId: 7,
      action: "prompt_release",
      target: {
        type: "prompt_template",
        id: "template-1"
      },
      outcome: "success",
      riskLevel: "high",
      metadata: {
        workflowSlug: "daily-plan"
      },
      occurredAt: "2026-07-02T12:00:00.000Z"
    });
  });

  it("requires a reason for denied and failed events", () => {
    expect(() =>
      createAuditEvent({
        tenantId: 1,
        action: "backup_restore",
        target: { type: "backup" },
        outcome: "denied",
        riskLevel: "critical"
      })
    ).toThrow("reason is required");
  });

  it("rejects invalid actions", () => {
    expect(() =>
      createAuditEvent({
        tenantId: 1,
        action: "Backup Restore",
        target: { type: "backup" },
        outcome: "success",
        riskLevel: "critical"
      })
    ).toThrow("Invalid audit action");
  });
});

describe("sanitizeAuditMetadata", () => {
  it("recursively redacts sensitive keys and sk-like values", () => {
    const metadata = sanitizeAuditMetadata({
      apiKey: "sk-live-secret-value",
      nested: {
        password: "plain-password",
        request: {
          authorization: "Bearer sk-live-secret-value",
          message: "model failed for sk-live-secret-value"
        }
      },
      headers: [
        {
          cookie: "session=abc"
        }
      ],
      safe: "visible"
    });

    expect(metadata).toEqual({
      apiKey: "[REDACTED_SECRET]",
      nested: {
        password: "[REDACTED_SECRET]",
        request: {
          authorization: "[REDACTED_SECRET]",
          message: "model failed for [REDACTED_SECRET]"
        }
      },
      headers: [
        {
          cookie: "[REDACTED_SECRET]"
        }
      ],
      safe: "visible"
    });
    expect(JSON.stringify(metadata)).not.toContain("sk-live-secret-value");
    expect(JSON.stringify(metadata)).not.toContain("plain-password");
  });
});
