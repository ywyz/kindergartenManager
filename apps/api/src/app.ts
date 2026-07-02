import Fastify, { type FastifyInstance } from "fastify";
import {
  CORE_WORKFLOW_ACTIONS,
  ROLE_CODES,
  ROLE_LABELS
} from "@kindergarten/contracts";

export function buildApp(): FastifyInstance {
  const app = Fastify({ logger: false });

  app.get("/health/live", async () => ({ status: "ok" }));
  app.get("/health/ready", async () => ({ status: "ok" }));
  app.get("/api/v1/contracts/roles", async (_request, reply) => {
    reply.header("Cache-Control", "no-store");
    return {
      roles: ROLE_CODES.map((code) => ({
        code,
        label: ROLE_LABELS[code]
      }))
    };
  });
  app.get("/api/v1/contracts/workflow-actions", async (_request, reply) => {
    reply.header("Cache-Control", "no-store");
    return {
      actions: CORE_WORKFLOW_ACTIONS
    };
  });

  return app;
}
