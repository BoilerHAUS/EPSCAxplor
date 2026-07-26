# Runbook — Traefik HTTP security headers (Dokploy)

How the four HTTP security headers reach the EPSCAxplor prod hosts, and how to re-apply
them if Dokploy regenerates its router config.

Supersedes #146, whose header labels never deployed: Dokploy (Docker Swarm) ignores compose
`traefik.*` labels — routing/TLS/middlewares come from Dokploy's per-service **Domains UI**,
which writes generated dynamic config under `/etc/dokploy/traefik/dynamic/`.

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
  Those routers live in Dokploy-**generated** files (regenerated on Domains-UI edits):
  - `epscaxplor-epscaweb-hmu07k.yml` — `...-router-websecure-16` (`epscaxplor.com`),
    `...-router-websecure-17` (`www.epscaxplor.com`)
  - `epscaxplor-epscaapi-ixh0v2.yml` — `...-router-websecure-15` (`api.epscaxplor.com`)
- Traefik's file provider watches the directory, so edits hot-reload (no restart). Fallback:
  `sudo docker restart dokploy-traefik` (briefly blips **every** site on the box).
- **Scope:** attach only to the three EPSCAxplor routers. Never make this an entryPoint
  default — the `websecure` entrypoint is shared by unrelated sites on this VPS.

## Definition (add to `middlewares.yml`, sibling of `redirect-to-https`)

```yaml
    epsca-secheaders:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        contentTypeNosniff: true
        referrerPolicy: strict-origin-when-cross-origin
        customFrameOptionsValue: DENY
```

## Attach / re-attach (VPS — `ssh boiler@149.202.56.68`, interactive sudo)

> **⚠️ Re-attach trigger:** the generated router files are reset to `middlewares: []` whenever
> a domain is **added / removed / edited** in the Dokploy Domains UI for these apps. Ordinary
> redeploys do NOT touch them. After any Domains-UI change to `epscaxplor.com` /
> `www.epscaxplor.com` / `api.epscaxplor.com`, redo steps 2–3.
> The filename suffixes (`-hmu07k`, `-ixh0v2`) can change on regeneration — locate with
> `grep -rl epscaxplor /etc/dokploy/traefik/dynamic/`.

```bash
# 0. back up before editing
sudo cp /etc/dokploy/traefik/dynamic/middlewares.yml{,.bak-159}
sudo cp /etc/dokploy/traefik/dynamic/epscaxplor-epscaweb-hmu07k.yml{,.bak-159}
sudo cp /etc/dokploy/traefik/dynamic/epscaxplor-epscaapi-ixh0v2.yml{,.bak-159}

# 1. (first time only) define the middleware
sudo nano /etc/dokploy/traefik/dynamic/middlewares.yml            # add the epsca-secheaders block

# 2. attach on web routers: middlewares: [] -> middlewares: [epsca-secheaders] on -websecure-16 AND -17
sudo nano /etc/dokploy/traefik/dynamic/epscaxplor-epscaweb-hmu07k.yml

# 3. attach on api router: middlewares: [] -> middlewares: [epsca-secheaders] on -websecure-15
sudo nano /etc/dokploy/traefik/dynamic/epscaxplor-epscaapi-ixh0v2.yml
```

## Verify

```bash
for url in https://epscaxplor.com https://www.epscaxplor.com https://api.epscaxplor.com/health; do
  echo "=== $url ==="
  curl -sSI "$url" | grep -iE '^(strict-transport-security|x-content-type-options|referrer-policy|x-frame-options):'
done
```

Each host must return all four headers. Then confirm nothing broke:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://api.epscaxplor.com/docs   # expect 200
curl -sS -o /dev/null -w '%{http_code}\n' https://epscaxplor.com            # expect 200
```

Load the web app in a browser to confirm `X-Frame-Options: DENY` didn't break rendering.
Rollback: restore the `.bak-159` copies and `sudo docker restart dokploy-traefik`.
