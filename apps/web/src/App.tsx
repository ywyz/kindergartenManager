import { buildContractViewModel } from "./contract-view-model";

export function App() {
  const model = buildContractViewModel();

  return (
    <main>
      <h1>幼儿园教学管理系统 dev4.0</h1>
      <p>角色：{model.roles.map((role) => role.label).join(" / ")}</p>
      <p>高权限动作：{model.businessPrivilegedActions.length + model.systemPrivilegedActions.length}</p>
    </main>
  );
}
