"""Synthetic transcripts. Nothing here is real: invented paths, prompts and titles."""
import json, os, uuid

def line(type_, ts, cwd, sid, text=None, **extra):
    d = {"type": type_, "timestamp": ts, "cwd": cwd, "sessionId": sid,
         "isSidechain": False, "uuid": str(uuid.uuid4())}
    if type_ == "user":
        d["message"] = {"role": "user", "content": text if text is not None else "do the thing"}
    elif type_ == "assistant":
        d["message"] = {"role": "assistant", "content": [{"type": "text", "text": text or "done"}]}
    d.update(extra)
    return d

def session(root, slug, sid, cwd, stamps, title=None, first_prompt="build the login page", extra_lines=()):
    """stamps: ISO strings; the first is a user prompt, then alternate assistant/user.
    Later user lines are tool results (as in real transcripts), so they are not requests."""
    os.makedirs(os.path.join(root, slug), exist_ok=True)
    rows = []
    tool_result = [{"type": "tool_result", "tool_use_id": "toolu_x", "content": "ok"}]
    for i, ts in enumerate(stamps):
        t = "user" if i % 2 == 0 else "assistant"
        rows.append(line(t, ts, cwd, sid, first_prompt if i == 0 else (tool_result if t == "user" else None)))
    if title:
        rows.append({"type": "ai-title", "aiTitle": title, "sessionId": sid})
    rows.extend(extra_lines)
    path = os.path.join(root, slug, sid + ".jsonl")
    with open(path, "w") as fh:
        for r in rows:
            fh.write((r if isinstance(r, str) else json.dumps(r)) + "\n")
    return path
