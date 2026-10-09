# OBELISK

**Search & Intelligence Engine** - the Royal Mint's internal command-line system for
ingesting, indexing, searching and inspecting its records.

OBELISK is currently misbehaving. You have inherited it.

- Pure Python, standard library only. **No install step, no internet, no database, no Docker.**
- Works on Windows, macOS and Linux (Python 3.10 or newer).
- Everything it needs - sample data included - is in this repository.

## Quick start

```
python obelisk.py ingest          # load the bundled data (data/) and build the index
python obelisk.py status
python obelisk.py search "vault AND security"
python obelisk.py suggest sec
python obelisk.py transaction TX-10100
```

Pick whichever launcher suits your platform - they are equivalent:

| Platform        | Command                                   |
|-----------------|-------------------------------------------|
| Any             | `python obelisk.py <command>`             |
| macOS / Linux   | `./obelisk <command>`                     |
| Windows         | `obelisk.cmd <command>`                   |
| Any (module)    | `PYTHONPATH=src python -m obelisk <command>` (Windows cmd: `set PYTHONPATH=src` first) |

Optional: `pip install -e . --no-build-isolation` gives you an `obelisk` command on your PATH.

Generated state (index, history, cache) lives in `.obelisk-state/` at the repository root.
Delete that folder at any time to start from scratch. Set `OBELISK_HOME` to use another location.

## Commands

`ingest`, `inspect`, `search`, `history`, `suggest`, `transaction`, `cache`, `logs`,
`status`, `index`, `rebuild`, `bench`. Run `python obelisk.py --help` or
`python obelisk.py <command> --help`. Every command accepts `--json` for machine-readable output.
Full reference: [docs/commands.md](docs/commands.md).

## Documentation

| Document                                    | Contents                                   |
|---------------------------------------------|--------------------------------------------|
| [docs/commands.md](docs/commands.md)        | every command, option and exit code         |
| [docs/search.md](docs/search.md)            | query syntax and semantics                  |
| [docs/data-format.md](docs/data-format.md)  | input files and generated state             |
| [docs/architecture.md](docs/architecture.md)| how the code is organised                   |
| [docs/contributing.md](docs/contributing.md)| working on OBELISK, tests, competition workflow |

## Running the tests

```
python scripts/run_tests.py        # add -v for per-test output
```

The tests in `public_tests/` describe the behaviour OBELISK is documented to have. They are
there to help you develop and debug. You may read, run and modify them; they carry no authority
over your official result, which is determined by the Codeverse judging system.

## Repository layout

```
obelisk.py, obelisk, obelisk.cmd   launchers
src/obelisk/                       the application
data/                              sample documents, transactions and logs
public_tests/                      public test-suite
docs/                              documentation
scripts/                           helper scripts (test runner, sample-data generator)
```
