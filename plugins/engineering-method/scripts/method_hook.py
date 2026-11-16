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
                    different from the last one announced in this session,
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

STAGES = [
    {"stage": "plan",
     "words": ["plan", "plans", "planning", "planned", "design", "designs", "designing",
               "designed", "spec", "specs"],
     "skill": "superpowers:writing-plans",
     "references": ["docs-and-decisions.md", "parallel-and-worktrees.md"]},
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
               "verify", "verifies", "verifying", "verified"],
     "skill": "superpowers:verification-before-completion",
     "references": ["measurement-and-state-claims.md", "behaviour-evals.md"]},
    {"stage": "deploy",
     "words": ["deploy", "deploys", "deploying", "deployed", "rollout", "rollouts",
               "rollback", "rollbacks", "restart", "restarts", "restarting", "restarted",
               "migrate", "migrates", "migrating", "migrated"],
     "skill": None,
     "references": ["live-system-changes.md"]},
    {"stage": "merge",
     "words": ["merge", "merges", "merging", "merged", "push", "pushes", "pushing", "pushed"],
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

# word -> stage lookup, derived from STAGES (never edited by hand)
_WORD_TO_STAGE = {w: s for s in STAGES for w in s["words"]}
_WORD_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")


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
    Inputs: none. Output: {session_id: {"stage", "at"}}; {} if missing or
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


def set_stage(session_id, stage):
    """Remember (or forget, when stage is None) the last stage announced.

    Why: speaking only on a change keeps the reminder from becoming noise.
    Inputs: session id, stage name or None. Output: none. Side effects:
    rewrites the state file.
    """
    state = load_state()
    if stage is None:
        state.pop(session_id, None)
    else:
        state[session_id] = {"stage": stage, "at": time.time()}
    save_state(state)


def detect_stage(prompt):
    """Find the stage of the earliest stage word in a prompt.

    Why: the first verb usually names the work being asked for. A leading
    slash-command token is skipped, so "/plan-layer status" is not "plan".
    Matching is whole-word and case-insensitive over an explicit word list.
    Inputs: prompt text. Output: a STAGES entry, or None. Side effects: none.
    """
    text = prompt.lstrip()
    if text.startswith("/"):
        parts = text.split(None, 1)
        text = parts[1] if len(parts) > 1 else ""
    for m in _WORD_RE.finditer(text):
        stage = _WORD_TO_STAGE.get(m.group(0).lower())
        if stage:
            return stage
    return None


def stage_message(stage):
    """Compose the short per-stage reminder (at most 400 characters).

    Why: it names exactly what to load, nothing more. Inputs: a STAGES
    entry. Output: text. Side effects: none.
    """
    skill = "load %s and " % stage["skill"] if stage["skill"] else ""
    refs = ", ".join("references/" + r for r in stage["references"])
    return ("engineering-method: stage %s — %sread %s before acting; "
            "keep the stakes tier you named." % (stage["stage"], skill, refs))[:400]


def session_brief(source):
    """Compose the session brief (at most 1,500 characters).

    Why: startup, /clear and compaction all lose the method; this restores
    its shape. Inputs: the SessionStart source. Output: text. Side effects:
    none.
    """
    stages = "; ".join("%s -> %s -> %s" % (s["stage"], s["skill"] or "-",
                                           ", ".join(s["references"])) for s in STAGES)
    lines = [
        "engineering-method is active in this session.",
        "First name the stakes tier: (a) exploration: throwaway, keep it light; "
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
    last = load_state().get(sid, {}).get("stage")
    if last == stage["stage"]:
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
