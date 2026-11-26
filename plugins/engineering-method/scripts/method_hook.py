#!/usr/bin/env python3
"""Re-apply the engineering method without anyone reminding the agent.

A skill is loaded once and then forgotten: after /clear or compaction the
summary does not carry it, and a fresh session has not read it yet. These
hooks put a short reminder into context at the moments that matter.

Two modes, wired to two events (see hooks/hooks.json):

  --session-start   startup, /clear, compaction: a brief of the method, the
                    stakes tiers and the stage map. Also resets the
                    per-session stage memory.
  --prompt          every user prompt: if the prompt moves to a stage of work
                    not yet announced in this session,
                    say which skill and references apply. Otherwise silent.

STAGES below is the single source of the stage map; both modes read it.

Never fails loudly: a broken reminder must not block a session. Every error
path exits 0; --prompt then prints nothing, --session-start prints a
one-line brief. Standard library only, Python 3.10+.
"""
import json
import os
import re
import sys
import tempfile
import time

STATE_FILE = "method-stage.json"
STATE_TTL_SECONDS = 7 * 24 * 3600
MAX_SCAN_CHARS = 4096  # stage intent sits at the start of a prompt
WRAPPER_TAGS = {"pasted_content", "command-name", "command-message", "command-args",
                "system-reminder"}

STAGES = [
    {"stage": "plan",
     "words": ["plan", "plans", "planning", "planned", "design", "designs", "designing",
               "designed", "spec", "specs"],
     "skill": "superpowers:writing-plans",
     "references": ["docs-and-decisions.md", "parallel-and-worktrees.md"]},
    {"stage": "debug",
     "words": ["debug", "debugs", "debugging", "debugged", "investigate", "investigates",
               "investigating", "investigated", "investigation", "diagnose", "diagnoses",
               "diagnosing", "diagnosed", "diagnosis", "bug", "bugs"],
     "skill": "superpowers:systematic-debugging",
     "references": ["root-cause-investigation.md", "measurement-and-state-claims.md"],
     "note": "evidence first (tier b, c): no cause, suspect list or fix until RC-1 to RC-4 "
             "are done, requested or skipped; "},
    {"stage": "build",
     "words": ["build", "builds", "building", "built", "implement", "implements",
               "implementing", "implemented", "fix", "fixes", "fixing", "fixed",
               "refactor", "refactors", "refactoring", "refactored"],
     "skill": "superpowers:test-driven-development",
     "references": ["model-routing-and-cost.md", "parallel-and-worktrees.md"]},
    {"stage": "review",
     "words": ["review", "reviews", "reviewing", "reviewed"],
     "skill": "superpowers:requesting-code-review",
     "references": ["review-loop.md"]},
    {"stage": "test",
     "words": ["test", "tests", "testing", "tested", "bench", "benchmark", "eval", "evals",
               "verify", "verifies", "verifying", "verified", "pytest"],
     "skill": "superpowers:verification-before-completion",
     "references": ["measurement-and-state-claims.md", "behaviour-evals.md"],
     "note": "a plan exists (tier b, c): run the skill's scripts/plan_conformance.py <plan+diff file> before saying "
             "verified; the owner rules each mismatch; "},
    {"stage": "deploy",
     "words": ["deploy", "deploys", "deploying", "deployed", "deployment", "deployments", "rollout", "rollouts",
               "rollback", "rollbacks", "restart", "restarts", "restarting", "restarted",
               "migrate", "migrates", "migrating", "migrated", "prod", "production", "live"],
     "skill": None,
     "references": ["live-system-changes.md"]},
    {"stage": "merge",
     "words": ["merge", "merges", "merging", "merged", "push", "pushes", "pushing", "pushed", "pr", "prs", "commit", "commits",
               "committing", "committed"],
     "skill": "superpowers:finishing-a-development-branch",
     "references": ["live-system-changes.md"]},
    {"stage": "release",
     "words": ["release", "releases", "releasing", "released", "promote", "promotes",
               "promoting", "promoted", "ship", "ships", "shipping", "shipped"],
     "skill": None,
     "references": ["live-system-changes.md", "progress-ladder.md"]},
    {"stage": "report",
     "words": ["status", "progress", "report", "reports", "reporting", "reported"],
     "skill": None,
     "references": ["progress-ladder.md", "measurement-and-state-claims.md"]},
]

FALLBACK_BRIEF = "engineering-method active; load the skill before acting"

# Two-word phrases that name a stage (matched on adjacent words).
PHRASES = {("roll", "back"): "deploy", ("rolling", "back"): "deploy",
           ("rolled", "back"): "deploy", ("pull", "request"): "merge",
           ("pull", "requests"): "merge", ("root", "cause"): "debug"}

# Build words that give way to debug when a debug word is also present ("fix the bug").
FIX_WORDS = ("fix", "fixes", "fixing", "fixed")

# word -> stage lookup, derived from STAGES (never edited by hand)
_BY_NAME = {s["stage"]: s for s in STAGES}
_WORD_TO_STAGE = {w: s for s in STAGES for w in s["words"]}
_WORD_RE = re.compile(r"[A-Za-z]+")  # hyphens split tokens: re-deploy, unit-tests
_OPEN_TAG_RE = re.compile(r"<([A-Za-z][\w:-]*)[^<>]*>")  # anchored, no backtracking
_CLOSE_TAG_RE = re.compile(r"</([A-Za-z][\w:-]*)\s*>")
_NOISE_LINE_RE = re.compile(
    r"^(?:(?:[ ]{4,}|\t)(?![-*]\s|\d+\.\s)|\s*\d{4}-\d{2}-\d{2}|\s*\d{1,2}:\d{2}:\d{2}"
    r"|\s*(?:ERROR|WARN|WARNING|INFO|DEBUG|Traceback)\b|\s*>>>|\s*\$ |\s*def )")


def read_stdin_json():
    """Read the hook payload from stdin.

    Why: the harness always sends JSON; the pipe must be drained even when
    the content is useless, or the writer can block.
    Inputs: none (stdin). Output: a dict, {} on any problem. Side effects:
    consumes stdin.
    """
    try:
        data = json.loads(sys.stdin.read())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def emit(event, text):
    """Print the hook JSON contract with text as additionalContext.

    Why: this is the only channel by which a hook reaches model context.
    Inputs: event name, context text. Output: none. Side effects: one JSON
    line on stdout.
    """
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event,
                                             "additionalContext": text}}))


def state_path():
    """Locate the per-session stage memory file.

    Why: plugin data survives plugin updates; the temp dir is the fallback
    when CLAUDE_PLUGIN_DATA is unset. Inputs: environment. Output: path
    string. Side effects: none.
    """
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or tempfile.gettempdir()
    return os.path.join(base, STATE_FILE)


def load_state():
    """Read the stage memory, dropping entries older than seven days.

    Why: the file must not grow forever, and a damaged file must not matter.
    Inputs: none. Output: {session_id: {"stages": [...], "at"}}; {} if missing or
    corrupt. Side effects: none.
    """
    try:
        with open(state_path()) as fh:
            raw = json.load(fh)
        cutoff = time.time() - STATE_TTL_SECONDS
        return {k: v for k, v in raw.items()
                if isinstance(v, dict) and isinstance(v.get("at"), (int, float))
                and v["at"] >= cutoff}
    except Exception:
        return {}


def save_state(state):
    """Write the stage memory atomically (temp file, then rename).

    Why: two prompts can race; a half-written file must never be read.
    Inputs: the state dict. Output: none. Side effects: writes the state
    file; silently gives up if the directory is unwritable.
    """
    path = state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".method-stage-")
        with os.fdopen(fd, "w") as fh:
            json.dump(state, fh)
        os.replace(tmp, path)
    except Exception:
        pass


def announced(session_id):
    """Return the set of stages already announced in this session.

    Why: each stage speaks at most once per session, so alternating between
    two stages cannot make the hook flap. Inputs: session id. Output: set of
    stage names. Side effects: none.
    """
    stages = load_state().get(session_id, {}).get("stages")
    return set(stages) if isinstance(stages, list) else set()


def set_stage(session_id, stage):
    """Record a stage as announced, or forget the session when stage is None.

    Why: the set is reset by SessionStart, because a new context no longer
    holds earlier announcements. Inputs: session id, stage name or None.
    Output: none. Side effects: rewrites the state file.
    """
    state = load_state()
    if stage is None:
        state.pop(session_id, None)
    else:
        seen = announced(session_id) | {stage}
        state[session_id] = {"stages": sorted(seen), "at": time.time()}
    save_state(state)


def strip_blocks(text):
    """Remove ``` fences and wrapper blocks over the whole text, linearly.

    Why: a regex with a backreference backtracks quadratically on unclosed
    tags, and a closer search per distinct tag name would not be linear
    either. Only WRAPPER_TAGS (pasted_content, command-name, ...) get block
    stripping, with one closer search each; an unclosed fence or wrapper
    drops everything after it. Any other <tag> or </tag> token is removed
    on its own and its contents stay, so "Vec<T>" cannot hide a request.
    Uses str.find and anchored regexes only. Inputs: text. Output: text with
    blocks replaced by a space. Side effects: none.
    """
    out, i = [], 0
    while True:
        j = text.find("```", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j] + " ")
        k = text.find("```", j + 3)
        if k < 0:
            break
        i = k + 3
    text, out, i = "".join(out), [], 0
    while True:
        j = text.find("<", i)
        if j < 0:
            out.append(text[i:])
            break
        m = _OPEN_TAG_RE.match(text, j) or _CLOSE_TAG_RE.match(text, j)
        if not m:
            out.append(text[i:j + 1])
            i = j + 1
            continue
        name = m.group(1)
        close = -1
        if name in WRAPPER_TAGS and not m.group(0).startswith("</"):
            close = text.find("</%s>" % name, m.end())
            if close < 0:
                out.append(text[i:j])
                break
            out.append(text[i:j] + " ")
            i = close + len(name) + 3
        else:  # any other tag: drop the token, keep what is inside
            out.append(text[i:j] + " ")
            i = m.end()
    return "".join(out)


def clean_prompt(prompt):
    """Strip the parts of a prompt that are not the user's own words.

    Why: pasted logs, code and tool wrappers contain stage words that say
    nothing about what the user is asking for. Fences and tag blocks are
    removed over the WHOLE prompt first (so a long paste cannot lose its
    closing tag to the cap, and a request after it is still seen); only then
    is the remainder capped to MAX_SCAN_CHARS (stage intent sits at the
    start, and the cap bounds the work). Log/code-looking lines are dropped,
    but not indented list items. Inputs: prompt text. Output: cleaned text.
    Side effects: none.
    """
    text = strip_blocks(prompt)[:MAX_SCAN_CHARS]
    return "\n".join(l for l in text.split("\n") if not _NOISE_LINE_RE.match(l))


def detect_stage(prompt):
    """Find the stage a prompt asks for.

    What: the stage of the earliest stage word or phrase (the first verb usually
    names the work asked for), except that when the earliest match is a fix word
    (FIX_WORDS) and a debug word or phrase follows before any other non-build
    stage word, the stage is debug (if that other stage word comes first, it wins) ("fix the bug" investigates first). Other
    build words keep build. The prompt is cleaned first, a leading slash-command
    token is skipped ("/plan-layer status" is not "plan"), and "git status" is
    ignored because it is a command, not a request for a report. Whole-word,
    case-insensitive; hyphens split words.
    Use when: the --prompt hook decides whether to announce a stage.
    Inputs: prompt text.
    Output: a STAGES entry, or None.
    Side effects: none.
    Role: routing only; one linear pass over at most MAX_SCAN_CHARS.
    """
    text = clean_prompt(prompt).lstrip()
    if text.startswith("/"):
        parts = text.split(None, 1)
        text = parts[1] if len(parts) > 1 else ""
    words = [m.lower() for m in _WORD_RE.findall(text)]
    first = None
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (w, nxt) in PHRASES:
            stage = _BY_NAME[PHRASES[(w, nxt)]]
        elif w == "status" and i > 0 and words[i - 1] == "git":
            continue
        else:
            stage = _WORD_TO_STAGE.get(w)
        if stage is None:
            continue
        if first is None:
            first = stage
            if first["stage"] != "build" or w not in FIX_WORDS:
                return first
        elif stage["stage"] == "debug":
            return stage
        elif stage["stage"] != "build":
            return stage  # a nearer plan/review/test/deploy/merge/release/report word wins
    return first


def stage_message(stage):
    """Compose the short per-stage reminder (at most 400 characters).

    What: names the stage's SKILL.md row, skill and references, plus the stage's
    optional "note" (the debug stage carries its evidence-before-cause rule).
    Why: it names exactly what to re-read and load, and the one rule a stage's
    answers skipped in evals, nothing more.
    Inputs: a STAGES entry. Output: text. Side effects: none. Role: routing text only.
    """
    skill = "load %s, " % stage["skill"] if stage["skill"] else ""
    refs = ", ".join("references/" + r for r in stage["references"])
    return ("engineering-method: stage %s — re-read SKILL.md §3 row '%s', %sread %s before "
            "acting; %skeep the stakes tier you named."
            % (stage["stage"], stage["stage"], skill, refs, stage.get("note", "")))[:400]


def session_brief(source):
    """Compose the session brief (at most 1,500 characters).

    Why: startup, /clear and compaction all lose the method; this restores
    its shape. Inputs: the SessionStart source. Output: text. Side effects:
    none.
    """
    stages = "; ".join(" -> ".join([s["stage"]] + ([s["skill"]] if s["skill"] else [])
                                   + [", ".join("references/" + r for r in s["references"])])
                       for s in STAGES)
    lines = [
        "engineering-method is active in this session.",
        "First name the stakes tier (an owner update opens with what needs the owner, then the tier): (a) exploration: throwaway, keep it light; "
        "(b) internal: others rely on it, show evidence; "
        "(c) live: real users or data, backup, rollback and read-backs first.",
        "Stage map (stage -> skill -> references): " + stages + ".",
        "Load engineering-method and the stage's reference before you dispatch, "
        "answer or act.",
    ]
    if source == "compact":
        lines.append("context was just compacted: the summary does not carry the "
                     "method; re-read the engineering-method skill now.")
    return "\n".join(lines)[:1500]


def session_start():
    """SessionStart mode: reset stage memory and emit the brief.

    Why: a new context means the last announcement is no longer in view.
    Inputs: stdin payload (source, session_id). Output: hook JSON. Side
    effects: clears this session's stage memory.
    """
    data = read_stdin_json()
    sid = data.get("session_id")
    if isinstance(sid, str) and sid:
        set_stage(sid, None)
    source = data.get("source")
    emit("SessionStart", session_brief(source if isinstance(source, str) else ""))


def prompt_mode():
    """UserPromptSubmit mode: speak only when the stage changes.

    Why: the event has no matcher, so the script decides. Inputs: stdin
    payload (prompt, session_id). Output: hook JSON, or nothing. Side
    effects: records the announced stage.
    """
    data = read_stdin_json()
    prompt, sid = data.get("prompt"), data.get("session_id")
    if not isinstance(prompt, str) or not isinstance(sid, str) or not sid:
        return
    stage = detect_stage(prompt)
    if stage is None:
        return
    if stage["stage"] in announced(sid):
        return
    set_stage(sid, stage["stage"])
    emit("UserPromptSubmit", stage_message(stage))


def main(argv):
    """Dispatch on the mode flag; swallow every error.

    Why: a reminder must never break a session. Inputs: argv. Output: hook
    JSON or nothing; exit code always 0. Side effects: see the modes.
    """
    mode = argv[1] if len(argv) > 1 else ""
    try:
        if mode == "--session-start":
            session_start()
        elif mode == "--prompt":
            prompt_mode()
    except Exception:
        if mode == "--session-start":
            emit("SessionStart", FALLBACK_BRIEF)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
