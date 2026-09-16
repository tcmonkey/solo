# Codex adapter

Install:

```bash
python3 /Users/monkey/Documents/kit/workspace/solo/installers/install.py --platform codex
```

Invoke in a target project:

```text
$solo
```

With no arguments, a new project starts in auto-selected delivery mode plus `guided`; a project with `.ai-delivery/state.json` continues from saved state. Add the requirement or target phase in the same message when known.

Codex can also open `/skills` and select Solo. Codex UI metadata lives in `solo/solo/agents/openai.yaml`. All workflow content resolves to the shared `core/` directory; generated Markdown uses Chinese filenames under `AI/output/`.
