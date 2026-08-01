---
name: deploy
description: Deploy MacroMic to the Proxmox host — the prod compose sequence and the restart rules that are not obvious
disable-model-invocation: true
---

# Deploy to production

Production is a Dell Wyse thin client at home: Proxmox VE, Docker inside an unprivileged
LXC, the repo cloned on that host and brought up with `docker-compose.prod.yml`. Caddy
terminates TLS, three `hetzner-ddns` containers keep the A records pointed at a dynamic
home IP.

**These commands run on the Proxmox host, not here.** Claude has no shell there — this
skill is the checklist to follow (or to hand to Marvin) once the code is on `master`.
Per `scripts/README.md` the repo lives at `/root/nutrition-tracker`; confirm before
assuming.

## 1. Before anything leaves the machine

```bash
python3 -m pytest -q --ignore=tests/test_rate_limit_page.py --ignore=tests/test_register_form.py
```

The two ignored files need `httpx`, which the local Python 3.9 does not have. To run the
whole suite, use the container — the image has httpx but not pytest, so it needs a
one-off install:

```bash
docker exec nutrition-tracker-api-1 pip install -q pytest pytest-asyncio
docker exec -w /app nutrition-tracker-api-1 python -m pytest -q
```

Push to `master`. Deploys pull from there; there is no CI.

## 2. On the host

```bash
cd /root/nutrition-tracker
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

`up -d --build` recreates the `api` container, which is what makes new code and any
`.env` change take effect.

## 3. The restart rules — these are the ones that bite

Three different mechanisms, three different fixes. Getting one wrong looks like a deploy
that silently did nothing.

- **`.env` changed → `up -d`, never `restart`.** A container's environment is frozen at
  creation. `restart` reuses it and the old values survive. Settings are also read at
  import time, so even inside the container nothing re-reads the file.
- **`Caddyfile` changed → `docker compose -f docker-compose.prod.yml restart caddy`.**
  Caddy does not hot-reload its bind-mounted config, and `up -d` will not recreate the
  `caddy` service when its image, env and ports are unchanged — so nothing happens
  unless the restart is explicit.
- **Schema change → nothing extra.** `init_db()` runs the migrations at boot, so the
  recreate in step 2 applies them. Watch the logs to confirm (step 4).

## 4. Verify

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=40 api
```

The app warns at boot about exactly the misconfigurations that are otherwise silent —
open signup, a missing Resend key, an unverified `EMAIL_FROM`, a `PUBLIC_BASE_URL` still
pointing at localhost. Read those warnings; they are there because each one fails
quietly in production.

Then from outside the network: `https://app.macromic.de/login` should answer 200,
`https://macromic.de/` should serve the landing page, and any other path on the bare
domain should 302 to `app.`.

## 5. Prod `.env` values worth re-checking

Not verified as set on the host — confirm before assuming, and never paste the values
into a transcript.

| Variable | Should be | Why |
|---|---|---|
| `WHISPER_PROVIDER` | `openai` | The only provider the image can run; `torch` is not installed. |
| `PUBLIC_BASE_URL` | `https://app.macromic.de` | Otherwise links in outgoing mail are unreachable. |
| `COOKIE_SECURE` | `true` | Session cookie over HTTPS only. |
| `TRUSTED_PROXY_HOPS` | `1` | Caddy sits in front; at `0` the real client IP is ignored, so rate limits count the proxy. |
| `SIGNUP_CODE` | set | Empty means anyone can register and spend credits. |

## Rollback

Images are rebuilt from the checkout, so rolling back is a git operation plus a rebuild:

```bash
git log --oneline -5
git checkout <last-good-sha>
docker compose -f docker-compose.prod.yml up -d --build
```

The `macromic_data` volume is untouched by this — but a rollback across a schema
migration does not undo the migration. Added columns stay. That is usually harmless
(older code ignores them); a backfill that rewrote existing rows is not recoverable this
way, and the backup is the only route back.

## Backups

`scripts/backup.sh` runs from the host's crontab at 03:00: a WAL-safe `sqlite3 .backup`
off the volume mountpoint, 7 days of local rotation, `rclone` to Proton Drive. Before a
migration that rewrites existing rows, take one by hand first:

```bash
/root/nutrition-tracker/scripts/backup.sh
```
