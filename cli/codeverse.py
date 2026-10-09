#!/usr/bin/env python3
"""Codeverse participant CLI - submit OBELISK fixes to the judging server.

    codeverse login                 sign in (asks for the server address once)
    codeverse submit OB-003         submit your latest commit as the fix for OB-003
    codeverse status                your score, rank and challenge progress
    codeverse history               your recent submissions
    codeverse leaderboard           top of the leaderboard

Pure Python standard library (3.8+). Needs `git` for `submit`.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "1.0.0"

REASONS = {
    "LABEL_MISSING": "The commit message must contain FIX[OB-00X], e.g. FIX[OB-003]: repair history.",
    "LABEL_MISMATCH": "The commit label does not match the challenge you submitted for.",
    "FORBIDDEN_PATH": "Your commit changes files outside src/obelisk/. Only source files may change.",
    "BAD_PATCH": "The patch could not be read. Submit a normal text commit (no binary files or symlinks).",
    "DOES_NOT_APPLY": "Your commit does not apply on top of the official base plus your accepted fixes.",
    "ALREADY_SOLVED": "You have already solved this challenge.",
    "MULTIPLE_FIXES": "This commit fixes more than one bug. Submit one bug fix per commit.",
    "TIMEOUT": "Your code took too long to run the tests (possible infinite loop).",
    "JUDGE_ERROR": "The judge had an internal error. Ask an organizer; try again shortly.",
    "EVENT_NOT_LIVE": "The event is not live right now.",
    "EVENT_ENDED": "The event has ended.",
    "PHASE_NOT_OPEN": "OBELISK opens when the organizers start Phase 2.",
    "DISQUALIFIED": "This team has been disqualified. Contact the organizers.",
}


class CliError(Exception):
    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


# --- config -------------------------------------------------------------------


def home_dir() -> Path:
    return Path(os.environ.get("CODEVERSE_HOME") or Path.home() / ".codeverse")


def load_config() -> dict:
    try:
        return json.loads((home_dir() / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    d = home_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(d / "config.json", 0o600)
    except OSError:
        pass


def normalise_server(raw: str) -> str:
    raw = raw.strip().rstrip("/")
    if not raw:
        raise CliError("server address is empty")
    if not re.match(r"^https?://", raw):
        raw = "http://" + raw
    return raw


# --- HTTP ---------------------------------------------------------------------


def request(cfg: dict, method: str, path: str, body: dict | None = None, auth: bool = True):
    server = os.environ.get("CODEVERSE_SERVER") or cfg.get("server")
    if not server:
        raise CliError("no server configured - run: codeverse login")
    req = urllib.request.Request(
        server.rstrip("/") + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
    )
    req.add_header("Content-Type", "application/json")
    if auth:
        if not cfg.get("token"):
            raise CliError("you are not signed in - run: codeverse login")
        req.add_header("Authorization", "Bearer " + cfg["token"])
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {"error": "HTTP_ERROR", "message": f"HTTP {exc.code}"}
    except (urllib.error.URLError, OSError) as exc:
        raise CliError(f"cannot reach the Codeverse server at {server}: {getattr(exc, 'reason', exc)}")


def need(status: int, data, expected: int = 200):
    if status == 401:
        raise CliError("your session is not valid - run: codeverse login")
    if status == 403 and data.get("error") in REASONS:
        raise CliError(REASONS[data["error"]])
    if status != expected:
        raise CliError(data.get("message") or data.get("error") or f"server error {status}")
    return data


# --- commands -----------------------------------------------------------------


def cmd_login(args, cfg: dict) -> int:
    server = args.server or os.environ.get("CODEVERSE_SERVER") or cfg.get("server")
    if not server:
        server = input("Server address (shown by the organizers, e.g. 192.168.1.10:3000): ")
    server = normalise_server(server)
    team = args.team or input("Team ID: ").strip()
    code = args.code or getpass.getpass("Access code: ")
    cfg = {**cfg, "server": server}
    status, data = request(cfg, "POST", "/api/login", {"teamId": team, "accessCode": code}, auth=False)
    if status == 401:
        raise CliError("wrong team ID or access code")
    need(status, data)
    cfg.update(token=data["token"], teamId=data["participantId"])
    save_config(cfg)
    print(f"Signed in as {data['participantId']} on {server}")
    return 0


def cmd_status(args, cfg: dict) -> int:
    me = need(*request(cfg, "GET", "/api/me"))
    ev = need(*request(cfg, "GET", "/api/status", auth=False))
    print(f"{me['teamName']} ({me['teamId']})   rank {me['rank']}/{me['totalTeams']}   score {me['score']}")
    print(f"event: {ev['status']}   phase {ev['phase']}   ends {ev['endTime']}")
    if "gamesPlayed" in me:
        print(f"games: {me['gamesPlayed']}/{me['gamesTotal']} played   games score {me['gamesScore']}")
    print()
    if me.get("obeliskOpen") is False:
        print("  OBELISK is locked: it opens when the organizers start Phase 2.")
        return 0
    chs = need(*request(cfg, "GET", "/api/challenges"))
    for c in chs:
        mark = {"SOLVED": "[x]", "IN_PROGRESS": "[~]"}.get(c["status"], "[ ]")
        print(f"  {mark} {c['id']}  {c['name']:<26} {c['points']:>4} pts  {c['status'].replace('_', ' ').lower()}")
    return 0


def cmd_history(args, cfg: dict) -> int:
    rows = need(*request(cfg, "GET", "/api/submissions"))
    if not rows:
        print("no submissions yet")
    for r in rows:
        print(describe(r))
    return 0


def cmd_leaderboard(args, cfg: dict) -> int:
    rows = need(*request(cfg, "GET", "/api/leaderboard", auth=False))
    for r in rows[: args.top]:
        print(f"{r['rank']:>3}  {r['teamName']:<28} {r['solvedCount']}/6  {r['score']:>5}")
    return 0


def describe(r: dict) -> str:
    score = f"{r['passed']}/{r['total']}" if r.get("total") is not None else "-"
    extra = f"  ({REASONS.get(r['reason'], r['reason'])})" if r.get("reason") else ""
    return f"#{r['id']:<4} {r['challenge']}  {r['status']:<9} {score:>8}{extra}"


def git(*cmd: str, cwd: str | None = None) -> str:
    try:
        out = subprocess.run(["git", *cmd], cwd=cwd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise CliError("git is not installed or not on your PATH")
    if out.returncode != 0:
        raise CliError(out.stderr.strip() or "git command failed")
    return out.stdout


def cmd_submit(args, cfg: dict) -> int:
    challenge = args.challenge.upper()
    if not re.fullmatch(r"OB-\d{3}", challenge):
        raise CliError("challenge must look like OB-003")
    repo = args.repo or os.getcwd()
    top = git("rev-parse", "--show-toplevel", cwd=repo).strip()
    rev = args.commit
    subject = git("log", "-1", "--format=%s", rev, cwd=top).strip()
    labels = {m.upper() for m in re.findall(r"FIX\[(OB-\d{3})\]", git("log", "-1", "--format=%B", rev, cwd=top), re.I)}
    if labels != {challenge}:
        raise CliError(
            f'The commit message must contain FIX[{challenge}].\n  Your latest commit says: "{subject}"\n'
            f'  Fix it with: git commit --amend -m "FIX[{challenge}]: describe your fix"'
        )
    dirty = git("status", "--porcelain", "--untracked-files=no", cwd=top).strip()
    if dirty and rev == "HEAD":
        print("note: you have uncommitted changes - only the committed fix is submitted.\n")
    patch = git("format-patch", "--stdout", "-1", rev, cwd=top)

    print(f"Submitting {challenge}: {subject}")
    status, data = request(cfg, "POST", "/api/submissions", {"challenge": challenge, "patch": patch})
    if status == 409:
        raise CliError("You already have a submission being judged - wait for its result.")
    if status == 429:
        raise CliError(f"Too many submissions - wait {data.get('retryAfter', 'a few')} seconds and try again.")
    if status == 403:
        raise CliError(REASONS.get(data.get("error"), data.get("message", "submissions are closed")))
    sub = need(status, data)

    shown = None
    while sub["status"] in ("QUEUED", "RUNNING"):
        line = "judging..." if sub["status"] == "RUNNING" else f"queued (position {sub.get('queuePosition', '?')})"
        if line != shown:
            print(" ", line)
            shown = line
        time.sleep(1.0)
        sub = need(*request(cfg, "GET", f"/api/submissions/{sub['id']}"))

    print()
    if sub["status"] == "ACCEPTED":
        print(f"PASSED {sub['passed']}/{sub['total']}  -  {challenge} ACCEPTED")
        return 0
    if sub.get("total") is not None:
        print(f"PASSED {sub['passed']}/{sub['total']}  -  not accepted")
    else:
        print("Not accepted")
    if sub.get("reason"):
        print(" ", REASONS.get(sub["reason"], sub["reason"]))
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="codeverse", description="Codeverse submission CLI")
    p.add_argument("--version", action="version", version=f"codeverse {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("login", help="sign in to the competition server")
    s.add_argument("--server")
    s.add_argument("--team")
    s.add_argument("--code")
    s.set_defaults(fn=cmd_login)

    s = sub.add_parser("submit", help="submit your latest commit as the fix for a challenge")
    s.add_argument("challenge", help="e.g. OB-003")
    s.add_argument("--repo", help="path to your OBELISK repository (default: current directory)")
    s.add_argument("--commit", default="HEAD", help="commit to submit (default: HEAD)")
    s.set_defaults(fn=cmd_submit)

    sub.add_parser("status", help="your score, rank and progress").set_defaults(fn=cmd_status)
    sub.add_parser("history", help="your recent submissions").set_defaults(fn=cmd_history)
    s = sub.add_parser("leaderboard", help="show the leaderboard")
    s.add_argument("--top", type=int, default=15)
    s.set_defaults(fn=cmd_leaderboard)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args, load_config())
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("\ninterrupted - your submission (if sent) is still being judged; see: codeverse history")
        return 130


if __name__ == "__main__":
    sys.exit(main())
