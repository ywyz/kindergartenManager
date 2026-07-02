import { z } from "zod";

export const RoleCodeSchema = z.enum([
  "teacher",
  "grade_lead",
  "academic_director",
  "principal",
  "sys_admin"
]);

export type RoleCode = z.infer<typeof RoleCodeSchema>;

export const ROLE_CODES = RoleCodeSchema.options;

export const ROLE_LABELS = {
  teacher: "教师",
  grade_lead: "年级组长",
  academic_director: "业务园长",
  principal: "园长",
  sys_admin: "系统管理员"
} satisfies Record<RoleCode, string>;
