# Main observed local browser continuation

Role: Main-controlled Edge via cua_repl; actual UI observations in this conversation.
Target: http://127.0.0.1:8096/weekly-plan; new disposable SQLite/runtime.
Startup source hashes: browser-fullflow-exact-sha-startup.json. Product source is
9cde71655c30cafdc6ac4e99ed22509ad989b121; checkout is docs-only successor
7c0acb9337534d0db60b9ff6d9e1abd09e382643. Integration AI is synthetic, qualification
is local-synthetic, runtime renderer is LibreOffice. No cloud/native Word claim.
This is a Main-authored observation record, not an exported raw AX transcript.

Observed actions and results:
1. Login synthetic3, use home weekly-plan entry, select 2026-09-07..11, open saved
   shared week. Header shows class 四班, week 2, last editor synthetic3, saved state.
   Teachers 教师甲 + 教师乙 and caregiver 保育甲 are loaded.
2. Source dialog: 2026-09-09 displays 出现重复备课，请确认 and two candidates. No
   candidate selected initially. 2026-09-07 selector has no displayed candidate.
   Explicitly select the activity/晨谈 candidate and compare five field differences.
   Reject: activity name remains 活动名称; questions remain 问题. No save invoked.
   Synthetic source accounts have empty display names; this does not verify real
   teacher-name presentation or the one-candidate branch.
3. Clear 本周重点 / 1, generate missing: only that field is proposed as 模拟候选1-0.
   Explicit adoption changes that field and leaves /2=内容21, /3=内容22 and people.
4. Choose 本周重点 / 2 for regeneration: only /2 is proposed, 当前=内容21,
   候选=模拟候选2-0. Reject; /1 remains 模拟候选1-0, /2 remains 内容21.
5. Explicit save displays 草稿已保存 and loaded saved-version state. Actual layout
   check displays 单页检测：实际单页检测通过；页数：1.
6. Logout synthetic3; login synthetic4 through actual login; open same dates.
   Header still shows last editor synthetic3; people still 教师甲 + 教师乙 / 保育甲;
   saved /1=模拟候选1-0, /2=内容21, /3=内容22. Opening did not visibly overwrite them.

Limitations: no all-branch browser PASS. Single-source, all drifts, in-flight
cancellation, TTL expiry, commit_unknown reconciliation, concurrent dual sessions,
new-round overflow/reduction/manual fallback, native Word and download receipt
remain unverified by this round's browser operations. Earlier browser evidence
retains its own source/time role; application tests do not close these UI rows.
