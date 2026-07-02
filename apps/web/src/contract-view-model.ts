import {
  CORE_WORKFLOW_ACTIONS,
  ROLE_CODES,
  ROLE_LABELS
} from "@kindergarten/contracts";

export interface RoleOptionViewModel {
  code: string;
  label: string;
}

export interface WorkflowActionViewModel {
  key: string;
  scope: string;
  auditAction: string;
  requiredRoleLabels: readonly string[];
}

export interface ContractViewModel {
  roles: readonly RoleOptionViewModel[];
  businessPrivilegedActions: readonly WorkflowActionViewModel[];
  systemPrivilegedActions: readonly WorkflowActionViewModel[];
}

function mapAction(action: (typeof CORE_WORKFLOW_ACTIONS)[number]): WorkflowActionViewModel {
  return {
    key: action.key,
    scope: action.scope,
    auditAction: action.auditAction,
    requiredRoleLabels: action.requiredRoles.map((role) => ROLE_LABELS[role])
  };
}

export function buildContractViewModel(): ContractViewModel {
  return {
    roles: ROLE_CODES.map((code) => ({
      code,
      label: ROLE_LABELS[code]
    })),
    businessPrivilegedActions: CORE_WORKFLOW_ACTIONS.filter(
      (action) => action.scope === "tenant" || action.scope === "grade"
    ).map(mapAction),
    systemPrivilegedActions: CORE_WORKFLOW_ACTIONS.filter(
      (action) => action.scope === "system"
    ).map(mapAction)
  };
}
