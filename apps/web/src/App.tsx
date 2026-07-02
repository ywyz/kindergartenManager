import { ROLE_LABELS } from "@kindergarten/contracts";

export function App() {
  return (
    <main>
      <h1>幼儿园教学管理系统 dev4.0</h1>
      <p>角色：{ROLE_LABELS.teacher} / {ROLE_LABELS.academic_director}</p>
    </main>
  );
}
