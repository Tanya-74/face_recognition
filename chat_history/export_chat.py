"""Turn a Claude Code session file (.jsonl) into a readable Markdown chat history.

This is how the files next to this script were made, so a reviewer can see the export is mechanical.
    python export_chat.py <session.jsonl> <output.md> "<title>"

What is kept, in full:   every message the user typed (also those sent while Claude was working),
                         every reply Claude wrote, and the questions Claude asked with the user's answers.
What is shortened:       tool calls (running a command, editing a file) become one line each; their output is left out.
What is left out:        hidden reasoning, system/harness notices, screenshots (marked as "screenshot attached"),
                         and the automatic summary Claude Code writes when a long session runs out of room.
What is redacted:        the user's e-mail address and the user name inside Windows paths.
"""
import json
import os
import re
import sys


def redact(s):
    s = re.sub(r"[A-Za-z0-9._%+-]+@gmail\.com", "[email redacted]", s)
    for term in os.environ.get("CHAT_REDACT", "").split(","):    # extra words to hide, e.g. CHAT_REDACT=part-of-the-address
        if term.strip():
            s = re.sub(re.escape(term.strip()) + r"\w*", "[redacted]", s)
    s = re.sub(r"Users(\\\\+|\\|/+)tanya", lambda m: "Users" + m.group(1) + "<user>", s)
    s = s.replace("Users-tanya", "Users-<user>")
    return s


def blocks(o):
    c = (o.get("message") or {}).get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return [b for b in (c or []) if isinstance(b, dict)]


def clean_user_text(t):
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S)
    t = re.sub(r"<ide_opened_file>.*?</ide_opened_file>", "", t, flags=re.S)
    t = re.sub(r"<ide_selection>.*?</ide_selection>", "", t, flags=re.S)
    t = re.sub(r"<local-command-caveat>.*?</local-command-caveat>", "", t, flags=re.S)
    t = re.sub(r"<local-command-stdout>.*?</local-command-stdout>", "", t, flags=re.S)
    t = re.sub(r"<command-(name|message|args)>.*?</command-\1>", "", t, flags=re.S)
    t = re.sub(r"</?pasted_content[^>]*>", "", t)
    t = t.strip()
    if re.fullmatch(r"(\[Image: [^\]]*\]\s*)+", t):
        return "*(screenshot attached)*"
    t = re.sub(r"\[Image: [^\]]*\]", "*(screenshot attached)*", t)
    if t.startswith("This session is being continued from a previous conversation"):
        return "*(automatic summary written by Claude Code when the conversation ran out of room; left out)*"
    return t


def tool_line(b):
    name, inp = b.get("name", "tool"), b.get("input") or {}
    if name in ("Write", "Edit", "Read", "NotebookEdit"):
        return f"{name} `{inp.get('file_path', '')}`"
    if name in ("Bash", "PowerShell"):
        d = inp.get("description") or (inp.get("command", "").strip().splitlines() or [""])[0]
        return f"{name}: {d[:150]}"
    if name == "Agent":
        return f"Agent: {inp.get('description', '')}"
    if name in ("Glob", "Grep"):
        return f"{name}: {inp.get('pattern', '')}"
    return name


def ask_question_md(b):
    out = []
    for q in (b.get("input") or {}).get("questions", []):
        out.append(f"**Claude asked:** {q.get('question', '')}")
        for opt in q.get("options", []):
            out.append(f"- *{opt.get('label', '')}*: {opt.get('description', '')}")
    return "\n".join(out)


def main(src, dst, title):
    rows = []
    for line in open(src, encoding="utf-8"):
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    events = []                      # (timestamp, kind, text)
    ask_ids = set()
    pending_tools = []
    last_user = None

    def flush_tools(ts):
        if pending_tools:
            events.append((ts, "tools", list(pending_tools)))
            pending_tools.clear()

    for o in rows:
        t, ts = o.get("type"), (o.get("timestamp") or "")[:16].replace("T", " ")
        if t == "user":
            bs = blocks(o)
            results = [b for b in bs if b.get("type") == "tool_result"]
            if results:
                for b in results:
                    if b.get("tool_use_id") in ask_ids:
                        c = b.get("content")
                        c = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                        c = c.replace("You can now continue with these answers in mind.", "").strip()
                        flush_tools(ts)
                        events.append((ts, "you", c))
                continue
            text = clean_user_text("\n".join(b.get("text", "") for b in bs if b.get("type") == "text"))
            if text and text != last_user:
                flush_tools(ts)
                events.append((ts, "you", text))
                last_user = text
        elif t == "attachment":
            a = o.get("attachment") or {}
            if a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human":
                p = a.get("prompt")
                p = p if isinstance(p, str) else "\n".join(x.get("text", "") for x in p if isinstance(x, dict))
                text = clean_user_text(p)
                if text and text != last_user:
                    flush_tools(ts)
                    events.append((ts, "you", text + "\n\n*(sent while Claude was still working)*"))
                    last_user = text
        elif t == "assistant":
            for b in blocks(o):
                if b.get("type") == "text" and b.get("text", "").strip():
                    flush_tools(ts)
                    events.append((ts, "claude", b["text"].strip()))
                elif b.get("type") == "tool_use":
                    if b.get("name") == "AskUserQuestion":
                        ask_ids.add(b.get("id"))
                        flush_tools(ts)
                        events.append((ts, "claude", ask_question_md(b)))
                    else:
                        pending_tools.append(tool_line(b))
    flush_tools("")

    out = [f"# {title}", "",
           "Exported from a Claude Code session (VS Code extension). See `README.md` in this folder for what is kept, shortened and left out.",
           f"Messages: {sum(1 for e in events if e[1] == 'you')} from the user, {sum(1 for e in events if e[1] == 'claude')} from Claude. Times are UTC.", ""]
    for ts, kind, text in events:
        if kind == "tools":
            out.append(f"<details><summary>{len(text)} tool call(s)</summary>\n")
            out.extend(f"- {x}" for x in text)
            out.append("\n</details>\n")
        else:
            who = "You" if kind == "you" else "Claude"
            out.append(f"## [{ts} UTC] {who}\n")
            out.append(text if kind == "claude" else "\n".join("> " + ln if ln.strip() else ">" for ln in text.splitlines()))
            out.append("")
    open(dst, "w", encoding="utf-8").write(redact("\n".join(out)) + "\n")
    print(dst, "->", sum(1 for e in events if e[1] == "you"), "user msgs,", sum(1 for e in events if e[1] == "claude"), "Claude msgs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Chat history")
