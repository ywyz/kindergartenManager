import { z } from "zod";

import { WorkflowActionSchema } from "@kindergarten/contracts";

export const WorkflowDefinitionSchema = z.object({
  slug: z.string().regex(/^[a-z][a-z0-9-]*$/),
  name: z.string().min(1),
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  actions: z.array(WorkflowActionSchema).min(1)
});

export type WorkflowDefinition = z.infer<typeof WorkflowDefinitionSchema>;
