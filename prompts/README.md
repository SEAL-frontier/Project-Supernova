# Bring your own personality

The four `.md` prompt files are intentionally zero bytes in the public repository. Fill `persona.md` locally; optionally fill `persona-auto.md`, `persona-soft.md`, and `persona-spicy.md` for `/persona` modes. An empty mode file falls back to your base `persona.md`.

Write the voice, language/addressing, roleplay boundaries, how teasing should work, and how to respond to emotional or serious situations. The experiment's built-in reply/UI language currently defaults to Vietnamese; the agent's operational contracts are implemented in code, not in these blank customization files.

The backend owns assignment checks, confirmation and verification. A personality prompt does not grant server access. If you enable playful refusal, it must keep new nonurgent work unexecuted, let a polite request resume it, and never block emergencies or ongoing work.

For a local private deployment, mark filled prompt files skip-worktree after editing:

```sh
git update-index --skip-worktree prompts/persona.md prompts/persona-auto.md prompts/persona-soft.md prompts/persona-spicy.md
```

Check staged files before pushing; `.gitignore` cannot hide changes to an already tracked placeholder.
