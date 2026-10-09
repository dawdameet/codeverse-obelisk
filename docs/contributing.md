# Working on OBELISK

## Set-up
Nothing to install. Run `python scripts/run_tests.py` to check your environment.

## Understanding a failure
1. Reproduce it with the CLI (`--json` makes output easy to compare).
2. Read the relevant documentation in `docs/` to establish the *intended* behaviour.
3. Read the code of the subsystem involved and the tests that exercise it.
4. Fix the cause, not the symptom, and keep the change small.

## Style
Standard library only, type hints where they help, no global mutable state, deterministic output,
paths via `pathlib` (never hard-coded separators).

## Competition workflow
You work in this repository; the Codeverse website only shows the rules and standings.

- Each problem is fixed in **its own commit** - one bug, one patch - starting from the official base.
- Commit messages start with the challenge ID, e.g. `FIX[OB-003]: repair query history`.
- Test locally with `python scripts/run_tests.py`. Public tests are for development and debugging;
  you may change them, but they have no authority over your official score. Official judging uses
  the Codeverse judging system.
- Submit each commit with the Codeverse submission CLI while connected to the event network.

Do not add network access or third-party dependencies to OBELISK.
