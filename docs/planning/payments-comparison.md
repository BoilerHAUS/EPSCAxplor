# Payments & Billing Platform Comparison — Phase 4 Decision Doc

**Date:** 2026-08-02
**Status:** Recommendation — pending owner decision
**Decides:** Which payment/billing platform backs recurring SaaS subscriptions for EPSCAxplor,
before #32 (API subscription integration) and #33 (pricing page + checkout) are built.

**Recommendation up front: keep Stripe (direct gateway) + Stripe Tax. #32/#33 stand as scoped.
Do not adopt a Merchant of Record now; re-evaluate at the trigger conditions in §9.**

> **Amendment 2026-08-02, during #32 implementation — the Stripe Tax half of this recommendation is
> DEFERRED, not adopted.** This document assumed tax collection was needed from day one. It is not:
> the owner is a Canadian **small supplier** (under the CAD $30,000 threshold) and is **not GST/HST
> registered**, so charging GST/HST would be improper — and Stripe Tax would bill 0.5%/txn to
> compute a 0% rate.
>
> What shipped instead: `automatic_tax` and `tax_id_collection` are both gated behind
> `STRIPE_AUTOMATIC_TAX_ENABLED`, defaulting to **false**, and Prices are created **tax-exclusive**
> so that registering later adds tax on top rather than carving it out of revenue (fixing that
> after the fact would need new Price objects plus migrating every live subscription).
>
> This does not change the platform choice. Every fee row below that includes a Stripe Tax line is
> now *cheaper* than shown for Stripe, which only widens the gap to the MoR options.
> [#181](https://github.com/BoilerHAUS/EPSCAxplor/issues/181) stays open as the registration
> tripwire: the threshold is a rolling four-consecutive-calendar-quarter window, and exceeding $30k
> inside a single quarter ends small-supplier status immediately.

---

## 1. What we are actually optimizing for

Facts that constrain the choice, drawn from the current codebase and plan:

| Reality | Source | Consequence |
|---|---|---|
| Tiers are `individual` / `professional` / `enterprise`; quota + user limits per tenant | [003_create_subscriptions.sql](infra/db/migrations/003_create_subscriptions.sql) | Need a webhook that writes tier + period window into one table. Nothing exotic. |
| Enforcement already exists and is *already* subscription-table-driven | [tier_limit.py](services/api/src/auth/tier_limit.py) | Billing only has to populate rows. Zero enforcement work in #32. |
| Schema already has `stripe_customer_id` / `stripe_subscription_id` | [003_create_subscriptions.sql:10](infra/db/migrations/003_create_subscriptions.sql) | Stripe path needs no migration; a non-Stripe path needs a rename migration. |
| Self-hosted FastAPI + Next.js behind Traefik on an OVH VPS | [CLAUDE.md](CLAUDE.md) | Integration must be API + webhook. No hosted storefront, no platform-managed frontend. |
| Buyers: Ontario construction contractors, union locals, union halls | [planning.md §Subscription Tiers](docs/planning.md) | Near-100% **Canadian B2B**. Cheque / PO / EFT purchasing is common. Buyers want a GST/HST number on the invoice to claim ITCs. |
| Enterprise tier = API keys, unlimited, white-label | [#35](https://github.com/BoilerHAUS/EPSCAxplor/issues/35), [#34](https://github.com/BoilerHAUS/EPSCAxplor/issues/34) | Manual/negotiated invoicing matters more than self-serve card checkout at the top tier. |
| Platform fork wants **per-tenant billing** across many orgs | [planning-platform.md](docs/planning-platform.md) | This is a marketplace/platform billing shape. It is the single most decision-relevant future constraint — see §6. |
| Solo Canadian developer, minimal compliance appetite | stated requirement | Weigh ops burden heavily; but see §4 — the Canadian burden here is smaller than it looks. |

The decisive asymmetry: **the customer base is domestic B2B, not global self-serve.** Merchant-of-Record
pricing is a premium paid to make *international* tax disappear. We do not currently have an
international tax problem to make disappear.

---

## 2. Comparison matrix

| Criterion | **Stripe** (direct gateway) | **Paddle** (MoR) | **Polar.sh** (MoR) | **Lemon Squeezy** (MoR) | **Shopify** |
|---|---|---|---|---|---|
| Model | Gateway — you are the seller of record | MoR — Paddle is the seller | MoR — built on Stripe | MoR — being absorbed into Stripe | Storefront commerce platform |
| Headline fee (CAD domestic card) | **2.9% + $0.30** | 5% + $0.50 | 5% + $0.50 (Starter); 4%-tier requires $20–400/mo plan | 5% + $0.50 (+1.5% international) | 2.9%-ish via Shopify Payments **+ 2% penalty on external gateways** |
| Recurring billing fee | Billing: 0.7% of billing volume (pay-as-you-go) — avoidable, see §3 | included | included | included | subscriptions require a 3rd-party app (Recharge etc.), extra $ |
| Tax engine fee | Stripe Tax Basic: 0.5%/txn (no-code) or CA$0.50/txn (API), only where registered | included | included | included | Shopify Tax, storefront-oriented |
| FX / conversion | 2% conversion + 0.8% international card | baked into 5% | baked in | 5% + 1.5% intl | 1.5%+ |
| **Who remits sales tax** | **You** (via Stripe Tax calc; you file) | Paddle | Polar | Lemon Squeezy | You |
| CAD pricing + CAD payouts | Yes, native | Yes (sells 200+ countries, pays out worldwide) | Yes | Yes | Yes |
| Canadian pre-authorized debit (PAD/ACSS) | **Yes** — big for recurring Canadian B2B | No | No | No | No |
| Manual/PO/wire invoicing for enterprise | Stripe Invoicing, 0.4% (US$2 cap/invoice) | Yes — wire, PO numbers, custom terms, auto-reconcile | Weak | Weak | No |
| Platform / per-tenant reseller billing | **Stripe Connect** — supported | **Not supported** | Not supported | Not supported | No |
| Python SDK | `stripe` 15.4.0, first-party, canonical | `paddle-python-sdk` 1.15.0, first-party | `polar-sdk` 0.32.0 | none maintained | n/a |
| Node/Next SDK (weekly npm dl) | `stripe` 22.4.0 — **15.7M/wk** | `@paddle/paddle-node-sdk` 3.8.0 — 111K/wk | `@polar-sh/sdk` 0.49.0 — 242K/wk | — | — |
| Customer portal / dunning / proration / trials | All first-party, mature | All present | Present, younger | Present | via apps |
| Ecosystem / hiring / AI-assist familiarity | Overwhelming | Good | Thin | Declining | Irrelevant |
| Vendor risk | Lowest | Independent, stable | Small startup; **raised prices in 2026** | **Being absorbed into Stripe Managed Payments** | n/a |

**Stripe Managed Payments** (Stripe's own MoR, public preview Feb 2026, available to Canadian
businesses subject to eligibility review) is listed separately because it is the *upgrade path*, not
a competitor: **+3.5% on top of standard Stripe fees** → ~6.4% + $0.30 domestic, past 8–10% on
international cards with FX. Critically, it **does not support Stripe Connect / platform models**.

---

## 3. Real fee math on our shape

Assume the Professional tier lands around **CAD $99/mo**, Canadian card, no FX.

| Platform | Per-transaction cost | Effective rate | At 50 subs/yr | At 200 subs/yr |
|---|---|---|---|---|
| Stripe, Checkout only (no Billing add-on) | $2.87 + $0.50 Tax (API) = $3.37 | 3.4% | $2,022 | $8,089 |
| Stripe + Billing pay-as-you-go (0.7%) | $4.06 | 4.1% | $2,438 | $9,752 |
| Paddle / Polar / Lemon Squeezy | $5.45 | 5.5% | $3,270 | $13,080 |
| Stripe Managed Payments | $6.64 | 6.7% | $3,984 | $15,936 |

MoR premium over lean Stripe: **~$1,250/yr at 50 subs, ~$5,000/yr at 200 subs.** What that premium
buys is tax filing relief. A Canadian GST/HST return for a single-jurisdiction domestic SaaS is a
few hundred dollars a year of accountant time. **The premium exceeds the burden it removes, and the
gap widens with growth.**

Note the "Billing pay-as-you-go" row is largely avoidable: Stripe **Checkout + Customer Portal +
Subscriptions** covers fixed-price recurring tiers without the metered/invoice-heavy Billing SKU.
Confirm the current Billing-vs-Checkout fee boundary with Stripe before launch — it has moved before.

---

## 4. Canadian tax — the part that changes the answer

**Domestic (the ~100% case).**
- Canada's **small-supplier threshold is CAD $30,000** in worldwide taxable supplies over four
  consecutive quarters. Below that, a Canadian solo dev is **not required to register for or charge
  GST/HST at all.** Phase 4 launch revenue will sit under this for some time.
- Above it: register once, charge the destination-province rate (Ontario HST 13% for the core
  market), file a return. One jurisdiction, one filing cadence. This is a bookkeeping task, not a
  compliance program.
- **Canadian unions and contractors are not tax-exempt purchasers.** There is no US-style exemption
  certificate flow to build. Labour unions and non-profits pay GST/HST and recover it downstream via
  input tax credits or the Public Service Bodies' rebate — *on their own return, not ours.* The
  practical requirement on us is narrow: **show a valid GST/HST registration number on the invoice**
  so the buyer can claim its ITC. Stripe Invoicing/Tax does this natively once registered.
- Being the seller of record is arguably an **advantage** here: the invoice carries *our* Canadian
  business number. Under an MoR, the invoice carries the MoR's registration and the seller-of-record
  is a foreign entity — legitimate, but a predictable source of friction with union-hall finance
  departments doing AP verification.

**International.**
- This is where MoR earns its fee: EU VAT on digital services has a **€0 threshold for non-EU
  sellers** (register via the non-Union OSS scheme), UK VAT likewise, and US state economic nexus
  rules vary. Today this is a hypothetical for a corpus of *Ontario* collective agreements.
- Mitigation while direct on Stripe: **geo-restrict checkout to Canada (and optionally the US) at
  launch.** Zero foreign registrations, zero exposure. Revisit deliberately.

**Verdict:** the MoR value proposition is priced for a global self-serve product. Ours is a domestic
B2B product. We would be paying a global-compliance premium against a single-province tax obligation.

---

## 5. Is Shopify the right tool? — No. Reject.

Assessed because it was on the table, not because it fits.

- **Storefront-centric by design.** Its object model is products, carts, orders, fulfillment. There
  is no native concept of a *SaaS entitlement* — a tenant with a tier, a quota, and an API key.
- **Subscriptions are not native for this shape.** They require selling-plan/subscription-contract
  APIs oriented toward physical replenishment, or third-party apps (Recharge et al.) — an extra
  vendor, extra fee, extra failure mode.
- **A 2% penalty fee applies to external payment gateways**, and meaningful checkout customization
  is gated behind Shopify Plus (~$2,300/mo).
- **Admin GraphQL rate limits** (100 points/sec on standard plans) make it a poor system-of-record
  for a service that must check entitlement on every query.
- We would be running a headless commerce platform purely as a billing table for a product with no
  storefront. Strictly more moving parts than Stripe, for less capability.

Shopify is the wrong tool for a non-storefront API SaaS. Drop it from consideration.

---

## 6. The white-label / platform-fork constraint (decisive)

[#34](https://github.com/BoilerHAUS/EPSCAxplor/issues/34) (white-label tenant config) and
[planning-platform.md](docs/planning-platform.md) both point at the same future: **many tenant
organizations, each billed separately, potentially with us intermediating.** That is a platform
billing shape.

- **Stripe Connect** is purpose-built for it (per-tenant accounts, split payments, per-tenant payouts,
  per-tenant tax posture) and is the industry default.
- **Paddle, Polar, and Lemon Squeezy do not support platform/marketplace models.**
- **Stripe Managed Payments explicitly excludes Connect**, including Express and platform-managed
  accounts.

So every MoR option — including Stripe's own — is a **dead end for the platform fork**. Choosing an
MoR now means a forced re-platform precisely when the product gets more valuable and migration is
most painful. Choosing direct Stripe keeps Connect available without committing to it.

This single constraint would justify the recommendation even if the fee math were neutral.

---

## 7. Recommendation

**Adopt Stripe as a direct gateway, with Stripe Tax, and geo-restrict checkout to Canada at launch.**

Rationale, ranked:

1. **Platform-fork compatibility.** Stripe Connect is the only path to per-tenant billing; all MoR
   options foreclose it (§6).
2. **Tax burden is overstated for our market.** Domestic-only B2B, one province, plus a $30K
   small-supplier runway before registration is even required (§4).
3. **Cheapest by a widening margin** — ~$1,250/yr at 50 subs, ~$5,000/yr at 200 (§3).
4. **Canadian B2B fit.** Pre-authorized debit for recurring domestic payments and mature Invoicing
   for PO/cheque enterprise deals — neither available on Paddle/Polar/LS. Union locals and
   contractors buy this way.
5. **Our invoice carries our GST/HST number**, which is exactly what buyers need for ITCs (§4).
6. **Lowest integration and maintenance cost.** Schema already Stripe-shaped; enforcement already
   built; SDKs are the most battle-tested in the category by orders of magnitude (§2).
7. **Lowest vendor risk.** Lemon Squeezy is being absorbed into Stripe Managed Payments (creator
   features are not surviving the migration) — building on it now would be building on a sunset.
   Polar raised prices in 2026 and is the smallest vendor here.

**Runner-up: Paddle.** If the product unexpectedly goes international-self-serve, Paddle is the right
MoR — strongest B2B story of the three (wire, PO numbers, custom terms, tax-exempt VAT/GST-number
billing, auto-reconciliation), first-party maintained Python SDK, independent vendor. It is a
credible switch target, not a rejected option.

**Do not adopt:** Shopify (wrong tool, §5), Lemon Squeezy (sunsetting), Polar (vendor + pricing risk,
no platform support), Stripe Managed Payments (+3.5% and kills Connect).

---

## 8. Integration sketch for the top pick

Deliberately minimal. Hosted Stripe Checkout + Customer Portal means **no new frontend dependency and
no card data anywhere near our VPS.**

**Dependencies**
- `services/api/requirements.txt`: `+ stripe>=15.4.0`
- `apps/web/package.json`: **no change.** Checkout and Portal are redirects to Stripe-hosted URLs.

**Config** (`services/api/src/config.py`, Pydantic Settings, validated at startup)
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_INDIVIDUAL`, `STRIPE_PRICE_PROFESSIONAL`.
Price ID → tier mapping lives in config, never hardcoded.

**New module** `services/api/src/routes/billing.py` (~200 lines, three endpoints)

| Endpoint | Auth | Does |
|---|---|---|
| `POST /billing/checkout-session` | JWT | Creates a Checkout Session for the caller's tenant. `client_reference_id = tenant_id`, `automatic_tax.enabled = true`, `tax_id_collection.enabled = true` (B2B GST/HST numbers), `allowed_countries = ["CA"]`. Returns the redirect URL. |
| `POST /billing/portal-session` | JWT | Billing Portal session for `stripe_customer_id` — cancel, update card, download invoices. Self-serve; zero support code for us. |
| `POST /billing/webhook` | **signature, not JWT** | `stripe.Webhook.construct_event(raw_body, sig_header, secret)`. Must read the **raw** request body. |

**Webhook events → the one write path**

`checkout.session.completed`, `customer.subscription.created|updated|deleted`,
`invoice.payment_failed` → upsert `subscriptions` (`tier`, `status`, `stripe_customer_id`,
`stripe_subscription_id`, `current_period_start/end`, `query_limit_monthly`, `user_limit`).

**Enforcement is already done.** `enforce_tier_limit` reads exactly these columns
([tier_limit.py:44](services/api/src/auth/tier_limit.py)) and currently fails open because rows do not
exist. Populating the table turns on tier enforcement with no new enforcement code — the cleanest
possible seam.

**Correctness requirements (non-negotiable)**
- **Signature verification before any parsing.** Unverified webhook bodies are untrusted input.
- **Idempotency.** New table `processed_stripe_events (event_id TEXT PRIMARY KEY, processed_at)`;
  insert-or-skip. Stripe retries and reorders — handlers must be safe to replay.
- **Raw body preservation.** Verify Traefik/Dokploy does not alter the body on the webhook path.
- **Never trust client-supplied tier.** Tier derives from the Stripe `price_id` server-side only.
- **Webhook path excluded from JWT middleware and from per-IP rate limiting** (Stripe retries in
  bursts) — check against [rate_limit.py](services/api/src/auth/rate_limit.py).
- Secrets via environment only, live keys never in the repo, per [security.md](CLAUDE.md).

**Migrations:** none required for #32 — `subscriptions` already carries the Stripe columns. One small
additive migration is likely wanted for `stripe_price_id` and `cancel_at_period_end`.

**Frontend (#33):** static pricing page → authenticated `POST /billing/checkout-session` →
`window.location = url`. A "Manage billing" link hits the portal endpoint. Success/cancel return
routes. No Stripe JS, no PCI surface, no new npm packages.

**Enterprise tier:** do **not** self-serve. Stripe Invoicing with PO number and net-30 terms, or
Canadian pre-authorized debit for recurring. Provision the tenant and API key manually
([#35](https://github.com/BoilerHAUS/EPSCAxplor/issues/35)) — correct for a handful of high-value
union/GC accounts, and avoids building a quoting flow nobody needs yet.

**Reference implementations:** Stripe's first-party Python and Next.js samples are the canonical
source; [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)
(44.5K★, actively maintained) is the best reference for FastAPI project structure around this. GitHub
search surfaced **no high-quality, maintained FastAPI+Stripe subscription reference** worth vendoring
— the top hit had 0 stars. Use the official SDK directly; the integration is small enough that
adopting a thin unmaintained wrapper would add risk rather than remove it.

---

## 9. When to revisit

Switch to an MoR (Paddle) if any of these become true:

- **International revenue exceeds ~20%** of MRR, or we intentionally open self-serve outside Canada.
- We start owing VAT/sales tax in **three or more foreign jurisdictions** — that is where filing cost
  overtakes the ~2% premium.
- Chargeback or fraud load becomes material (MoR assumes liability).

Do **not** switch if the platform fork is live on Connect — at that point the MoR options cannot
serve the business model at all (§6).

---

## 10. Implication for the Phase 4 issues

| Issue | Verdict | Action |
|---|---|---|
| [#32](https://github.com/BoilerHAUS/EPSCAxplor/issues/32) feat(api): Stripe subscription integration | **Keep — Stripe confirmed** | Re-scope the body to the §8 sketch: Checkout + Portal + webhook, idempotency table, Stripe Tax with `automatic_tax` and `tax_id_collection`, CA-only `allowed_countries`. Note that enforcement is already built. |
| [#33](https://github.com/BoilerHAUS/EPSCAxplor/issues/33) feat(web): pricing page + Stripe checkout | **Keep — Stripe confirmed** | Confirm hosted-Checkout redirect (no new npm deps). Set the three tier prices in CAD. Add a "contact us" path for enterprise instead of a checkout button. |
| [#35](https://github.com/BoilerHAUS/EPSCAxplor/issues/35) enterprise API-key dashboard | Unaffected | Enterprise stays manually invoiced; the dashboard manages keys, not billing. |
| [#34](https://github.com/BoilerHAUS/EPSCAxplor/issues/34) white-label tenant config | **Reinforced** | Stripe Connect is the eventual per-tenant billing path. Do not design tenant billing against an MoR. |
| — | **New issue suggested** | `ops: register for GST/HST and configure Stripe Tax` — a no-pr prerequisite for #32. Includes deciding whether to register before the $30K threshold (voluntary registration lets us claim ITCs on infra spend, and gives B2B buyers the number they want on invoices — likely worth doing early). |

**Net: no re-scope of the platform choice. Stripe was the right default; it now has a documented
rationale rather than an assumed one.** The substantive changes are the *shape* of #32 (leaner than
originally implied — no enforcement work, no schema migration, no frontend SDK) and one new ops
prerequisite.

---

## Sources

- [Stripe pricing (Canada)](https://stripe.com/en-ca/pricing) · [Stripe Tax](https://stripe.com/tax) · [Stripe Managed Payments](https://stripe.com/managed-payments) · [Managed Payments eligibility](https://docs.stripe.com/payments/managed-payments/eligibility) · [MoR for SaaS](https://stripe.com/resources/more/merchant-of-record-for-saas) · [GST registration in Canada](https://stripe.com/guides/tax-registration-process-canada) · [Canadian pre-authorized debits](https://docs.stripe.com/payments/acss-debit)
- [Paddle supported countries](https://developer.paddle.com/concepts/sell/supported-countries-locales/) · [How Paddle handles VAT](https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf) · [Paddle invoicing](https://www.paddle.com/billing/invoicing) · [Enterprise billing via invoices](https://www.boathouse.co/paddle-video-series-episode/13-selling-saas-through-enterprise-billing-with-custom-plans-in-paddle) · [Stripe Managed Payments, per Paddle](https://www.paddle.com/resources/stripe-managed-payments)
- [Polar pricing](https://polar.sh/resources/pricing) · [Polar merchant of record](https://polar.sh/resources/merchant-of-record) · [Polar 2026 review / rate increase](https://fungies.io/polar-sh-review-2026/)
- [Stripe acquires Lemon Squeezy](https://www.lemonsqueezy.com/blog/stripe-acquires-lemon-squeezy) · [Lemon Squeezy + Managed Payments, 2026](https://www.lemonsqueezy.com/blog/2026-update) · [Acquisition analysis](https://fungies.io/lemon-squeezy-stripe-acquisition-saas-founders-2026/)
- [Shopify subscriptions (dev docs)](https://shopify.dev/docs/apps/build/purchase-options/subscriptions) · [Shopify limitations 2026](https://www.swell.is/content/shopify-limitations)
- [CRA — GST/HST Public Service Bodies' rebate](https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses/gst-hst-rebates/public-service-bodies.html) · [Public Service Body Rebate Regulations](https://laws-lois.justice.gc.ca/eng/Regulations/SOR-91-37/index.html)
- MoR fee comparisons: [Stripe vs Paddle vs Lemon Squeezy vs Polar](https://fintechspecs.com/blog/stripe-vs-paddle-vs-lemon-squeezy-vs-polar-merchant-of-record-b2b-saas/) · [MoR pricing guide 2026](https://fungies.io/merchant-of-record-pricing-guide-2026/) · [Managed Payments cost analysis](https://tiun.io/blog/cost-of-stripe-managed-payments-2026)
- SDK maturity: PyPI `stripe` 15.4.0, `paddle-python-sdk` 1.15.0, `polar-sdk` 0.32.0 · npm `stripe` 22.4.0 (15.7M/wk), `@paddle/paddle-node-sdk` 3.8.0 (111K/wk), `@polar-sh/sdk` 0.49.0 (242K/wk) · [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)

> Fees and tax thresholds were verified 2026-08-02 and change frequently. Re-confirm the Stripe
> Billing-vs-Checkout fee boundary and the Stripe Tax plan tiers before implementing #32.
> This document is engineering analysis, not tax advice — confirm registration timing with an
> accountant.
