# Runbook — Traefik HTTP security headers (Dokploy)

How the four HTTP security headers reach the EPSCAxplor prod hosts, and how to re-apply them
if Dokploy regenerates its router config.

Supersedes #146, whose header labels never deployed: Dokploy (Docker Swarm) ignores compose
`traefik.*` labels — routing/TLS/middlewares come from Dokploy's per-service **Domains UI**,
which writes generated dynamic config under `/etc/dokploy/traefik/dynamic/`.

**Delivered live 2026-07-27** on `epscaxplor.com`, `www.epscaxplor.com`, `api.epscaxplor.com`.

## Headers delivered (#146 values)

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (no `preload`) |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `X-Frame-Options` | `DENY` |

`X-Frame-Options: DENY` is kept forward-consistent with the planned CSP `frame-ancestors 'none'`
(#156). CSP itself is out of scope here.

## Mechanism

- The middleware **definition** lives in the persistent, hand-edited
  `/etc/dokploy/traefik/dynamic/middlewares.yml` (root-owned; Dokploy never regenerates it —
  it already holds `redirect-to-https`, `ollama-auth`, etc.).
- The **attachment** is a bare-name middleware reference on each host's `websecure` router.
  Those routers live in Dokploy-**generated** files (rewritten on Domains-UI edits):
  - `epscaxplor-epscaweb-hmu07k.yml` — `...-router-websecure-16` (`epscaxplor.com`),
    `...-router-websecure-17` (`www.epscaxplor.com`)
  - `epscaxplor-epscaapi-ixh0v2.yml` — `...-router-websecure-15` (`api.epscaxplor.com`)
- Traefik's file provider watches the directory, so edits hot-reload (no restart).
  **⚠️ A YAML error in ANY dynamic file makes Traefik reject that entire reload and silently
  keep the last-good config** — so a malformed edit disables *both* the definition and the
  attach, with no 404 and no headers. Always validate against the logs after editing
  (Troubleshooting) rather than trusting the header check alone.
- **Scope:** attach only to the three EPSCAxplor routers. Never make this an entryPoint default
  — the `websecure` entrypoint is shared by unrelated sites on this VPS.

All steps below run on the VPS (`ssh boiler@149.202.56.68`) and need `sudo` (root-owned files).

## 1. Define the middleware — one-time (`middlewares.yml` is durable, never regenerated)

Add this block under `http.middlewares:`, as a sibling of `redirect-to-https` (4-space indent
for `epsca-secheaders:`, 6 for `headers:`, 8 for each key):

```yaml
    epsca-secheaders:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        contentTypeNosniff: true
        referrerPolicy: strict-origin-when-cross-origin
        customFrameOptionsValue: DENY
```

> **⚠️ Paste gotcha (this bit us during rollout):** in a nano/vi paste, the last line
> (`customFrameOptionsValue: DENY`) can weld onto the following key
> (`...DENY    ollama-auth:`), producing `yaml: mapping values are not allowed in this
> context`. Ensure `DENY` sits on its own line with a newline before the next key. **Validate
> immediately** (step 3) before relying on it.

```bash
sudo cp /etc/dokploy/traefik/dynamic/middlewares.yml{,.bak-159}
sudo nano /etc/dokploy/traefik/dynamic/middlewares.yml   # add the block above
```

## 2. Attach / re-attach to the websecure routers

> **⚠️ Re-attach trigger:** the generated router files are reset to `middlewares: []` whenever a
> domain is **added / removed / edited** in the Dokploy Domains UI for these apps. Ordinary
> redeploys do NOT touch them. After any such Domains-UI change, redo this step.
> Suffixes (`-hmu07k`, `-ixh0v2`) can change on regeneration — locate with
> `grep -rl epscaxplor /etc/dokploy/traefik/dynamic/`.

Every `middlewares: []` in these two files is a `websecure` router (the `:80` routers use the
`redirect-to-https` block form), so this hits exactly the three and leaves the redirects alone:

```bash
sudo cp /etc/dokploy/traefik/dynamic/epscaxplor-epscaweb-hmu07k.yml{,.bak-159}
sudo cp /etc/dokploy/traefik/dynamic/epscaxplor-epscaapi-ixh0v2.yml{,.bak-159}

sudo sed -i 's/middlewares: \[\]/middlewares: [epsca-secheaders]/' \
  /etc/dokploy/traefik/dynamic/epscaxplor-epscaweb-hmu07k.yml \
  /etc/dokploy/traefik/dynamic/epscaxplor-epscaapi-ixh0v2.yml

# confirm: 3x `middlewares: [epsca-secheaders]`, redirect-to-https blocks untouched
grep -n 'middlewares:' \
  /etc/dokploy/traefik/dynamic/epscaxplor-epscaweb-hmu07k.yml \
  /etc/dokploy/traefik/dynamic/epscaxplor-epscaapi-ixh0v2.yml
```

## 3. Validate + verify

First confirm Traefik accepted the reload (this is the authoritative validation — headers can
be absent purely because Traefik rejected a malformed file):

```bash
sudo docker logs dokploy-traefik --since 2m 2>&1 | grep -iE 'error|middlewar' || echo "clean — no reload errors"
```

Then check the headers. The watcher reloads within ~a second; **re-run if the first host misses
(reload race — the first curl can beat the reload)**:

```bash
for url in https://epscaxplor.com https://www.epscaxplor.com https://api.epscaxplor.com/health; do
  echo "=== $url ==="
  curl -sS -o /dev/null -D - "$url" | grep -iE '^(strict-transport-security|x-content-type-options|referrer-policy|x-frame-options):'
done
```

Each host must return all four headers. Then confirm nothing broke:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://api.epscaxplor.com/docs   # expect 200
curl -sS -o /dev/null -w '%{http_code}\n' https://epscaxplor.com            # expect 200
```

Load the web app in a browser to confirm `X-Frame-Options: DENY` didn't break rendering.

## Troubleshooting

- **Headers absent on ALL hosts after an edit** → almost always a YAML error in
  `middlewares.yml` (Traefik rejected the whole reload, kept last-good). The log line
  `middlewares.yml: yaml: line N: mapping values are not allowed in this context` points at the
  bad line — usually a merged/mis-indented line. Fix it (or restore `middlewares.yml.bak-159`)
  and re-verify.
- **Headers absent on ONE host only** → usually the reload race; re-run the verify loop. If it
  persists, confirm that host's `websecure` router shows `middlewares: [epsca-secheaders]`.
- **Force a reload** (last resort; briefly blips every site on the box):
  `sudo docker restart dokploy-traefik`.
- **Rollback:** restore the `.bak-159` copies and `sudo docker restart dokploy-traefik`.
