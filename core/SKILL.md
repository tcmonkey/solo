---
name: solo
description: "Guide one developer through a persistent, stage-gated delivery workflow from mixed inputs to requirements, product and technical designs, development with developer self-testing, code review, independent testing, release, and retrospective. 用于从零开始、继续或修改端到端软件项目交付；孤立的编码问答不自动使用。"
---

# Solo

Turn a project idea and its supporting materials into a traceable, reviewable implementation. Preserve the user's business decisions and existing repository conventions. Keep progress in the target project so the workflow can resume across sessions, agent runtimes, and model providers.

## Default invocation

When the user invokes this skill without additional instructions:

- if the target project contains `.ai-delivery/state.json`, continue from its next unfinished or requested phase;
- otherwise initialize a new delivery using an automatically selected Lite, Standard, or Full mode and `guided` interaction;
- if the target project or requirement input is missing, ask one concise consolidated question for it;
- start with intake and requirements understanding, then stop at the scope gate before product design or implementation.

## Locate or initialize the delivery workspace

1. Resolve the target project root from the user's path or current working directory. Never treat this skill's own directory as the target project unless explicitly requested.
2. Read [references/运行环境规范.md](references/运行环境规范.md), identify the host and model when known, and detect the capabilities needed for the current phase before relying on them.
3. Read the active host's project instructions and precedence rules, repository documentation, build configuration, and existing `.ai-delivery/state.json` before acting.
4. If `.ai-delivery/state.json` exists with a template version older than `0.7.0`, migrate it when Python execution is available:

   ```bash
   python3 <skill-dir>/scripts/migrate_project.py --project <project-root>
   ```

   Without Python, preserve an export or backup of the existing state, apply the `0.7.0` fields from `assets/state.json` and `assets/project-profile.yaml`, move human-readable artifacts to `AI/output` with the numbered Chinese filenames defined in `assets/`, move the input manifest to `AI/input/00 输入材料清单.md`, increment the revision once, and append a migration entry to `AI/output/18 交接记录.md` before continuing. When migrating versions before `0.4.0`, also replace `implementation` with `development`, split `verification` into `code_review` and `testing`, and treat completed combined verification as `stale` until separated evidence is reviewed.

5. If `.ai-delivery/` is absent, read [references/交付流程规范.md](references/交付流程规范.md), select Lite, Standard, or Full, and initialize it. When Python execution is available, run:

   ```bash
   python3 <skill-dir>/scripts/init_project.py --project <project-root> --mode <lite|standard|full> --interaction <guided|continuous>
   ```

   Pass `--platform`, `--model`, and known `--capability key=value` arguments. If Python is unavailable but the host has a writable filesystem, create the same structure from `assets/` and record that scripted initialization was unavailable. If persistent files are unavailable, produce exportable artifacts and state rather than claiming they were saved.
6. Ingest the user's text, images, local files, URLs, and available connected documents. Store or link user-provided materials under `AI/input/` and record each source in `AI/input/00 输入材料清单.md`; link large files rather than copying them unless the user wants a local snapshot. Store generated human-readable Markdown under `AI/output/` using the numbered filenames defined in `assets/`. Keep `.ai-delivery/` for machine state and configuration only.
7. Separate supplied facts, repo-observed facts, assumptions, conflicts, and unanswered questions. Never silently convert an assumption into a requirement.
8. Before any stateful change, reload `.ai-delivery/state.json`, note its `revision`, and read the latest entry in `AI/output/18 交接记录.md`.

## Operate by intent

- **Start / 初始化**: initialize state, assess complexity, inspect inputs, and produce an intake summary.
- **Continue / 继续**: load state and proceed from the next unfinished or requested phase.
- **Status / 状态**: report current phase, approvals, missing inputs, risks, and next action without changing artifacts.
- **Revise / 修改**: update the named artifact, mark affected downstream artifacts stale, and show impact.
- **Skip / 跳过**: skip an optional phase only; record the reason in `AI/output/15 决策记录.md`.
- **Validate / 检查**: run the validator and relevant repository checks, then report evidence.
- **Handoff / 交接**: summarize completed work, changed artifacts, unresolved risks, and the exact next action for another agent runtime.

If the user's instruction names a phase or endpoint, honor it. Otherwise use the configured interaction mode.

## Execute phases

Use only the reference for the current phase plus `交付流程规范.md`:

1. Intake and requirements: read [references/需求阶段规范.md](references/需求阶段规范.md).
2. Product solution: read [references/产品阶段规范.md](references/产品阶段规范.md).
3. UI/UX when enabled: read [references/界面设计阶段规范.md](references/界面设计阶段规范.md).
4. Technical design and plan: read [references/技术方案阶段规范.md](references/技术方案阶段规范.md).
5. Development and developer self-testing: read [references/开发阶段规范.md](references/开发阶段规范.md).
6. Code review: read [references/代码审查阶段规范.md](references/代码审查阶段规范.md).
7. Independent testing: read [references/测试阶段规范.md](references/测试阶段规范.md).
8. Release and learning: read [references/发布与复盘阶段规范.md](references/发布与复盘阶段规范.md).

At every phase:

- For projects adopting the Java DDD reference template, the consolidated [Java DDD开发规范](references/Java%20DDD开发规范.md) is the current rule source. Technical/development references route installation of the project's own Checkstyle/Maven gate before coding; do not infer new rules from superseded historical project decisions or apply the template to unrelated stacks.
- The Java DDD implementation examples are bundled in `assets/java-ddd/reference-project/`; technical planning and development references route task-specific reading. Use them as examples, not another rulebook, a production-ready scaffold or an absolute-path dependency on the original ddd project.
- cite input sources using stable labels such as `SRC-001`;
- assign stable IDs to requirements, decisions, tasks, interfaces, and tests;
- update `AI/output/14 交付追踪矩阵.md` rather than relying on prose memory;
- label unknown information `TBD` and place it in `AI/output/17 开放问题.md`;
- preserve existing user edits and avoid overwriting an approved artifact without noting the revision;
- validate the phase with `scripts/validate_delivery.py` when Python is available; otherwise perform the equivalent structural review and label scripted validation `not_run`.

After a state-changing turn, record the handoff with revision protection when Python is available:

```bash
python3 <skill-dir>/scripts/record_handoff.py \
  --project <project-root> --platform <platform> --model <model-or-unknown> \
  --phase <phase> --summary <short-summary> --next-action <next-action> \
  --expected-revision <revision-read-before-work>
```

If the expected revision no longer matches, another runtime changed the workflow. Reload the state and artifacts, reconcile the difference, and rerun the handoff command. Do not overwrite the newer state.

If the host cannot execute the handoff script, update `.ai-delivery/state.json` and `AI/output/18 交接记录.md` together, increment the revision exactly once, and disclose that process locking was unavailable.

## Gates and autonomy

In `guided` interaction mode, pause for user confirmation at scope, product, technical, development-ready, test-acceptance, and release gates. Present a concrete artifact and a short decision summary before asking. Consolidate questions that materially affect the result; do not ask the user to approve formatting or routine checks.

In `continuous` mode, proceed through authorized phases, using explicit assumptions for non-critical gaps. Still stop when a missing business decision would materially change scope, data, security, money movement, external communication, deployment, or destructive changes.

Approval of a technical design or an explicit request to implement authorizes repository edits and proportionate developer self-testing within that design. It does not authorize deployment, publishing, merging, production data changes, or external messages.

When an upstream artifact changes, mark dependent phases `stale` in `state.json`, list affected IDs, and revalidate them before development or release.

Do not let two agent runtimes edit the same project concurrently. Sequential handoffs may use different models or platforms because `.ai-delivery/` is the source of truth.

## Finish each response with a checkpoint

State:

- current phase and status;
- artifacts created or changed;
- important assumptions and unresolved questions;
- validation evidence;
- the exact next decision or action.

Do not claim completion when required checks did not run. Distinguish failures, unavailable checks, and checks that passed.

## Improve the templates safely

During retrospective, write proposed improvements to the target project's `AI/output/13 项目复盘.md`. Do not modify this skill automatically. Template changes require an explicit user request and should be supported by a concrete project failure, revision pattern, or measured improvement.
