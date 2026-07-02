import { z } from "zod";

import { RoleCodeSchema, type RoleCode } from "./roles";

export const WorkflowScopeSchema = z.enum(["self", "grade", "tenant", "system"]);

export type WorkflowScope = z.infer<typeof WorkflowScopeSchema>;

export const WorkflowActionSchema = z.object({
  key: z.string().regex(/^[a-z][a-z0-9:_-]*$/),
  requiredRoles: z.array(RoleCodeSchema).min(1),
  scope: WorkflowScopeSchema,
  auditAction: z.string().regex(/^[a-z][a-z0-9_]*$/)
});

export type WorkflowAction = z.infer<typeof WorkflowActionSchema>;

export const CORE_WORKFLOW_ACTIONS = [
  {
    key: "record:create",
    requiredRoles: ["teacher", "grade_lead", "academic_director", "principal"],
    scope: "self",
    auditAction: "workflow_record_create"
  },
  {
    key: "record:grade-review",
    requiredRoles: ["grade_lead"],
    scope: "grade",
    auditAction: "workflow_record_grade_review"
  },
  {
    key: "prompt:release",
    requiredRoles: ["academic_director"],
    scope: "tenant",
    auditAction: "prompt_release"
  },
  {
    key: "backup:restore",
    requiredRoles: ["sys_admin"],
    scope: "system",
    auditAction: "backup_restore"
  }
] satisfies WorkflowAction[];

export function canRolePerform(role: RoleCode, actionKey: string): boolean {
  const action = CORE_WORKFLOW_ACTIONS.find((item) => item.key === actionKey);
  return action
    ? (action.requiredRoles as readonly RoleCode[]).includes(role)
    : false;
}
