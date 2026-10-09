# Codeverse CLI (participants)

Single-file, standard-library Python. Copy the `cli/` folder (or just `codeverse.py`) next to your OBELISK repo.

```
python codeverse.py login                  # server address, team ID, access code (once)
python codeverse.py submit OB-003          # submit your latest commit as the fix for OB-003
python codeverse.py status
python codeverse.py history
python codeverse.py leaderboard
```

`./codeverse` (macOS/Linux) and `codeverse.cmd` (Windows) are shortcuts for `python codeverse.py`.

## Workflow
1. Fix **one** bug in your OBELISK repository and commit it with the label in the message:
   `git commit -am "FIX[OB-003]: repair query history"`
2. From inside the repo run `codeverse submit OB-003`.
3. You get `PASSED x/y`. Only committed changes are submitted; one bug per commit.

Settings live in `~/.codeverse/config.json` (override with `CODEVERSE_HOME`; `CODEVERSE_SERVER` overrides the address).
