# Working on keys-keys

- This is the canonical repository for future builds. Work here rather than exporting another disconnected source snapshot.
- For user-authorized builds/changes, update the version and CHANGELOG, validate the change, commit and push to origin unless the user explicitly says otherwise.
- Keep runtime VERSION, package __version__, pyproject, compose image label and README version badge consistent. Patch bumps cover fixes/packaging; document behavior changes.
- Never commit .env, kei.yaml, known_hosts, databases, logs, private deployment notes or host credentials.
- Public personalization prompts and .env.example must remain empty. Runtime configuration/persona and operator-specific tests belong in ignored local files. Check staged prompt files before every commit: ignore rules do not protect already tracked files.
- Public tests intentionally contain only a blank placeholder. Do not advertise an empty test suite as passing or transplant private tests without explicit user approval.
- Keep README bilingual, practical and readable. Architecture name: Supernova. Project name: keys-keys. Avoid research-paper language and inflated capability claims.
