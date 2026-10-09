# Contestant flow - clone once, fix, submit

This is everything you do in Round 2. You **clone once**. You do **not** `git push` to GitHub:
your fixes are **submitted to the judge with a Python script** that ships in this repo
(`cli/codeverse.py`). The judge replies in your terminal and your score updates on the website.

You need: **Python 3.10+** and **git**. Nothing to install.
(On Windows use `python`; if that is not found, use `py`. On macOS/Linux use `python3` if `python` is not found.)

---

## 0. Once, before the round starts

You will be given a **server address** (for example `192.168.1.40:3000`), your **Team ID** (for
example `CV-032`) and your **Access Code**.

Check you can reach the server:
```
curl http://<server-address>/api/health
```
It should print `{"ok": true, ...}`.

## 1. Clone the repo (only once)

```
git clone <repo-url> obelisk
cd obelisk
```
Do not re-clone later - you would lose your fixes. If you need the latest files, ask an organizer.

Look around:
```
python obelisk.py ingest         # load the bundled data
python obelisk.py status
python scripts/run_tests.py      # 17 failures at the start - those are the bugs
```
Read `BUGS.md` for what is wrong.

## 2. Log in (only once)

```
python cli/codeverse.py login --server <server-address> --team <TEAM-ID> --code <ACCESS-CODE>
python cli/codeverse.py status
```
`status` shows your team, rank, score and which challenges are open or solved. If it says
"OBELISK is locked", the organizers have not opened Round 2 yet.

## 3. The loop - repeat for each bug

1. **Pick a bug** from `BUGS.md` (any order) and reproduce it with the commands there.
2. **Find and fix it.** Edit **only files under `src/obelisk/`**.
3. **Test locally**: `python scripts/run_tests.py`. The failures for your bug should disappear and
   nothing that passed before should start failing.
4. **Commit it** - one bug per commit, and the message **must** contain `FIX[OB-00X]`:
   ```
   git add -A
   git commit -m "FIX[OB-001]: include the last document in the index"
   ```
5. **Submit it** with the script:
   ```
   python cli/codeverse.py submit OB-001
   ```
   You will see it queue and judge:
   ```
   Submitting OB-001: FIX[OB-001]: include the last document in the index
     queued (position 1)
     judging...

   PASSED 119/119  -  OB-001 ACCEPTED
   ```
6. **Check it counted**: `python cli/codeverse.py status` shows `[x]` next to the challenge, and
   the website dashboard and leaderboard update within seconds.

If it says `PASSED 111/118 - not accepted`, some tests still fail. Fix more, commit again (a new
commit, or `git commit --amend`), and submit again. There is a short wait between submissions.

Then go back to step 1 for the next bug.

## Rules that get submissions rejected

| You did | What happens |
|---|---|
| Changed a file outside `src/obelisk/` (tests, docs, data, `cli/`) | Rejected as a forbidden file, and flagged to the organizers |
| Fixed two bugs in one commit | Rejected - one bug per commit |
| Forgot `FIX[OB-00X]` in the commit message, or it does not match the challenge | Stopped locally, nothing is sent |
| Submitted a bug you already solved | Rejected, no penalty |
| Edited files that were not part of the release (re-cloned, replaced files) | "does not apply" - ask an organizer |

You can see your past submissions with `python cli/codeverse.py history`
and the standings with `python cli/codeverse.py leaderboard`.

## Scoring in one minute

- Base points per bug: 50, 75, 100, 150, 200, 300 (875 in total), credited when accepted.
- The fastest teams to solve a bug earn a time bonus of up to +50% of its value. The bonus stays
  hidden during the round and appears when the organizers finalize the results.
- Ties: higher total, then more bugs solved, then who finished earlier.

## Quick fixes for common problems

| Message | What to do |
|---|---|
| `OBELISK is locked` / `PHASE_NOT_OPEN` | Round 2 is not open yet - wait for the organizers |
| `your session is not valid` | Run the `login` command again |
| `wrong team ID or access code` | Check your slip; the Team ID looks like `CV-032` |
| `cannot reach the Codeverse server` | Check the Wi-Fi and the server address |
| `The commit message must contain FIX[OB-00X]` | `git commit --amend -m "FIX[OB-00X]: ..."` then submit again |
| `submitting too quickly` | Wait the number of seconds shown, then retry |
| `a previous submission is still being judged` | Wait for the result of the first one |
| `This team has been disqualified` | Speak to an organizer |
