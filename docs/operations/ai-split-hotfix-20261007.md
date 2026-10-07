# AI lesson split reliability hotfix, 2026-10-07

The Aliyun production baseline is c5512af3bbbc9c4b5b9c457e1db7509c301791a6
(v3.4.0-beta16, immutable index 792eee66a96b0dd62a1f2e57a70ddcaf738b019cf323ec4e1cdb87a29e1e2e56).
At 20:44:37 Asia/Shanghai an AI read timeout was followed by an assertion
when the callback tried to access pruned NiceGUI user storage. This prevented
the failure message and loading-button cleanup from completing. The process
had zero container restarts. Browser disconnect timing was not recorded,
so the initial cause of connection loss is still unconfirmed.

The hotfix extends the page reconnect window from 3 to 120 seconds. Each
lesson split/adaptation call waits up to 180 seconds for response data and
executes once; the existing timeout/retry defaults remain for other AI tasks.
The page cancels its split on client deletion and never revalidates a deleted
client in cleanup. Missing user storage fails closed without an assertion.
Provider failures use local safe messages; stale target results are discarded
with an explicit explanation, preserving existing date/version/form guards.

The default hotfix Docker target derives from the exact existing dual-platform
production index and copies only the six changed application files. The
renderer test/full rebuild targets remain available. This avoids resolving
new runtime dependencies during the repair.

No schema, saved teacher configuration, prompt versions, or provider key is
changed. No background task system or automatic draft save is introduced.
An explicit reload/navigation or disconnect lasting beyond the reconnect
window still ends the unsaved operation. Slow/unavailable providers may still
time out, but the current page reports the failure and enables another try.

Isolated verification uses the exact production dependencies, no production
volumes and no network. The new 14 regressions and the existing AI client,
lesson client/service, UI session, daily target and daily date tests pass:
75 tests in 15.48 seconds. The UI session tests explicitly supply a live client context
because they execute outside NiceGUI's UI event loop. Earlier verification
found six test-seam incompatibilities; these were corrected before release.
This does not replace a real teacher/browser/provider acceptance run.

Deployment must use the repository's immutable multi-platform image and
backup/deploy helpers. Record exact source/image identities, restore-verified
backup, liveness, readiness, login/business gates and rollback identity in a
separate final operations result. Keep credentials, database archives and
NiceGUI session storage in protected server directories.
