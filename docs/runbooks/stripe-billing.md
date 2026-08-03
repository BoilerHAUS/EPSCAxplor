# Runbook — Stripe subscription billing (#32)

How to configure, test, and deploy the billing integration, and what to check when a
subscription does not appear.

**Status: test mode.** No live keys exist. Going live is gated on #181 (GST/HST) for the tax
question and on the checklist in §6.

---

## 0. What the code does

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /billing/plans` | none | The purchasable plans + Price IDs. #33's pricing page reads this. |
| `POST /billing/checkout-session` | JWT / API key | Returns a hosted Stripe Checkout URL. |
| `POST /billing/portal-session` | JWT / API key | Returns a Billing Portal URL (cancel, card, invoices). |
| `POST /billing/webhook` | **Stripe signature** | Syncs subscription state into `subscriptions`. |

Populating `subscriptions` is what turns tier enforcement on: `enforce_tier_limit` (#25) reads that
table and fails open while it is empty. No enforcement code changed in #32; what a tenant gets once
its subscription ends was decided separately in #185 — see §9.

The tier a tenant receives is derived **server-side from the Stripe Price ID** via
`src/billing/plans.py`. A client never supplies a tier — `POST /billing/checkout-session` takes a
tier *name* only to choose which configured Price to send the buyer to.

---

## 1. Stripe Dashboard setup (test mode)

1. **Products → Add product**, one per self-serve tier:
   - *EPSCAxplor Individual* and *EPSCAxplor Professional*
   - Price: **recurring**, **monthly**, **CAD**
   - **Tax behaviour: EXCLUSIVE.** This is not reversible in a useful way — see §5.
2. Copy each **Price** ID (`price_…`, *not* the product's `prod_…`) into
   `STRIPE_PRICE_INDIVIDUAL` / `STRIPE_PRICE_PROFESSIONAL`.
3. **Do not** create an Enterprise price. Enterprise is manually invoiced (#35) with PO/net-30 or
   pre-authorized debit; the checkout route rejects it by construction.
4. **Developers → API keys.** Prefer a **restricted key** (`rk_test_…`) over the account secret
   key. Permissions needed: write on Checkout Sessions, Billing Portal Sessions, Customers,
   Subscriptions. Nothing else.
5. **Settings → Billing → Customer portal**: enable cancellation, payment-method update, and
   invoice history. The portal is unusable until this is configured once.
6. **Leave Stripe Tax off.** See §5.

## 2. Local development

```bash
# Terminal 1 — forward Stripe events to the local API
stripe login
stripe listen --forward-to localhost:8000/billing/webhook
# copy the printed whsec_… into STRIPE_WEBHOOK_SECRET

# Terminal 2 — run the API with billing configured
cd services/api && uvicorn src.main:app --reload
```

Trigger events without a real purchase:

```bash
stripe trigger customer.subscription.created
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
stripe trigger invoice.payment_failed
```

> `stripe trigger` builds a synthetic subscription on a throwaway Price, so the webhook will log
> `no known plan matched` and write nothing. That is correct behaviour, not a failure — an
> unrecognised Price must never be granted a tier. To exercise the real path, complete a Checkout
> with test card `4242 4242 4242 4242`.

## 3. Deploying to prod

Migrations are **not** run by deploys (see CLAUDE.md). Apply 011 and 012 by hand *before* the
first webhook arrives — the webhook writes columns that do not exist until then.

```bash
ssh boiler@149.202.56.68
# Reuse the API's DSN on dokploy-network (see docs/runbooks + the dokploy-ops notes)
docker run --rm -i --network dokploy-network -v /home/boiler/EPSCAxplor:/repo postgres:16-alpine \
  psql "$DSN" -v ON_ERROR_STOP=1 -f /repo/infra/db/migrations/011_add_subscription_stripe_columns.sql
docker run --rm -i --network dokploy-network -v /home/boiler/EPSCAxplor:/repo postgres:16-alpine \
  psql "$DSN" -v ON_ERROR_STOP=1 -f /repo/infra/db/migrations/012_create_processed_stripe_events.sql
```

Verify:

```sql
\d subscriptions              -- stripe_price_id, stripe_status, cancel_at_period_end,
                              -- stripe_event_created_at, and the two new indexes
\d processed_stripe_events
```

Then set the env vars on the **epsca-api** service in the Dokploy Environment tab (not compose —
Dokploy injects the Environment tab verbatim) and redeploy.

### Registering the webhook endpoint

In **Developers → Webhooks → Add endpoint**:

- URL: `https://api.epscaxplor.com/billing/webhook`
- Events: `customer.subscription.created`, `customer.subscription.updated`,
  `customer.subscription.deleted`, `invoice.payment_failed`

> **Use `https://`, not `http://`.** The `:80` Traefik router for `api.epscaxplor.com` attaches
> `redirect-to-https`, and **Stripe does not follow redirects on webhook deliveries** — an
> `http://` endpoint would 301 on every attempt and never deliver.

Copy the endpoint's signing secret into `STRIPE_WEBHOOK_SECRET`. It is **different** from the
`stripe listen` value used locally.

## 4. Request-body integrity through Traefik — verified

Signature verification reads the raw request body, so anything that rewrites the body in transit
would break it. Checked 2026-08-02 on the VPS:

- `epscaxplor-epscaapi-ixh0v2.yml` → the `websecure` router for `api.epscaxplor.com` attaches
  exactly one middleware, `epsca-secheaders`, which is **response-header only**
  (`stsSeconds`, `contentTypeNosniff`, `referrerPolicy`, `customFrameOptionsValue`).
- No `compress`, `buffering`, or path/body-rewriting middleware is attached to that router.
- The service is a plain load balancer to `http://epscaxplor-epscaapi-ixh0v2:8000`; Traefik v3
  streams request bodies through unmodified.
- In the app, the only global middleware are CORS and the CSP response-header middleware. Nothing
  reads or re-serialises the request body before the route does.

**Re-check this after any Dokploy Domains-UI change**, which regenerates the router files (the
same trigger that drops the security-header attachment — see
[traefik-security-headers.md](traefik-security-headers.md)).

## 5. Tax — read before enabling anything

The owner is a **Canadian small supplier** (under CAD $30,000) and is **not GST/HST registered**.

- `STRIPE_AUTOMATIC_TAX_ENABLED` stays **false**. An unregistered supplier must not charge
  GST/HST, and Stripe Tax bills 0.5%/txn to compute a 0% rate.
- The flag gates **both** `automatic_tax` and `tax_id_collection` — collecting a buyer's GST/HST
  number serves no purpose while we cannot charge tax.
- No GST/HST line or registration number appears on invoices/receipts while unregistered.
- **Prices must be created TAX-EXCLUSIVE.** With a tax-inclusive price, registering later takes
  the tax *out of* revenue instead of adding it on top, and correcting that requires new Price
  objects plus migrating every live subscription.

**#181 is the tripwire.** The $30k threshold is a **rolling four-consecutive-calendar-quarter**
window, and exceeding $30k within a *single* quarter ends small-supplier status **immediately**.
When registration happens: add the CA registration in Stripe (Tax → Registrations), then flip
`STRIPE_AUTOMATIC_TAX_ENABLED=true`. Existing subscriptions with `default_tax_rates` or item-level
`tax_rates` must have those cleared first — `automatic_tax` and explicit rates are mutually
exclusive.

## 6. Before switching to live mode

- [ ] #181 resolved, or a deliberate decision that revenue stays under the threshold
- [ ] Live-mode Products/Prices created (**tax-exclusive**, CAD, recurring) and live Price IDs set
- [ ] Live restricted key (`rk_live_…`) issued and set — never committed
- [ ] Live webhook endpoint registered at `https://api.epscaxplor.com/billing/webhook`, its
      signing secret set
- [ ] Customer portal configured in live mode (it is a separate config from test mode)
- [ ] Migrations 011 + 012 confirmed applied to the prod database
- [ ] One end-to-end live purchase with a real card, then refunded
- [ ] #38 — terms of service and privacy policy published (required by Stripe for live accounts)

## 7. Troubleshooting

**A subscription was paid for but the tenant has no row.**

1. Stripe Dashboard → Developers → Webhooks → the endpoint → recent deliveries. A 4xx/5xx there
   points at the app; no delivery at all points at the endpoint URL or event selection.
2. `400 invalid signature` → `STRIPE_WEBHOOK_SECRET` does not match this endpoint (the commonest
   cause is the local `stripe listen` value having been copied to prod).
3. `503` → `STRIPE_WEBHOOK_SECRET` is unset. The webhook fails closed by design.
4. App logs `no known plan matched` → the subscription is on a Price that is not in
   `STRIPE_PRICE_INDIVIDUAL` / `STRIPE_PRICE_PROFESSIONAL`. Usually a live/test Price ID mix-up.
5. App logs `cannot resolve tenant` → the subscription carries no `tenant_id` metadata and no
   prior row maps its customer. This happens for subscriptions created **directly in the
   Dashboard** rather than through Checkout. Fix by setting `tenant_id` in the subscription's
   metadata in the Dashboard, then resending the event.
6. Nothing in the logs → confirm the delivery reached Traefik at all, and re-check §4.

**Replaying an event after a fix.** Stripe's "Resend" button reuses the same event id, and the
idempotency ledger will refuse it as already processed. Clear the claim first:

```sql
DELETE FROM processed_stripe_events WHERE event_id = 'evt_…';
```

**Pruning the ledger.** It grows one row per event forever. Stripe retries for ~3 days, so rows
older than that can never be needed again:

```sql
DELETE FROM processed_stripe_events WHERE processed_at < NOW() - INTERVAL '90 days';
```

## 8. Known gaps (deliberately not in #32)

- ~~**A cancelled subscription keeps its quota.**~~ Closed by #185 — see §9.
- **`tenants.tier` is not synced.** It duplicates `subscriptions.tier` and is currently read by no
  code. The webhook deliberately leaves it alone rather than writing a second source of truth.
- **No proration/upgrade-path handling beyond what Stripe does by default.** Changing plans
  through the Billing Portal works and emits `customer.subscription.updated`, which is handled;
  nothing special is done about mid-period credits.
- **Seat limits are not status-aware.** `scripts/create_user.py` enforces `user_limit` off
  whatever `get_tenant_subscription` returns, ignoring status. It is an operator-run CLI, so an
  admin running it is already an authorisation decision, and blocking support from provisioning a
  user while a customer sorts out a card would be worse than the gap. Unchanged by #185.

---

## 9. What a lapsed subscription gets (#185)

> **Deploy order — migration 011 must be applied first.** `enforce_tier_limit` now selects
> `stripe_status` and `cancel_at_period_end`, and it runs on *every* `POST /query`. Deploying this
> image against a database without migration 011 fails every query with a 500, not just billing
> ones. Migrations are manual on prod (see CLAUDE.md), so confirm before deploying:
>
> ```sql
> SELECT column_name FROM information_schema.columns
> WHERE table_name = 'subscriptions'
>   AND column_name IN ('stripe_status', 'cancel_at_period_end');
> ```
>
> Two rows means it is safe to deploy.

`enforce_tier_limit` resolves entitlement through `src/billing/entitlements.py` rather than
reading `query_limit_monthly` directly. The policy:

| Stripe status | Stored `status` | Gets |
|---|---|---|
| `active` | `active` | Full tier quota |
| `active` + `cancel_at_period_end` | `active` | **Full tier quota** — paid through period end |
| `trialing` | `trialing` | Full tier quota |
| `past_due` (retrying) | `past_due` | Full tier quota, up to the backstop below |
| `unpaid` (retries exhausted) | `past_due` | Lapsed allowance |
| `canceled` / `incomplete` / `incomplete_expired` / `paused` | `cancelled` | Lapsed allowance |
| *no subscription row at all* | — | **Unlimited** (bootstrap tenant, hand-provisioned) |

The lapsed allowance is `LAPSED_QUERY_LIMIT_MONTHLY` in `src/billing/plans.py` (10/month,
calendar-month window). It is not a tier: there is no Price, it is absent from `GET /billing/plans`,
and the row keeps the tier it was bought on.

Exhausting it returns **402**, not 429 — waiting will not help, paying will. A paying tenant that
exhausts its real quota still gets 429 with `Retry-After`. `/history` and `/documents` are not
gated, so a churned customer keeps read access to answers they already paid to produce.

> **Operational dependency — check this in the Dashboard.** `past_due` keeps full quota because
> Stripe's own dunning schedule is treated as the grace period. That only terminates if
> **Billing → Subscriptions and emails → Manage failed payments** is set to cancel or mark unpaid
> after the final retry. If it is left on "do nothing", the subscription sits `past_due` forever.
> `PAST_DUE_GRACE_DAYS` (env, default 14) is the backstop that bounds this, measured from
> `current_period_start`. **Keep it at or above the Dashboard's retry window**, or it will cut
> customers off while Stripe is still legitimately collecting.

To verify after a status change, re-read the row and confirm what the tenant now gets:

```sql
SELECT tier, status, stripe_status, cancel_at_period_end,
       query_limit_monthly, current_period_start
FROM subscriptions WHERE tenant_id = '<uuid>'
ORDER BY (status IN ('active','trialing','past_due')) DESC, created_at DESC;
```

The `ORDER BY` matches `get_tenant_subscriptions`: the top row is the one that decides access.
It is not always the newest — an abandoned 3-D Secure checkout leaves an `incomplete` row newer
than the subscription actually being paid for, and entitled rows deliberately outrank it.
