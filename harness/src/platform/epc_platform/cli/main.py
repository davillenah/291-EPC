"""`epc`: the command-line entry point. `main(argv)` returns the exit code (0 ok, 1 api error envelope, 2 usage error); it never exits.

The CLI parses arguments, reads the JSON files the user names, calls `epc_platform.api` and renders the envelope. This module holds the
ONLY read of the system clock in the platform (`utc_now`); every api function receives the clock as a parameter.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from epc_platform.cli import commands, render

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2
GLOBALS = (
    (("--projects-root",), {"metavar": "DIR", "help": "folder that holds the projects (env EPC_PROJECTS_ROOT; default: projects in the repository root)"}),
    (("--actor-role",), {"metavar": "ROLE", "help": "RACI role to act as (env EPC_ACTOR_ROLE; default orchestrator)"}),
    (("--actor-id",), {"metavar": "ID", "help": "actor id in the audit log (env EPC_ACTOR_ID; default cli)"}),
    (("--json",), {"action": "store_true", "help": "print the api envelope as canonical JSON"}),
)


def utc_now():
    """The default clock of the CLI: the current UTC time as text. The only place of the platform that reads the system clock."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ParserExit(Exception):
    """argparse wanted to exit: `status` 0 for help, 2 for a usage error; `message` is the text to print."""

    def __init__(self, status, message=None):
        super().__init__(message)
        self.status = status
        self.message = message


class Parser(argparse.ArgumentParser):
    """An argparse parser that never calls sys.exit and prints help to the injected stdout."""

    def __init__(self, *args, out=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.out = out

    def error(self, message):
        raise ParserExit(EXIT_USAGE, f"{self.format_usage()}{self.prog}: error: {message}")

    def exit(self, status=0, message=None):
        raise ParserExit(status, message)

    def print_help(self, file=None):
        self.out.write(self.format_help())

    def print_usage(self, file=None):
        self.out.write(self.format_usage())


def _add_globals(parser, inherited):
    """The global options; in the subcommands they are optional overrides that leave the top-level value alone when absent."""
    for flags, kwargs in GLOBALS:
        parser.add_argument(*flags, **dict(kwargs, **({"default": argparse.SUPPRESS} if inherited else {})))


def _holder(top, groups, words, out):
    """The subparsers object a command hangs from: the top one, or the one of its group (`engines`)."""
    if len(words) == 1:
        return top
    if words[0] not in groups:
        group = top.add_parser(words[0], help="engine queries", out=out)
        groups[words[0]] = group.add_subparsers(dest="action", required=True, metavar="ACTION", parser_class=Parser)
    return groups[words[0]]


def build_parser(out):
    parser = Parser(prog="epc", description="EPC-291 command line: the same functions as the MCP server.", out=out)
    _add_globals(parser, False)
    top, groups = parser.add_subparsers(dest="group", required=True, metavar="COMMAND", parser_class=Parser), {}
    for command in commands.COMMANDS.values():
        words = command.key.split()
        leaf = _holder(top, groups, words, out).add_parser(words[-1], help=command.help, out=out)
        for flags, kwargs in command.arguments:
            leaf.add_argument(*flags, **kwargs)
        _add_globals(leaf, True)
        leaf.set_defaults(key=command.key)
    return parser


def _session(args, env, clock):
    root = args.projects_root or env.get("EPC_PROJECTS_ROOT") or commands.default_projects_root()
    actor = {"role": args.actor_role or env.get("EPC_ACTOR_ROLE") or "orchestrator", "id": args.actor_id or env.get("EPC_ACTOR_ID") or "cli"}
    return commands.Session(projects_root=Path(root), actor=actor, clock=clock)


def _emit(envelope, args, out, err):
    if args.json:
        out.write(render.as_json(envelope) + "\n")
    elif envelope["ok"]:
        out.write(render.render(args.key, envelope["data"]) + "\n")
        err.writelines(f"warning: {w}\n" for w in envelope.get("warnings", []))
    else:
        err.write(render.error_text(envelope) + "\n")
    return EXIT_OK if envelope["ok"] else EXIT_ERROR


def main(argv=None, *, stdout=None, stderr=None, clock=None, env=None):
    """Run one `epc` command and return its exit code. `clock` returns the event timestamp text; `env` is the environment mapping."""
    out, err = stdout or sys.stdout, stderr or sys.stderr
    try:
        args = build_parser(out).parse_args(sys.argv[1:] if argv is None else list(argv))
    except ParserExit as stop:
        if stop.message:
            (out if stop.status == EXIT_OK else err).write(stop.message if stop.message.endswith("\n") else stop.message + "\n")
        return stop.status
    session = _session(args, os.environ if env is None else env, clock or utc_now)
    return _emit(commands.run_command(session, args), args, out, err)
