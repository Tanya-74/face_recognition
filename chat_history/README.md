# Chat history

The full AI chat history for this project, starting from the very first prompt. All of it is Claude Code (VS Code extension)
sessions on the author's laptop. [../AI_COLLAB.md](../AI_COLLAB.md) points into these files as its evidence.

| File | When | What happens in it |
|---|---|---|
| [01_2026-11-22_project-setup-and-test-data.md](01_2026-11-22_project-setup-and-test-data.md) | 22 Nov 2026 | The first prompt. Project skeleton, git, `.gitignore`, then the public LFW photo set and the test data (50 known people, unknown people, 3 collage group photos). |
| [02_2026-11-23_to_24_research-app-and-ui.md](02_2026-11-23_to_24_research-app-and-ui.md) | 23-24 Nov 2026 | The long one. Comparing the four libraries, the plan change, choosing UniFace, the threshold evaluation, building the app, the diagram, the UI redesign (one screen, dark), the docs, merging, and the final checks. |
| [03_subagent_helper-agent.md](03_subagent_helper-agent.md) | 23 Nov 2026 | A small helper agent that chat 2 started to read the Archify install instructions. |

## What is in the exports

- **Kept in full:** every message the author typed (including the ones sent while Claude was still working), every reply Claude wrote,
  and the questions Claude asked with the author's answers.
- **Shortened:** tool calls (running a command, editing a file) are one line each, grouped in a folded "tool calls" block.
  Their output is not included.
- **Left out:** hidden reasoning, system and harness notices, screenshots (marked as "screenshot attached"), and the automatic
  summary Claude Code writes when a long conversation runs out of room. Chat 2 hit that limit once; the messages before and after it are all there.
- **Redacted:** the author's e-mail address and the user name inside Windows paths (shown as `<user>`). Nothing else was changed.
  A stray word in the author's first prompt ("Show" at the end) is in the original and was kept.

The exports are a snapshot taken while the last documents were being written, so the final exchanges about these files themselves come after it.

## Raw data

`claude_code/5cc35c47-cb5b-4b4e-b5c7-98a19bc354f3.jsonl` is the raw record of chat 1 (with the same two redactions).
The raw record of chat 2 is about 31 MB, mostly screenshots and internal records, so it is not committed; the author can show it at the demo.

## How the exports were made

`export_chat.py` in this folder turns a session file into the Markdown above:

```
python chat_history/export_chat.py <session.jsonl> <output.md> "<title>"
```

The session files live in `~/.claude/projects/<project folder>/` on the laptop. The script is short and only reads and re-formats;
it does not summarise or rewrite any message.
