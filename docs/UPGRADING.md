# Update, backup and recovery / Nâng cấp

## From 2.0.7

Stop the existing consumer and back up the database, config, environment and persona.
Keep the SQLite backup consistent; copying only `kei.db` while it has an active WAL
is not a reliable live backup. The migration command uses SQLite's backup API.

```sh
python -m pip install -e .
keys-keys migrate --config kei.yaml
keys-keys doctor --config kei.yaml
keys-keys run --config kei.yaml
```

Schema 3 adds tables and preserves legacy messages, assignments, task checkpoints,
preferences and audit. It does not fill or publish the maintainer's persona.
Existing Wings+SSH profiles are normalized into independent connectors.

For Docker, the new compose file mounts `data/` only. Before replacing a 2.x compose
deployment, run setup into a private new config or deliberately preserve its old
config/env/persona/known_hosts mounts in `compose.override.yaml`. Do not drop your
old mounts and assume the container can still see the files.

## Routine update

1. Back up `data/` and stop the bot when no mutation is running.
2. Pull the intended tag/commit, read CHANGELOG, rebuild and run doctor.
3. Start one consumer. Confirm the reported version and actual server capabilities.
4. For plugin updates, replace the JAR and restart Minecraft normally.

```sh
docker compose stop keys-keys
git pull --ff-only
docker compose build
docker compose run --rm keys-keys doctor
docker compose up -d
```

If Git reports local edits to tracked blank persona placeholders, preserve those private
files first. New wizard installs avoid that problem by writing persona under `data/`.

## Rollback

Keep the previous source/tag/image and pre-migration DB/config backup. Stop the consumer
before restoring them. A rollback to an old snapshot discards newer state, so export or
preserve post-cutover data first. Never restart an uncertain mutation merely because
you restored a program version.
