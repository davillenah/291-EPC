"""PreToolUse hook of the product Claude layer: the hard rules of PRD 14.4 in code (MIG-34).

Claude Code runs it before every tool call (see harness/.claude/settings.json) and passes the event as JSON on stdin:
`tool_name`, `tool_input` (`file_path`, `notebook_path`, `path`, `command`), `cwd`. Exit code 0 lets the call go on; exit code 2 blocks it and
the one-line message on stderr (it names the rule id) goes back to the agent.

The rules are NOT copied here: paths are classified with `epc_platform.permissions.classify_path` and decided with
`epc_platform.permissions.check` (the matrix D-01..D-10, A-01..A-08). The actor role comes from the environment variable `EPC_ACTOR_ROLE`
(default `orchestrator`). Rules that exist only in the hook:

    H-00  malformed event, hook failure or missing path (fail closed)
    H-01  standards and normative knowledge (harness/knowledge/normative) are read-only
    H-02  git writes (owner rule: no git writes)
    H-03  a path that cannot be resolved or classified (variables, command substitution, unknown project paths)
    H-04  an unknown tool whose name says it writes

Deletes (rm, del, Remove-Item, rmdir...) are blocked everywhere as D-01 (nobody deletes anything; owner rule: no deletes).
Two classes are NOT enforced here (EXEMPT_CLASSES): `runs` (the pipeline writes it through its store token and agents keep scratch there) and
`harness_code` (developers change code through review and CODEOWNERS, D-10). Inputs are treated as frozen: agents never edit them with a tool.

Audit: when the environment variable `EPC_PROJECT_DIR` is set, every block is appended as a `denied` event to that project's audit log through
`epc_platform.events` (best effort, never fatal). The hook reads no system clock: the timestamp is `EPC_HOOK_NOW` or `-`.

Standard library only (plus the platform package found next to this file).  Usage:  python harness/.claude/hooks/guard_paths.py < event.json
"""
import json
import os
import re
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2]
REPO = HARNESS.parent
for _extra in (HARNESS / "src" / "platform", HARNESS / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

DEFAULT_ROLE = "orchestrator"
EXEMPT_CLASSES = ("runs", "harness_code")
KNOWLEDGE_NORMATIVE = HARNESS / "knowledge" / "normative"
PROJECTS = REPO / "projects"
PROJECT_FOLDERS = ("inputs", "deliverables", "transmittals", ".epc")

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
SHELL_TOOLS = ("Bash", "PowerShell")
READ_TOOLS = ("Read", "Glob", "Grep", "LS", "NotebookRead", "WebFetch", "WebSearch", "TodoWrite", "Task", "Agent", "Skill", "ToolSearch",
              "BashOutput", "KillShell", "KillBash", "ExitPlanMode", "SlashCommand", "AskUserQuestion")
WRITEISH = re.compile(r"(?i)(write|edit|create|delete|remove|update|put|move|rename|patch|save|append|upload|insert|replace|commit|push)")
PATH_KEYS = ("file_path", "notebook_path", "path")

UNRESOLVABLE = re.compile(r"[$%`]")
WILDCARDS = re.compile(r"[*?\[\]]")
MSYS_DRIVE = re.compile(r"^/([A-Za-z])(/.*)?$")
SEGMENT = re.compile(r"&&|\|\||[;|\n]|(?<!>)&(?![>&])")
TOKEN = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")
REDIRECT = re.compile(r"(?:\d|&)?>>?\s*(?!&)(\"[^\"]*\"|'[^']*'|[^\s;|&<>()]+)")
PATHLIKE = re.compile(r"[\w.~:\\/-]*[/\\][\w.~:\\/-]*|[\w-]+\.\w{1,5}")
INPLACE = re.compile(r"^(--in-place|-[A-Za-z]*i[A-Za-z]*)$")
IGNORED_TARGETS = ("/dev/null", "nul", "$null", "null")

WRAPPERS = ("sudo", "env", "command", "exec", "nohup", "time", "call", "start", "builtin")
SHELLS = ("bash", "sh", "zsh", "dash", "pwsh", "powershell", "cmd")
SHELL_FLAGS = ("-c", "-lc", "-command", "-commandwithargs", "/c", "/k")
CD_VERBS = ("cd", "chdir", "set-location", "sl", "pushd")
DELETE_VERBS = ("rm", "del", "erase", "rmdir", "rd", "remove-item", "ri", "unlink", "shred", "trash")
WRITE_ALL = ("mv", "move", "move-item", "mi", "ren", "rename", "rename-item", "rni", "tee", "touch", "mkdir", "md", "new-item", "ni",
             "set-content", "sc", "add-content", "ac", "out-file", "clear-content", "set-item", "truncate", "install", "ln", "mklink")
WRITE_LAST = ("cp", "copy", "copy-item", "cpi", "xcopy", "robocopy")
GIT_WRITES = ("commit", "push", "merge", "reset", "checkout", "switch", "branch", "tag", "stash", "rebase", "add", "rm", "mv", "restore", "clean",
              "cherry-pick", "revert", "pull", "apply", "am", "init", "clone", "fetch", "gc", "worktree", "submodule", "config", "remote",
              "update-ref", "reflog", "notes", "prune", "filter-branch")
GIT_OPTIONS_WITH_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path")
PY_WRITE = re.compile(r"open\([^)]*['\"][wax]b?\+?['\"]|write_text|write_bytes|\.write\(|shutil\.(copy|copy2|copyfile|copytree|move)|"
                      r"os\.(replace|rename)|to_csv|json\.dump\(|\.save\(")
PY_DELETE = re.compile(r"rmtree|os\.remove|os\.unlink|os\.rmdir|\.unlink\(|\.rmdir\(")


class Block(Exception):
    """The call is refused. `rule_id` names the rule (a matrix id or H-xx), `message` says why in one line."""

    def __init__(self, rule_id, message, target="-"):
        super().__init__(message)
        self.rule_id = rule_id
        self.message = " ".join(str(message).split())
        self.target = str(target)

    def line(self):
        return f"guard_paths: BLOCKED [{self.rule_id}] {self.message}"


# -- the platform's rules ---------------------------------------------------------------------------------------------------------------
def _permissions():
    try:
        from epc_platform import permissions
        from epc_platform.permissions import rules
    except Exception as exc:  # noqa: BLE001 - any import failure must fail closed
        raise Block("H-00", f"the platform permission rules cannot be loaded ({type(exc).__name__}: {exc})") from exc
    return permissions, rules


def _relative(path, base):
    try:
        return path.relative_to(base)
    except ValueError:
        return None


def to_path(text, cwd):
    """The absolute resolved path of a path text; Block H-03 for variables, command substitution or an empty text."""
    if not isinstance(text, str) or not text.strip():
        raise Block("H-00", "the event has an empty or missing path")
    if UNRESOLVABLE.search(text):
        raise Block("H-03", f"cannot resolve {text!r} (variable or command substitution in a path)", text)
    value = text.strip().replace("\\", "/")
    drive = MSYS_DRIVE.match(value) if os.name == "nt" else None
    if drive:
        value = f"{drive.group(1).upper()}:{drive.group(2) or '/'}"
    value = os.path.expanduser(WILDCARDS.sub("_", value))
    path = Path(value)
    try:
        return (path if path.is_absolute() else Path(cwd) / path).resolve()
    except (OSError, ValueError) as exc:
        raise Block("H-03", f"cannot resolve {text!r}: {exc}", text) from exc


def classify(path):
    """The path class (matrix names) of an absolute path, or None when the path is outside every protected place."""
    permissions, _rules = _permissions()
    rel = _relative(path, PROJECTS)
    if rel is not None:
        return _project_class(permissions, rel, path)
    try:
        return permissions.classify_path(PROJECTS / "__none__", path, REPO)
    except permissions.PathError:
        return None


def _project_dir(rel):
    """The project folder holding `rel`: projects/<project> or, in a client folder, projects/<CLIENT>/<project>."""
    nested = rel.parts[1] not in PROJECT_FOLDERS and len(rel.parts) > 2
    return PROJECTS.joinpath(*rel.parts[:2 if nested else 1])


def _project_class(permissions, rel, path):
    if len(rel.parts) <= 1:
        return None
    try:
        return permissions.classify_path(_project_dir(rel), path, REPO)
    except permissions.PathError as exc:
        raise Block("H-03", f"{path.as_posix()} is not a known project path: {exc}", path) from exc


def judge_write(role, text, cwd):
    """Block when `role` may not write `text`. Returns the class that was checked (None when unclassified)."""
    path = to_path(text, cwd)
    if _relative(path, KNOWLEDGE_NORMATIVE) is not None:
        raise Block("H-01", "standards and normative knowledge are read-only", path.as_posix())
    cls = classify(path)
    if cls is None or cls in EXEMPT_CLASSES:
        return cls
    permissions, rules = _permissions()
    action = rules.WRITE if path.exists() else rules.CREATE
    decision = permissions.check(role, action, cls, inputs_frozen=True)
    if not decision.allowed:
        raise Block(decision.rule_id, f"{role} may not {action} {cls}: {decision.reason}", path.as_posix())
    return cls


# -- shell commands ---------------------------------------------------------------------------------------------------------------------
def _strip_quotes(token):
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def tokenise(segment):
    return [_strip_quotes(t) for t in TOKEN.findall(segment)]


def _verb_name(token):
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def split_verb(tokens):
    """(verb, args) of a segment after environment assignments and wrappers such as sudo or env; (None, []) when empty."""
    index = 0
    while index < len(tokens) and ("=" in tokens[index].split("/")[0][:-1] and not tokens[index].startswith("-") or _verb_name(tokens[index]) in WRAPPERS):
        index += 1
    if index >= len(tokens):
        return None, []
    return _verb_name(tokens[index]), tokens[index + 1:]


def _git_subcommand(args):
    index = 0
    while index < len(args):
        if args[index] in GIT_OPTIONS_WITH_VALUE:
            index += 2
        elif args[index].startswith("-"):
            index += 1
        else:
            return args[index].lower()
    return None


def _plain(args):
    return [a for a in args if not a.startswith("-")]


def _write_targets(verb, args):
    if verb == "dd":
        return [a[3:] for a in args if a.startswith("of=")]
    if verb == "sed":
        return _plain(args) if any(INPLACE.match(a) for a in args) else []
    if verb in WRITE_LAST:
        return _plain(args)[-1:]
    return _plain(args) if verb in WRITE_ALL else []


def _find_deletes(verb, args):
    return verb == "find" and ("-delete" in args or any(a in ("rm", "del") for a in args))


def _shell_payload(args):
    lowered = [a.lower() for a in args]
    if any(a.startswith("-enc") for a in lowered):
        raise Block("H-03", "an encoded shell command cannot be inspected")
    for index, flag in enumerate(lowered):
        if flag in SHELL_FLAGS:
            return " ".join(args[index + 1:])
    return None


def _cd_target(cwd, args):
    plain = [a for a in args if not a.startswith("-")]
    if not plain:
        return cwd
    try:
        return str(to_path(plain[0], cwd))
    except Block:
        return None


def _redirect_findings(segment, cwd):
    out = []
    for target in REDIRECT.findall(segment):
        target = _strip_quotes(target)
        if target.lower() not in IGNORED_TARGETS:
            out.append(("write", target, cwd))
    return out


def _segment_findings(segment, cwd, depth):
    """(findings, new cwd) of one shell segment. A finding is (kind, value, cwd) with kind write, delete or git."""
    out = _redirect_findings(segment, cwd)
    verb, args = split_verb(tokenise(segment))
    if verb is None:
        return out, cwd
    if verb in CD_VERBS:
        return out, _cd_target(cwd, args)
    return out + _verb_findings(verb, args, cwd, depth), cwd


def _nested_findings(verb, args, cwd, depth):
    """Findings of the command a shell (bash -c ...) or xargs runs."""
    payload = _shell_payload(args) if verb in SHELLS else " ".join(_plain(args))
    return analyse_command(payload, cwd, depth + 1) if payload else []


def _verb_findings(verb, args, cwd, depth):
    if verb in SHELLS or verb == "xargs":
        return _nested_findings(verb, args, cwd, depth)
    out = []
    if verb == "git" and _git_subcommand(args) in GIT_WRITES:
        out.append(("git", _git_subcommand(args), cwd))
    if verb in DELETE_VERBS or _find_deletes(verb, args):
        out.append(("delete", verb, cwd))
    return out + [("write", t, cwd) for t in _write_targets(verb, args)]


def _python_findings(command, cwd):
    if "python" not in command.lower():
        return []
    out = []
    if PY_DELETE.search(command):
        out.append(("delete", "python", cwd))
    if PY_WRITE.search(command):
        out += [("write", s, cwd) for s in PATHLIKE.findall(command)]
    return out


def analyse_command(command, cwd, depth=0):
    """Findings (kind, value, cwd) for a shell command: every write target, delete and git write it contains."""
    if depth > 2:
        raise Block("H-03", "shell commands nested too deeply to inspect")
    out = _python_findings(command, cwd)
    current = cwd
    for segment in SEGMENT.split(command):
        found, current = _segment_findings(segment, current, depth)
        out += found
    return out


def judge_finding(role, finding):
    kind, value, cwd = finding
    if kind == "git":
        raise Block("H-02", f"git {value} is a git write (owner rule: no git writes)", value)
    if kind == "delete":
        raise Block("D-01", f"{value} deletes; nobody deletes anything (owner rule: no deletes)", value)
    if cwd is None and not Path(value.replace("\\", "/")).is_absolute() and not re.match(r"^[A-Za-z]:|^/", value):
        raise Block("H-03", f"cannot resolve {value!r}: the working directory changed to an unknown place", value)
    judge_write(role, value, cwd or os.getcwd())


# -- the event --------------------------------------------------------------------------------------------------------------------------
def read_event(stream):
    try:
        event = json.loads(stream.read())
    except (ValueError, UnicodeDecodeError) as exc:
        raise Block("H-00", f"the hook event is not valid JSON ({exc})") from exc
    if not isinstance(event, dict) or not isinstance(event.get("tool_name"), str) or not isinstance(event.get("tool_input", {}), dict):
        raise Block("H-00", "the hook event has no tool_name or tool_input")
    return event


def _check_role(role):
    _permissions_mod, rules = _permissions()
    if role not in rules.ROLES:
        raise Block("D-98", f"unknown actor role {role!r} (EPC_ACTOR_ROLE)")


def _edit_path(tool_input):
    for key in PATH_KEYS:
        if isinstance(tool_input.get(key), str) and tool_input[key].strip():
            return tool_input[key]
    raise Block("H-00", "the edit event has no file_path, notebook_path or path")


def decide(event, role=DEFAULT_ROLE):
    """Raise Block when the call must be refused; return None when it may go on."""
    tool, tool_input = event["tool_name"], event.get("tool_input", {})
    cwd = event.get("cwd") if isinstance(event.get("cwd"), str) and event.get("cwd") else os.getcwd()
    if tool in EDIT_TOOLS:
        _check_role(role)
        judge_write(role, _edit_path(tool_input), cwd)
    elif tool in SHELL_TOOLS:
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            raise Block("H-00", "the shell event has no command")
        _judge_command(role, command, cwd)
    elif tool not in READ_TOOLS and not tool.startswith("mcp__epc__") and WRITEISH.search(tool):
        raise Block("H-04", f"unknown tool {tool!r} may write and is not covered by the rules")


def _judge_command(role, command, cwd):
    findings = analyse_command(command, cwd)
    if any(kind == "write" for kind, _v, _c in findings):
        _check_role(role)
    for finding in findings:
        judge_finding(role, finding)


# -- audit and entry point --------------------------------------------------------------------------------------------------------------
def audit_denied(event, role, block, environ):
    """Append a `denied` event to the project's audit log when EPC_PROJECT_DIR is set. Best effort: never raises."""
    project = environ.get("EPC_PROJECT_DIR")
    if not project:
        return False
    try:
        from epc_platform.events import EventLog
        stamp = environ.get("EPC_HOOK_NOW") or "-"
        log = EventLog.for_project(project, lambda: stamp)
        command = str(event.get("tool_input", {}).get("command", ""))[:200]
        log.append({"pipeline_run_id": environ.get("EPC_RUN_ID") or "hook", "actor": {"role": str(role), "id": environ.get("EPC_ACTOR_ID") or "-"},
                    "action": f"hook:{event.get('tool_name')}", "target": block.target or "-", "result": "denied",
                    "detail": {"rule_id": block.rule_id, "reason": block.message, "command": command}})
        return True
    except Exception:  # noqa: BLE001 - the audit must never break the hook
        return False


def run(stdin, stderr, environ):
    """The exit code (0 allow, 2 block) for the event on `stdin`; the reason goes to `stderr`."""
    role = environ.get("EPC_ACTOR_ROLE") or DEFAULT_ROLE
    event = {"tool_name": "?", "tool_input": {}}
    try:
        event = read_event(stdin)
        decide(event, role)
        return 0
    except Block as block:
        audit_denied(event, role, block, environ)
        stderr.write(block.line() + "\n")
    except Exception as exc:  # noqa: BLE001 - fail closed on anything unexpected
        stderr.write(f"guard_paths: BLOCKED [H-00] hook failure ({type(exc).__name__}: {' '.join(str(exc).split())})\n")
    return 2


def main():
    return run(sys.stdin, sys.stderr, os.environ)


if __name__ == "__main__":
    sys.exit(main())
