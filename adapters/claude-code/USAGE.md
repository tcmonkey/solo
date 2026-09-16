# Claude Code adapter

Install after Claude Code is available:

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform claude-code
```

Start Claude Code in the target repository and invoke:

```text
/solo
```

With no arguments, a new project starts in auto-selected delivery mode plus `guided`; a project with `.ai-delivery/state.json` continues from saved state. Add the requirement or target phase in the same message when known.

The shared skill follows Claude Code's active project instructions, persists machine state under `.ai-delivery/`, and writes Chinese-named Markdown documents under `AI/output/`.
