# Working on keys-keys

- This is the canonical repository for future builds. Work here rather than exporting another disconnected source snapshot.
- Public builds/changes: update the version and CHANGELOG, validate, then commit and push only within the user-approved public scope.
- Keep experimental/local-only features outside this public checkout. Do not publish their code, documentation, tags or releases until the user explicitly approves publication. Authorization to build or deploy locally is not authorization to publish.
- Keep runtime VERSION, package __version__, pyproject, compose image label and README version badge consistent. Patch bumps cover fixes/packaging; document behavior changes.
- Never commit .env, kei.yaml, known_hosts, databases, logs, private deployment notes or host credentials.
- Public personalization prompts and .env.example must remain empty. Runtime configuration/persona and operator-specific tests belong in ignored local files. Check staged prompt files before every commit: ignore rules do not protect already tracked files.
- Public tests contain explicitly reviewed synthetic offline regressions. Keep their .gitignore exceptions current; never transplant private operator fixtures or cite private test totals as public acceptance.
- Keep README bilingual, practical and readable. Architecture name: Supernova. Project name: keys-keys. Avoid research-paper language and inflated capability claims.
