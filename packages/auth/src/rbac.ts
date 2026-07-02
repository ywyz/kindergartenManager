import {
  CORE_WORKFLOW_ACTIONS,
  type RoleCode,
  type WorkflowAction,
  type WorkflowScope
} from "@kindergarten/contracts";

export interface AuthorizationContext {
  userId: number;
  tenantId: number;
  roles: readonly RoleCode[];
  managedGradeIds?: readonly number[];
}

export interface WorkflowActionAuthorizationRequest {
  actionKey: string;
  resourceOwnerId?: number;
  resourceGradeId?: number;
  resourceTenantId?: number;
}

export interface AuthorizationDecision {
  allowed: boolean;
  reason: string;
  auditAction?: string;
}

function hasRequiredRole(context: AuthorizationContext, action: WorkflowAction): boolean {
  return context.roles.some((role) =>
    (action.requiredRoles as readonly RoleCode[]).includes(role)
  );
}

function tenantMatches(
  context: AuthorizationContext,
  request: WorkflowActionAuthorizationRequest
): boolean {
  return request.resourceTenantId === undefined || request.resourceTenantId === context.tenantId;
}

function allowsScope(
  context: AuthorizationContext,
  request: WorkflowActionAuthorizationRequest,
  scope: WorkflowScope
): boolean {
  if (scope !== "system" && !tenantMatches(context, request)) {
    return false;
  }

  if (scope === "self") {
    return request.resourceOwnerId === context.userId;
  }
  if (scope === "grade") {
    return (
      request.resourceGradeId !== undefined &&
      (context.managedGradeIds ?? []).includes(request.resourceGradeId)
    );
  }
  if (scope === "tenant") {
    return true;
  }
  return context.roles.includes("sys_admin");
}

export function authorizeWorkflowAction(
  context: AuthorizationContext,
  request: WorkflowActionAuthorizationRequest,
  actions: readonly WorkflowAction[] = CORE_WORKFLOW_ACTIONS
): AuthorizationDecision {
  const action = actions.find((item) => item.key === request.actionKey);
  if (!action) {
    return {
      allowed: false,
      reason: "unknown_action"
    };
  }

  if (!hasRequiredRole(context, action)) {
    return {
      allowed: false,
      reason: "missing_required_role",
      auditAction: action.auditAction
    };
  }

  if (!allowsScope(context, request, action.scope)) {
    return {
      allowed: false,
      reason: `scope_denied:${action.scope}`,
      auditAction: action.auditAction
    };
  }

  return {
    allowed: true,
    reason: "allowed",
    auditAction: action.auditAction
  };
}
