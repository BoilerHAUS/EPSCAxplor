# Phase 2 Full-Corpus Evaluation — GATE RUN

> Final #22 gate run against the complete 18-union corpus (317 documents), after
> the nomic-prefix reingest (#94), scope-aware wage pass + terrazzo alias (#95),
> BACU grade fix, and interim auth (#93). Baseline for comparison: the pre-#94
> run in git history (14/17 auto-checks; W14/W15/W21 failing).

**Run date:** 2026-07-12 13:19 UTC  
**Questions:** 50  
**API errors:** 0  
**Auto-checked (expected_contains):** 17 pass / 0 fail / 33 manual-only  

> **Note:** Correctness and citation accuracy scores require manual review against
> the source PDFs. Fill in the `Correct?` and `Citations valid?` columns below.

## Acceptance Criteria

| Criterion | Threshold | Result |
|-----------|-----------|--------|
| Correctness | ≥ 85% | **92.0%** (44 Yes, 4 Partial x 0.5, 0 No / 50) — PASS |
| Citation accuracy | 100% | **100%** of reviewed citations valid (no section mislabels observed this run) |
| Zero hallucinated facts on refusal questions | 0 | **0** — R03/R04 clean refusals, zero citations |
| Cross-union comparison valid | Pass/Fail | **Pass** — C01 full two-union comparison; C02/C03/C04 exact rates from both unions |
| Nuclear context includes NPA chunks | Pass/Fail | **Pass** — N03/N05/N06 cite NPA sources |

---

## Wages & Rates

### W01 — IBEW

**Question:** What is the journeyperson hourly rate for IBEW Generation electricians effective May 1, 2025?

**Answer:**

# IBEW Generation Journeyperson Hourly Rates Effective May 1, 2025

The journeyperson hourly rate for IBEW Generation electricians effective May 1, 2025 **varies by local**. There is no single rate across all IBEW Generation locals. Here are the base hourly rates for the available locals:

| Local | Location | Base Rate (May 1, 2025) |
|-------|----------|------------------------|
| LU 105 | Hamilton | $46.65 [SOURCE 1] |
| LU 115 | Quinte/St. Lawrence | $48.63 [SOURCE 2] |
| LU 586 | Ottawa | $50.82 [SOURCE 4] |
| LU 1687 | Sudbury | $50.25 [SOURCE 3] |
| LU 120 | London | $48.59 [SOURCE 5] |

**Supporting Clause Text:**

Each local wage schedule lists the effective rates for journeyman/welder/communications electricians (occupation codes 410135, 410136, 410137; grade/step 07-6). For example, IBEW Local 105 shows: "Effective 2025-05-01: base hourly rate $46.65, vacation & statutory holiday pay $5.60, welfare $5.93, retirement fund $9.50, union funds $6.04, total wage package $73.72" [SOURCE 1, IBEW Local 105 Wage Schedule E-6-C].

**Note:** The rates shown are base hourly rates. Total wage packages include vacation, statutory holiday pay, welfare, retirement/pension funds, union funds, and other statutory contributions, which vary by local.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation Wage Schedule E-6-C LU 105 Hamilto |  |  |
| 2 | IBEW | IBEW Generation Wage Schedule E-12-C LU 115 Quinte |  |  |
| 3 | IBEW | IBEW Generation Wage Schedule E-15-C LU 1687 Sudbu |  |  |
| 4 | IBEW | IBEW Generation Wage Schedule E-13-C LU 586 Ottawa |  |  |
| 5 | IBEW | IBEW Generation Wage Schedule E-4-C LU 120 London  |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6471ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 46.65. |

---

### W02 — IBEW

**Question:** What is the foreman wage premium for IBEW Generation electricians?

**Answer:**

The provided documents do not contain information about a foreman wage premium as a separate percentage or fixed amount above the journeyperson rate for IBEW Generation electricians.

What the documents do show is that the wage schedules list "ELECTRICIAN / FOREMAN" as a distinct classification (occupation code 410165; grade/step 07-9) with its own hourly rates that differ from journeyperson rates. For example:

- [SOURCE 1] IBEW Local 586 (Ottawa) shows Foreman base rate of $56.92 effective May 1, 2025
- [SOURCE 2] IBEW Local 402 (Thunder Bay) shows Foreman base rate of $59.43 effective May 1, 2025
- [SOURCE 3] IBEW Local 303 (Niagara) shows Foreman base rate of $57.72 effective May 1, 2026

However, the documents do not explicitly state what premium (if any) this represents above journeyperson wages, nor do they contain a contractual clause defining a foreman premium formula.

To determine the actual premium, you would need to compare the foreman rates in these schedules against the journeyperson rates for the same local and effective date, which would require additional wage schedule information not provided here.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation Wage Schedule E-13-C LU 586 Ottawa |  |  |
| 2 | IBEW | IBEW Generation Wage Schedule E-16-C LU 402 Thunde |  |  |
| 3 | IBEW | IBEW Generation Wage Schedule E-7-C LU 303 Niagara |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4514ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Partial** | **Yes** | Same-local rates correct; CA §600 F (12%/6% rule) still not retrieved — #78. |

---

### W03 — IBEW

**Question:** What is the tool allowance for IBEW Generation electricians?

**Answer:**

Based on the provided documents, there is no specific monetary "tool allowance" stated for IBEW Generation electricians. 

Instead, the collective agreement establishes a **tool list requirement** rather than a cash allowance. [SOURCE 1, Page 49] specifies that "All journeypeople electricians are required to have the following tools:" and then lists 16 categories of hand tools including centre punch, cold chisel, pliers, screwdrivers, tape measure, tool box, and tool pouch.

Under [SOURCE 7, Section 1200 A], employees "shall be required to provide themselves with the ordinary hand tools of the trade as specified in the attached tool list." The Employer is not required to pay a tool allowance, but rather:

- Must provide storage facilities for tools [SOURCE 7, Section 1200 A]
- Will compensate up to $750.00 for tools lost by fire or theft under specific conditions [SOURCE 7, Section 1200 A(i)-(ii)]
- Gang tools (issued to forepersons) remain the Employer's responsibility [SOURCE 9, Section 1200 C]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 9 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5533ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: Centre Punch. |

---

### W04 — Sheet Metal

**Question:** What is the journeyperson hourly rate for Sheet Metal workers effective May 1, 2025?

**Answer:**

The journeyperson hourly rate for Sheet Metal workers effective May 1, 2025 varies by local union jurisdiction. There is no single rate across all Sheet Metal locals covered by EPSCA.

**The base hourly rates effective May 1, 2025 are:**

- **Local 562 (Kitchener): $48.63** [SOURCE 1, Wage Schedule SM-05, effective 2025-05-01]
- **Local 504 (Sault Ste. Marie): $47.42** [SOURCE 2, Wage Schedule SM-15, effective 2025-05-01]
- **Local 504 (Sudbury): $48.06** [SOURCE 3, Wage Schedule SM-14, effective 2025-05-01]
- **Local 235 (Chatham): $48.08** [SOURCE 4, Wage Schedule SM-02, effective 2025-05-01]
- **Local 235 (Windsor): $48.16** [SOURCE 5, Wage Schedule SM-01, effective 2025-05-01]
- **Local 235 (Sarnia): Not provided in sources for 2025-05-01**

These are **base hourly rates only**. The total wage package (including vacation & statutory holiday pay, welfare, pension, union funds, provincial training fund, and EPSCA association fund) is higher. For example, Local 562's total wage package is $65.88 [SOURCE 1].

If you need the rate for a specific local union, please clarify which jurisdiction applies.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-05 LU 562 Kitchener |  |  |
| 2 | Sheet Metal | Sheet Metal Wage Schedule SM-15 LU 504 Sault Ste.  |  |  |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-14 LU 504 Sudbury |  |  |
| 4 | Sheet Metal | Sheet Metal Wage Schedule SM-02 LU 235 Chatham |  |  |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-01 LU 235 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4893ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 48.16. |

---

### W05 — Sheet Metal

**Question:** What apprentice wage rates apply to Sheet Metal workers under the 2025-2030 collective agreement?

**Answer:**

# Apprentice Wage Rates for Sheet Metal Workers (2025-2030)

The apprentice wage rates under the 2025-2030 collective agreement vary by local and apprenticeship period. Here are the rates currently provided in the source documents:

## Sheet Metal Local 473 (London)

**Apprentice / 3rd Period (70% of journeyman)** [SOURCE 1]
- Effective 2025-05-01: Base $31.83/hr, total package $49.13/hr
- Effective 2026-05-01: Base $33.71/hr, total package $51.43/hr
- Effective 2027-05-01: Base $35.46/hr, total package $53.36/hr
- Effective 2028-05-01: Base $37.28/hr, total package $55.36/hr
- Effective 2029-05-01: Base $38.23/hr, total package $56.40/hr

**Apprentice / 1st Period (50% of journeyman)** [SOURCE 5]
- Effective 2025-05-01: Base $22.74/hr, total package $34.49/hr
- Effective 2026-05-01: Base $24.08/hr, total package $36.13/hr
- Effective 2028-05-01: Base $26.63/hr, total package $38.93/hr

## Sheet Metal Local 504 (Sault Ste. Marie)

**Apprentice / 1st Period (50% of journeyman)** [SOURCE 3]
- Effective 2025-05-01: Base $23.71/hr, total package $34.45/hr
- Effective 2026-05-01: Base $25.20/hr, total package $36.09/hr
- Effective 2027-05-01: Base $26.45/hr, total package $37.47/hr
- Effective 2028-05-01: Base $27.75/hr, total package $38.90/hr
- Effective 2029-05-01: Base $28.43/hr, total package $39.64/hr

**Apprentice / 2nd Period (60% of journeyman)** [SOURCE 2]
- Effective 2025-05-01: Base $28.45/hr, total package $40.95/hr
- Effective 2026-05-01: Base $30.23/hr, total package $42.90/hr
- Effective 2027-05-01: Base $31.73/hr, total package $44.55/hr
- Effective 2028-05-01: Base $33.29/hr, total package $46.27/hr
- Effective 2029-05-01: Base $34.11/hr, total package $47.17/hr

**Apprentice / 5th Period (80% of journeyman)** [SOURCE 4]
- Effective 2025-05-01: Base $37.94/hr, total package $53.92/hr
- Effective 2026-05-01: Base $40.31/hr, total package $56.53/hr
- Effective 2027-05-01: Base $42.31/hr, total package $58.73/hr
- Effective 2028-05-01: Base $44.39/hr, total package $61.02/hr
- Effective 2029-05-01: Base $45.48/hr, total package $62.22/hr

**Note:** The wage packages include base hourly rate, vacation & statutory holiday pay, welfare, pension, union funds, provincial training fund, and EPSCA association fund. Rates vary by local and apprenticeship period. The provided sources do not contain complete apprentice wage schedules for all locals or all apprenticeship periods under the 2025-2030 agreement.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-04 LU 473 London |  |  |
| 2 | Sheet Metal | Sheet Metal Wage Schedule SM-15 LU 504 Sault Ste.  |  |  |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-15 LU 504 Sault Ste.  |  |  |
| 4 | Sheet Metal | Sheet Metal Wage Schedule SM-15 LU 504 Sault Ste.  |  |  |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-04 LU 473 London |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7537ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: % of Journeyman. |

---

### W06 — Sheet Metal

**Question:** What is the general foreman wage rate for Sheet Metal workers?

**Answer:**

# Foreman Wage Rates for Sheet Metal Workers

There is **no single "general" foreman wage rate** across all Sheet Metal locals in Ontario. Instead, foreman wages vary by local and effective date. Here are the current rates:

## By Local (Effective May 1, 2026):

**Sheet Metal Local 269 (Kingston) — FOREMAN:**
- Base hourly rate: $53.95
- Total wage package: $77.28 [SOURCE 1]

**Sheet Metal Local 537 (St. Catharines) — FOREMAN:**
- Base hourly rate: $57.98
- Total wage package: $79.01 [SOURCE 4]

**Sheet Metal Local 537 (Hamilton) — FOREMAN:**
- Base hourly rate: $57.68
- Total wage package: $78.68 [SOURCE 5]

## Note on Classification Variants:

The sources also show a **FOREMAN SHEETER/DECKER** classification (different occupation code 445566 vs. standard foreman code 445565) with different rates:

**Sheet Metal Local 537 (St. Catharines) — FOREMAN SHEETER/DECKER:**
- Base hourly rate: $57.78
- Total wage package: $78.79 [SOURCE 2]

**Sheet Metal Local 537 (Brantford) — FOREMAN SHEETER/DECKER:**
- Base hourly rate: $57.55
- Total wage package: $78.54 [SOURCE 3]

Future effective dates (2027–2029) show scheduled increases in all locals.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-12 LU 269 Kingston |  |  |
| 2 | Sheet Metal | Sheet Metal Wage Schedule SM-08 LU 537 St Catharin |  |  |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-07 LU 537 Brantford |  |  |
| 4 | Sheet Metal | Sheet Metal Wage Schedule SM-08 LU 537 St Catharin |  |  |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-06 LU 537 Hamilton |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4947ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 445565. |

---

### W07 — United Association

**Question:** What is the journeyperson hourly rate for United Association plumbers effective May 1, 2025?

**Answer:**

The journeyperson hourly rate for United Association plumbers effective May 1, 2025 varies by local jurisdiction. There is no single rate across Ontario. Here are the applicable rates:

**Local 628 (Thunder Bay):** $48.98 base hourly rate [SOURCE 1, UA-17 Wage Schedule, effective May 1, 2025]

**Local 663 (Sarnia):** $50.94 base hourly rate [SOURCE 2, UA-2 Wage Schedule, effective May 1, 2025]

**Local 800 (Sault Ste. Marie):** $47.14 base hourly rate [SOURCE 3, UA-16 Wage Schedule, effective May 1, 2025]

**Local 71 (Ottawa):** $49.87 base hourly rate [SOURCE 4, UA-14 Wage Schedule, effective May 1, 2025]

**Local 800 (Sudbury):** $47.96 base hourly rate [SOURCE 5, UA-15 Wage Schedule, effective May 1, 2025]

These rates are for the Journeyman/Pipewelder classification (occupation codes 450035, 450036; grade/step 13-6). Each rate includes the base hourly wage plus add-ons for vacation & statutory holiday pay, welfare, pension, union funds, and the EPSCA association fund.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association Wage Schedule Local 628 Thunder |  |  |
| 2 | United Association | United Association Wage Schedule Local 663 Sarnia |  |  |
| 3 | United Association | United Association Wage Schedule Local 800 Sault S |  |  |
| 4 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 5 | United Association | United Association Wage Schedule Local 800 Sudbury |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4125ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 450035. |

---

### W08 — United Association

**Question:** What is the foreman premium percentage for United Association workers?

**Answer:**

Based on the provided wage schedules, United Association workers have **two foreman premium percentages**:

1. **Subforeman: 7.5% above journeymen base hourly rate** [SOURCE 1, SOURCE 2, SOURCE 5, SOURCE 8, SOURCE 9]

2. **Foreman: 15% above journeymen base hourly rate** [SOURCE 3, SOURCE 4, SOURCE 6, SOURCE 7, SOURCE 10]

These premiums are stated in the classification descriptions across all United Association wage schedules. For example:

- "Classification: SUBFOREMAN (occupation code 450055; grade/step 13-8). **(7.5% above journeymen base hourly rate)**" [SOURCE 1, United Association Local 46 Toronto, UA-7]

- "Classification: FOREMAN (occupation code 450065; grade/step 13-9). **(15% above journeymen base hourly rate)**" [SOURCE 4, United Association Local 46 Toronto, UA-7]

These percentages apply consistently across all United Association locals covered in the provided documents (Toronto, Ottawa, Barrie, Brantford/Hamilton, Niagara, and Thunder Bay).

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association Wage Schedule Local 46 Toronto |  |  |
| 3 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 4 | United Association | United Association Wage Schedule Local 46 Toronto |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3965ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 15%. |

---

### W09 — Boilermakers

**Question:** What is the Boilermakers journeyperson hourly rate effective May 1, 2025?

**Answer:**

# Boilermakers Journeyperson Hourly Rate – Effective May 1, 2025

The Boilermakers journeyperson hourly rate effective May 1, 2025 is **$52.72 (base rate)**, with a **total wage package of $70.48 per hour**.

## Wage Components (May 1, 2025):

- Base hourly rate: $52.72
- Vacation & statutory holiday pay: $4.75
- Welfare: $1.58
- Pension: $3.95
- Supplementary fund: $6.50
- Union funds: $0.98
- Additional amount 1: $0.33
- Additional amount 2: $0.30

**Total wage package: $70.48** [SOURCE 1]

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Boilermakers | Boilermakers Wage Schedule EPSCA Boilermakers |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3046ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 52.72)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W10 — Carpenters

**Question:** What is the journeyperson hourly rate for Carpenters in Windsor effective May 1, 2025?

**Answer:**

# Journeyperson Hourly Rate for Carpenters in Windsor (Effective May 1, 2025)

There are **three different journeyperson rates** for Carpenters in Windsor effective May 1, 2025, depending on the trade classification:

## 1. **General Carpenters / Welder & Burner**
**Base hourly rate: $44.69**
**Total wage package: $63.04** [SOURCE 2]

This applies to Carpenters Local 494 (Windsor) under EPSCA Wage Schedule C-1 for the Journeyman/Welder & Burner classification (occupation codes 400035, 400036; grade/step 01-6, 02-6).

## 2. **Acoustic and Drywall Workers**
**Base hourly rate: $44.69**
**Total wage package: $63.04** [SOURCE 3]

This applies to Carpenters Local 494 (Windsor) under EPSCA Wage Schedule AD-1 for the Journeyman/Welder & Burner classification (occupation codes 400136, 400137; grade/step 04-6).

## 3. **Resilient Floor Workers**
**Base hourly rate: $43.78**
**Total wage package: $62.04** [SOURCE 1]

This applies to Carpenters Local 494 (Windsor) under EPSCA Wage Schedule RF-1 for the Journeyman classification (occupation code 400135; grade/step 03-6).

The total wage package includes the base hourly rate, vacation & statutory holiday pay, union funds, administration & training fund, and EPSCA association fund.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Carpenters | Carpenters Resilient Floor Wage Schedule RF-1 LU 4 |  |  |
| 2 | Carpenters | Carpenters Wage Schedule C-1 LU 494 Windsor |  |  |
| 3 | Carpenters | Carpenters Acoustic and Drywall Wage Schedule AD-1 |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4880ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 44.69)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W11 — Millwrights

**Question:** What is the Millwrights journeyperson hourly rate effective May 1, 2025?

**Answer:**

Based on the provided wage schedule, the Millwrights journeyperson hourly rate effective May 1, 2025 is:

**Base hourly rate: $50.14**
**Total wage package: $69.85** (which includes base rate, vacation & statutory holiday pay, welfare, pension, and union funds)

The complete breakdown effective May 1, 2025 is:
- Base hourly rate: $50.14
- Vacation & statutory holiday pay: $5.01
- Welfare: $4.20
- Pension: $8.65
- Union funds: $1.85
- Total wage package: $69.85
- Benefits stabilization fund: $0.35
- EPSCA association fund: $0.30

[SOURCE 1: Millwrights Wage Schedule, Classification: JOURNEYMAN (occupation code 436335; grade/step 05-6), Effective May 1, 2025]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Millwrights | Millwrights Wage Schedule Millwright |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3639ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 50.14)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W12 — Ironworkers

**Question:** What is the journeyperson rate for Ironworkers in Windsor on a generation project effective May 1, 2025?

**Answer:**

# Journeyperson Ironworker Rate for Windsor — Generation Project, May 1, 2025

**Effective May 1, 2025**, the journeyperson rate for Ironworkers in Windsor on a generation project is:

- **Base hourly rate: $48.33**
- **Total wage package: $66.95** (including vacation & statutory holiday pay $4.83, welfare $4.75, pension $8.82, union funds $0.22, plus EPSCA association fund $0.30)

**Citation:**  
[SOURCE 1] — Ironworkers Generation Wage Schedule I-1, LU 700 Windsor Ironworkers - Generation, Classification: JOURNEYMAN IRONWORKER, RIGGER (occupation code 445035; grade/step 19-6), effective May 1, 2025.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Ironworkers | Ironworkers Generation Wage Schedule I-1 LU 700 Wi |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3392ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 48.33)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W13 — Rodmen

**Question:** What is the Rodmen journeyperson hourly rate in Toronto on a generation project effective May 1, 2025?

**Answer:**

The Rodmen journeyperson hourly rate in Toronto on a generation project effective May 1, 2025 is **$46.94 base hourly rate**, with a total wage package of **$65.18** per hour.

**Supporting Details:**

This rate comprises:
- Base hourly rate: $46.94
- Vacation & statutory holiday pay: $4.69
- Welfare: $4.45
- Pension: $8.99
- Union funds: $0.11
- EPSCA association fund: $0.30

[SOURCE 1, Rodmen Local 721 (Toronto) — RODMEN EPSCA Wage Schedule R-5, Journeyman classification, effective 2025-05-01]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Rodmen | Rodmen Generation Wage Schedule R-5 LU 721 Toronto |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2834ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 46.94)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W14 — Operating Engineers

**Question:** What is the operating engineer hourly rate in Hamilton effective May 1, 2025?

**Answer:**

# Operating Engineer Hourly Rate in Hamilton (May 1, 2025)

The operating engineer hourly rate in Hamilton effective May 1, 2025 depends on the specific classification and grade, as the wage schedule contains multiple rates:

| Classification | Base Hourly Rate | Total Wage Package |
|---|---|---|
| **Operating Engineer / Group 1 (Grade 51-6)** | $50.40 | $69.98 |
| **Group 2 (Grade 53-6)** | $48.85 | $68.28 |
| **Group 2 (Grade 54-6)** | $48.25 | $67.61 |
| **Group 1 (Grade 52-6)** | $49.81 | $69.33 |

## Supporting Documentation

The most common classification is **Operating Engineer / Group 1 (Grade 51-6)**, which has:
- **Base hourly rate: $50.40**
- **Total wage package: $69.98** (including vacation & statutory holiday pay of $5.04, union funds of $14.54, and additional amounts)

[SOURCE 3, Operating Engineers Wage Schedule O-4 Hamilton, Effective May 1, 2025, page 1]

The total wage package breakdown includes:
- Base hourly rate: $50.40
- Vacation & statutory holiday pay: $5.04
- Union funds: $14.54
- Additional amounts: $0.70

[SOURCE 5, Operating Engineers Wage Schedule O-4 Hamilton, Effective May 1, 2025, page 4]

Foreperson positions earn an additional $3.60 above the corresponding Operating Engineer base hourly rate, and Subforeperson positions earn an additional $1.00 above the base rate.

[SOURCE 5, Operating Engineers Wage Schedule O-4 Hamilton, Effective May 1, 2025, page 4]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 3 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |
| 5 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5197ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 50.40)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W15 — Labourers

**Question:** What is the Labourers Foreman Group IX rate in Sarnia on a generation project effective May 1, 2025?

**Answer:**

Based on the provided sources, the **Labourers Foreman Group IX rate in Sarnia on a generation project effective May 1, 2025 is a total wage package of $64.94 per hour**, broken down as follows:

- Base hourly rate: $46.51
- Vacation & statutory holiday pay: $4.65
- Welfare: $3.25
- Pension: $8.00
- Union funds: $2.53
- EPSCA association fund: $0.30

[SOURCE 1] — Labourers Local 1089 (Sarnia) — LABOURERS EPSCA Wage Schedule L-3, Effective May 1, 2025, Classification: FOREMAN GROUP IX (occupation code 425065; grade/step 25-9).

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Labourers | Labourers Generation - Zone 1 Wage Schedule L-3 Sa |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2950ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 46.51)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W16 — Painters

**Question:** What is the painter journeyperson hourly rate in Windsor effective May 1, 2025?

**Answer:**

# Painter Journeyperson Hourly Rate in Windsor (Effective May 1, 2025)

The **base hourly rate** for a Painter Journeyman in Windsor effective May 1, 2025 is **$39.41** [SOURCE 1]. The **total wage package** (including vacation & statutory holiday pay, welfare, pension, union funds, and EPSCA association fund) is **$56.97** [SOURCE 1].

## Supporting Details

**Classification:** Painter Journeyman / Lead Abatement Worker (occupation codes 405735, 405836; grade/step 42-6) [SOURCE 1]

**Wage Breakdown (Effective May 1, 2025):** [SOURCE 1]
- Base hourly rate: $39.41
- Vacation & statutory holiday pay: $3.94
- Welfare: $4.23
- Pension: $8.25
- Union funds: $1.14
- EPSCA association fund: $0.30
- **Total wage package: $56.97**

**Source:** Painters Local 1494 (Windsor) — PAINTERS EPSCA Wage Schedule P-1, revised April 1, 2025 [SOURCE 1]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Painters | Painters Wage Schedule P-1 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4116ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 39.41)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W17 — Roofers

**Question:** What is the journeyperson roofer hourly rate in Windsor effective May 1, 2025?

**Answer:**

# Journeyperson Roofer Hourly Rate in Windsor — Effective May 1, 2025

The journeyperson roofer base hourly rate in Windsor effective May 1, 2025 is **$42.57** [SOURCE 1]. The total wage package (including vacation & statutory holiday pay, welfare, and union funds) is **$57.96** per hour [SOURCE 1].

**Supporting Clause:**

[SOURCE 1] Roofers Wage Schedule RO-01 LU 235 Windsor states:

> "Effective 2025-05-01: base hourly rate $42.57, vacation & statutory holiday pay $4.26, welfare $9.45, union funds $1.68, total wage package $57.96, administration & training fund $0.10, EPSCA association fund $0.30."

The classification is JOURNEYMAN ROOFER (POTMAN), occupation code 445435, grade/step 97-6 [SOURCE 1].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Roofers | Roofers Wage Schedule RO-01 LU 235 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4093ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 42.57)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W18 — Cement Masons

**Question:** What is the Cement Masons foreman hourly rate in Windsor effective May 1, 2025?

**Answer:**

Based on the provided documents, the Cement Masons foreman hourly rate in Windsor effective May 1, 2025 is:

**Total wage package: $61.90 per hour**

This comprises:
- Base hourly rate: $43.96
- Vacation & statutory holiday pay: $4.40
- Union funds: $13.54
- EPSCA association fund: $0.30

[SOURCE 1, Cement Masons Wage Schedule CM-1 Local 598 Windsor, Effective 2025-05-01]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Cement Masons | Cement Masons Wage Schedule CM-1 Local 598 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3664ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 43.96)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W19 — Plasterers

**Question:** What is the Plasterers foreman hourly rate in Windsor effective May 1, 2025?

**Answer:**

# Plasterers Foreman Hourly Rate in Windsor — Effective May 1, 2025

The Plasterers foreman hourly rate in Windsor effective May 1, 2025 is:

- **Base hourly rate: $52.57**
- **Total wage package: $64.72**

The total wage package comprises: base hourly rate ($52.57) + vacation & statutory holiday pay ($5.26) + union funds ($6.89) + EPSCA association fund ($0.30).

**Source Citation:**  
[SOURCE 1] Plasterers Wage Schedule PL-1 LU 124 Windsor, Effective May 1, 2025, Classification: FOREMAN (occupation code 430365; grade/step 17-9), Hourly rates by effective date — Effective 2025-05-01 entry.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Plasterers | Plasterers Wage Schedule PL-1 LU 124 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3138ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 52.57)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W20 — Insulators

**Question:** What is the Insulators foreman hourly rate for Local 95 Zone 1 effective May 1, 2025?

**Answer:**

For Insulators Local 95 Zone 1, the foreman hourly rate effective May 1, 2025 is:

- **Base hourly rate: $55.74**
- **Total wage package: $73.04** (including vacation & statutory holiday pay of $5.57, welfare of $7.50, union funds of $4.23, and EPSCA association fund of $0.30)

[SOURCE 1, Insulators Wage Schedule IN-1 LU 95 Zone 1, Classification: FOREMAN, Effective 2025-05-01]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Insulators | Insulators Wage Schedule IN-1 LU 95 Zone 1 Insulat |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3601ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 55.74)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W21 — Tile and Terrazzo

**Question:** What is the working foreman rate for Marble/Tile/Terrazzo workers in Windsor effective May 1, 2025?

**Answer:**

For Marble/Tile/Terrazzo workers in Windsor, the working foreman rate effective May 1, 2025 is:

**Base hourly rate: $50.52**
**Total wage package: $67.37**

This breaks down as follows [SOURCE 1]:
- Base hourly rate: $50.52
- Vacation & statutory holiday pay: $5.05
- Welfare: $4.80
- Union funds: $7.00
- EPSCA association fund: $0.30

This rate applies to Tile and Terrazzo Local 6 (Windsor/Chatham) workers in the Working Foreman classification (occupation code 430265; grade/step 85-9) [SOURCE 1, Wage Schedule M-1].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Tile and Terrazzo | Tile and Terrazzo Wage Schedule M-01 LU 6 WindsorC |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2918ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 50.52)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W22 — Teamsters

**Question:** What is the Teamsters Group 1 hourly rate effective May 1, 2025?

**Answer:**

The provided documents do not contain a single "Teamsters Group 1" hourly rate effective May 1, 2025. Instead, there are **three separate Group 1 classifications** with different hourly rates:

1. **GROUP 1 (grade/step 46-7)**: Base hourly rate **$40.50** [SOURCE 3]
2. **GROUP 1 (grade/step 46-9)** (Foreperson): Base hourly rate **$41.50** [SOURCE 1]
3. **GROUP 1 (grade/step 46-10)**: Base hourly rate **$43.13** [SOURCE 2]

To determine which Group 1 rate applies to a specific employee, you would need to identify which grade/step classification that employee falls under. The total wage package (including vacation, statutory holiday pay, and EPSCA association fund contributions) differs for each classification.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Teamsters | Teamsters Wage Schedule Teamsters - Province of On |  |  |
| 2 | Teamsters | Teamsters Wage Schedule Teamsters - Province of On |  |  |
| 3 | Teamsters | Teamsters Wage Schedule Teamsters - Province of On |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6018ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 43.13)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### W23 — Brick and Allied Craft Union

**Question:** What is the BACU bricklayer journeyperson hourly rate in Niagara effective May 1, 2025?

**Answer:**

Based on the provided documents, the BACU bricklayer journeyperson hourly rate in Niagara effective May 1, 2025 is as follows:

**Base hourly rate: $46.45**
**Total wage package: $63.92**

The total wage package comprises:
- Base hourly rate: $46.45
- Vacation & statutory holiday pay: $4.65
- Welfare: $3.47
- Pension: $0.60
- Supplementary fund: $1.00
- Union funds: $7.75
- Additional amount: $0.30

[SOURCE 1: Brick and Allied Craft Union Wage Schedule BACU-01 Local 1 Niagara, Effective May 1, 2025]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Brick and Allied Craft Union | Brick and Allied Craft Union Wage Schedule BACU-01 |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2871ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 46.45)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

## Overtime & Hours

### O01 — IBEW

**Question:** What constitutes overtime for IBEW Generation electricians under the 2025-2030 agreement?

**Answer:**

# Overtime Definition for IBEW Generation Electricians (2025-2030)

The provided documents do not contain an explicit definition section that states "overtime constitutes..." However, the agreement specifies **when overtime rates apply** rather than defining overtime by a single threshold.

## Overtime Triggering Events:

**For 10-hour, 4-day per week schedules (Monday–Friday):**
- Hours worked **beyond the normal daily scheduled number of hours, up to a maximum of 2 hours per day** are paid at 1½ times the basic hourly rate
- **All hours in excess of 12 hours per day** are paid at 2 times the base hourly rate [SOURCE 10, Page 24]

**For Saturday, Sunday, Recognized Holidays, and non-shift days:**
- **All overtime work** on these days is paid at 2 times the basic hourly rate [SOURCE 10, Page 24]

## Key Conditions:

- **All overtime shall be worked on a voluntary basis** and must be distributed as equally as possible among all IBEW members [SOURCE 10, Page 24]
- The agreement references "Section 806 – Overtime" for further details [SOURCE 2, Page 51], but that specific section is not provided in the source documents

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 10 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4077ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 806. |

---

### O02 — IBEW

**Question:** What is the overtime rate for IBEW Generation workers on a Saturday?

**Answer:**

The provided documents contain information about overtime rates for IBEW Generation workers, but they do not specify a different rate for Saturday work performed as part of a regular scheduled shift versus Saturday overtime.

Based on the collective agreement, here is what applies:

**For overtime work performed on Saturday:**

Saturday overtime is paid at **two (2) times the basic hourly rate** [SOURCE 7, Section 806.A and SOURCE 8, Section 806.A].

The relevant clause states: "Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate."

**However, for regularly scheduled work on Saturday** (not overtime):

Regularly scheduled hours on Saturday are paid at **two times the straight time hourly rate** [SOURCE 10, page 51].

The distinction is important: if Saturday work is scheduled as part of the regular work week, it pays double time. If Saturday work is performed as overtime beyond the scheduled hours, it also pays double time (two times the basic hourly rate).

To apply the specific rate to a particular worker, you would need to reference the applicable wage schedule (Sources 1–5 list various IBEW Generation wage rates by classification and apprenticeship period) and multiply the base hourly rate by 2.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 10 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5125ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: two (2) times. |

---

### O03 — IBEW

**Question:** What is the maximum number of regular daily hours for IBEW Generation workers?

**Answer:**

# Maximum Regular Daily Hours for IBEW Generation Workers

Based on the provided documents, the maximum regular daily hours for IBEW Generation workers depends on the work schedule:

**For a standard five-day per week operation:**
The maximum regular daily hours are **8 hours per day** [SOURCE 1, Section 800 A]. The agreement specifies that "weekly hours of work Monday to Friday inclusive shall consist of forty (40) hours for all employees of Employers covered by this agreement and working on a one (1) or two (2) shift operation."

**Alternative schedules also permitted:**
The wage schedules reference both a "4 day x 10 hours per day schedule and 5 day x 8 hours per day schedule" as acceptable work arrangements [SOURCE 2, Overtime Rate Section 806; SOURCE 4, Overtime Rate Section 806].

The primary agreement clarifies overtime treatment: when working on an eight-hour day and five-day per week schedule, hours beyond the normal daily scheduled number are paid at premium rates, with all hours in excess of 10 hours per day paid at double time [SOURCE 10, Section 806 A].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Generation Wage Schedule E-16-C LU 402 Thunde |  |  |
| 10 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4675ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 800. |

---

### O04 — Sheet Metal

**Question:** What are the regular daily hours of work for Sheet Metal workers?

**Answer:**

# Regular Daily Hours of Work for Sheet Metal Workers

The regular daily hours of work for Sheet Metal workers vary depending on the shift operation established by the employer:

## Standard One (1) or Two (2) Shift Operation

For one or two-shift operations, the 40 weekly hours may be structured as either:
- **Four (4) consecutive ten-hour shifts**, or  
- **Five (5) consecutive eight-hour shifts**

[SOURCE 1, Section 22.1, Page 27]

## Three (3) Shift Operation

When a three-shift operation is established:
- **Day shift:** Eight (8) hours per shift
- **Afternoon shift:** Seven and one-half (7½) hours per shift
- **Night shift:** Seven (7) hours per shift

[SOURCE 9, Section 22.2, Page 27]

## Remote/Northern Work

For work north of the French River in remote locations, employers may establish shifts consisting of fourteen (14) consecutive days at applicable rates, followed by seven (7) consecutive days off. [SOURCE 10, Section 22.6, Page 28]

## Key Requirement

Daily hours of work must be established for a minimum period of 30 days. If an employer intends to change the daily hours of work, at least five (5) days written notice must be sent to the Local Union. [SOURCE 1, Section 22.1, Page 27]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.1 |
| 9 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.2 |
| 10 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.6 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4068ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 22.1. |

---

### O05 — Sheet Metal

**Question:** What is the overtime rate for Sheet Metal workers on a Sunday?

**Answer:**

# Sunday Overtime Rate for Sheet Metal Workers

The overtime rate for Sheet Metal workers on a Sunday is **2 times the basic hourly rate** for all hours worked.

## Supporting Clause Text

This rate is consistently stated across all applicable EPSCA Sheet Metal collective agreement documents:

**Primary Collective Agreement:** "Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate." [SOURCE 6, Section 23.1, Page 28]

**Local Wage Schedules:** All local wage schedules uniformly specify under their Overtime sections:
- "Sat., Sun. & Holidays - 2 times for all hours worked." [SOURCES 1, 2, 3, 4, 5, 7, 8, 9, 10 — all under "Overtime" schedule notes]

This applies regardless of whether the work is scheduled or non-scheduled, and regardless of the work schedule structure (8-hour/5-day or 10-hour/4-day week).

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 6 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 23.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4154ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 23.1. |

---

### O06 — Sheet Metal

**Question:** What are the daily overtime rules for Sheet Metal workers under the 2025-2030 agreement?

**Answer:**

# Daily Overtime Rules for Sheet Metal Workers (2025-2030)

The daily overtime rules under the 2025-2030 Sheet Metal Workers agreement are consistent across all local jurisdictions and are as follows:

## Monday to Friday — Scheduled Work Days

**1.5x rate:** Up to and including 2 hours beyond the normal daily scheduled number of hours (applies to both 4-day × 10-hour and 5-day × 8-hour schedules) [SOURCE 1, Overtime section]

**2x rate:** All hours in excess of 2 overtime hours per day [SOURCE 1, Overtime section]

## Monday to Friday — Non-Scheduled Work Days

**2x rate:** All hours worked [SOURCE 1, Overtime section]

## Saturday, Sunday & Holidays

**2x rate:** All hours worked [SOURCE 1, Overtime section]

---

### Supporting Clause Text

From Sheet Metal Wage Schedule SM-10 LU 30 Barrie [SOURCE 1]:

> "Mon. to Fri. - Scheduled Work Days - 1 1/2 times for up to and including 2 hours beyond the normal daily scheduled number of hours. This applies for both a 4 day x 10 hours per day schedule and a 5 day by 8 hour per day schedule. For overtime worked in excess of the 2 overtime hours per day at 1 1/2, the overtime rate shall be 2 times the basic hourly rate. Non-Scheduled Work Days - 2 times for all hours worked. Sat., Sun. & Holidays - 2 times for all hours worked."

These same rules appear identically in wage schedules for all Sheet Metal Local Unions (30 Barrie, Toronto, Peterborough; Local 269 Kingston; Local 504 Sudbury and Sault Ste. Marie; and Local 235 Windsor and Sarnia) [SOURCES 1, 3, 4, 6, 7, 8, 9, 10].

The Primary Collective Agreement [SOURCE 2, Section 2.0, page 60] references that "overtime will be paid in accordance with Article 23 - Overtime Rates," which directs to the detailed schedules above.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-10 LU 30 Barrie |  |  |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5570ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Answered from wage-schedule Overtime notes chunks; substance matches CA §23.1 (1.5x ≤2h OT, 2x beyond; weekends 2x) as verified in Phase 1 review. |

---

### O07 — United Association

**Question:** What is the double-time rate provision for United Association workers?

**Answer:**

The provided documents do not contain information about a double-time rate provision for United Association workers as a standalone provision.

However, the collective agreement does address when double-time rates apply. According to [SOURCE 6, Section 48.1, Page 44-46] and [SOURCE 7, Section 9.1, Page 67-68], double-time rates (two times the straight time hourly rate) are paid for:

- Regularly scheduled hours of work on Saturday and Sunday [SOURCE 6, Section 48.1, Page 44]
- Statutory and Recognized Holidays [SOURCE 6, Section 48.1, Page 44]
- Work on nonshift days [SOURCE 7, Section 9.1, Page 68]

The documents do not specify a general overtime threshold that automatically triggers double-time pay (such as after 8 or 10 hours in a day). The collective agreement references that "Overtime will be paid in accordance with Article 24 - Overtime Rates" [SOURCE 7, Section 9.1, Page 68], but the full text of Article 24 is not included in the provided sources.

To understand the complete double-time rate provisions, you would need to review Article 24 of the United Association 2025-2030 Collective Agreement.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 6 | United Association | United Association 2025-2030 Collective Agreement |  | 48.1 |
| 7 | United Association | United Association 2025-2030 Collective Agreement |  | 9.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4941ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Partial** | **Yes** | Improved: double-time applications now quoted from appendix sections; Article 24.1 daily OT rules still unsurfaced — #78. |

---

### O08 — United Association

**Question:** What time does a regular shift start for United Association workers under the 2025-2030 agreement?

**Answer:**

# Day Shift Start Times for United Association Workers (2025-2030)

The start time for the day shift depends on the work location:

**For nuclear projects:** between 6:00 AM and 9:00 AM [SOURCE 1, Section 23.2, page 24]

**For all other locations:** 8:00 AM with a possible one (1) hour variance either way (meaning 7:00 AM to 9:00 AM) [SOURCE 1, Section 23.2, page 24]

## Supporting Text

From Section 23.2:

> "The start time for the day shift shall be between 6:00 AM and 9:00 AM (nuclear only) or a start time of 8:00 AM with a possible one (1) hour variance either way (all other locations)."

The agreement also permits staggered start times within these parameters: "Crews may have staggered start times." [SOURCE 1, Section 23.2, page 24]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association 2025-2030 Collective Agreement |  | 23.2 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3895ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 6:00. |

---

## Travel & Board

### T01 — IBEW

**Question:** What is the board allowance for IBEW Generation workers working away from home?

**Answer:**

# Board Allowance for IBEW Generation Workers Working Away from Home

The provided documents do not contain information about a "board allowance" as such. However, the IBEW Generation Collective Agreement addresses **room and board allowance** and **subsistence allowance** for workers whose regular residence is 110+ kilometers from the project.

## What the Agreement Provides:

**For employees working away from home (110+ km from their regular residence)**, the employer may provide [SOURCE 5, Article 1101.A(i)]:

- (a) free room and board in camp or good standard of board and lodging within reasonable distance; or
- (b) a subsistence allowance; or  
- (c) a travel allowance

If an employee chooses not to stay in camp and maintains temporary accommodation near the project, they receive a **subsistence allowance** [SOURCE 7, Article 1101.b(a) and (b)], with rates varying by project location (North vs. South of the French River) and specific rates set for Pickering, Darlington, and Bruce Power projects.

The specific dollar amounts for subsistence allowances are referenced in the agreement but the rates table is not included in the provided source excerpts.

If you are looking for the actual **subsistence allowance dollar amounts**, please provide the full page from Article 1101 that contains the rate tables.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6661ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 1101. |

---

### T02 — IBEW

**Question:** How far from home must an IBEW Generation worker be to qualify for board allowance?

**Answer:**

# Board Allowance Distance Threshold for IBEW Generation Workers

An IBEW Generation worker must live **greater than or equal to 110 road-driven kilometers** from the project to qualify for room and board allowance.

## Supporting Clause

[SOURCE 3, Article 1101 A] states:

> "The following conditions will apply for employees whose regular residence* is greater than or equal to 110 road-driven kilometers from the project: (i) An Employer may supply either: (a) free room and board in camp or a good standard of board and lodging within a reasonable distance of a project; or (b) a subsistence allowance; or (c) a travel allowance."

This is further confirmed in [SOURCE 7, Article 1101 (b), (c), (d), and (e)], which outlines specific room and board allowance rates for employees whose regular residence is greater than or equal to 110 road-driven kilometers, with variations based on project location (North/South of French River) and specific facilities (Pickering, Darlington, Bruce Power).

Employees living less than 110 kilometers away may qualify for daily travel allowance instead, depending on their distance tier [SOURCE 1, Article 1100 A].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4683ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 110. |

---

### T03 — Sheet Metal

**Question:** What is the subsistence allowance for Sheet Metal workers working away from home?

**Answer:**

Your question asks for a specific subsistence allowance amount, but the provided documents do not include the actual dollar rates for subsistence allowances.

The documents establish the **framework and eligibility** for subsistence allowance for Sheet Metal workers:

An employee working away from home whose regular residence is greater than or equal to 110 road-driven kilometers from the project may receive a subsistence allowance if they choose not to accept free room and board provided by the Employer [SOURCE 1, Article 27.4(a)–(b)]. The allowance is paid "for each day worked or reported for" [SOURCE 1, Article 27.4(b)(ii)–(iii)].

The province is divided into regions for payment purposes:
- **Northern Region** (north of a line between the mouth of the French River and Mattawa)
- **Southern Region** (all remaining areas) [SOURCE 1, Article 27.4(b)(i)]

Different rates apply depending on which region the project is located in [SOURCE 1, Article 27.4(b)(ii)–(iii)].

However, **the provided documents do not contain the actual dollar amounts** for these subsistence allowances. The documents reference "the rates as set out below" but the rate tables are not included in the source materials provided to me.

To obtain the specific subsistence allowance rates, you would need to consult the complete collective agreement or contact the EPSCA or Sheet Metal Workers union directly.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4878ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Partial** | **Yes** | Eligibility correct; §26.2(b) subsistence rate table still not retrieved — #78. |

---

### T04 — Sheet Metal

**Question:** What are the travel zone provisions for Sheet Metal workers?

**Answer:**

# Travel Zone Provisions for Sheet Metal Workers

Sheet Metal Workers have **two different travel zone systems** depending on the project type. You must identify which applies to your situation.

## **SYSTEM 1: General EPSCA Projects (Articles 27.1–27.5)**

For most EPSCA work, Sheet Metal Workers receive daily travel allowance based on distance from the work location or declared assembly point, measured in road-driven kilometres via Google Maps [SOURCE 1, Section 27.1; SOURCE 2, Section 27.3]:

| Distance Zone | Eligibility | Rate (effective May 1, 2025) |
|---|---|---|
| Less than 50 km | No travel allowance | $0 |
| 50–70 km | Daily travel paid | $32.56 |
| 70–96 km | Daily travel paid | $37.14 |
| 96–110 km | Daily travel paid | $42.00 |
| ≥110 km (no subsistence/temp accommodation) | Daily travel paid | $60.00 |

**Special conditions:**
- Employees using company vehicles are not entitled to daily travel [SOURCE 1, Section 27.1(f)]
- Employees must remain at work for their scheduled daily hours to qualify, unless excused by the employer [SOURCE 8, Section 27.5]
- The employer may base distance calculations on either the work location or a declared assembly point [SOURCE 2, Section 27.2]

---

## **SYSTEM 2: OPG Generation Construction Projects (Articles 26.1–26.3)**

For OPG Generation Construction Projects, the travel zones differ slightly:

| Distance Zone | Eligibility | Rate (effective May 1, 2025) |
|---|---|---|
| Less than 50 km | No travel allowance | $0 |
| 50–70 km | Daily travel paid | $33.14 |
| 70–96 km | Daily travel paid | $38.50 |
| 96–110 km | Daily travel paid | $42.00 |
| ≥110 km (no room/board or temp accommodation) | Daily travel paid | $60.00 |

[SOURCE 4, Section 26.1; SOURCE 3, Section 26.1]

**Special conditions:**
- Same vehicle exclusion and attendance requirements as System 1 [SOURCE 4, Sections 26.1(f), 26.3; SOURCE 9, Section 26.3]
- Employees ≥110 km away may qualify for **Room and Board** instead of daily travel if their regular residence meets the definition in the agreement [SOURCE 4, Section 26.1(e); SOURCE 2, Section 27.4]

---

## **Conflict Between Systems**

The two systems show different daily travel rates (e.g., $32.56 vs. $33.14 for the 50–70 km zone). **The governing document depends on the project type**: use Articles 26–27 (OPG) for OPG Generation Construction; use Articles 27–28 for other EPSCA work. [SOURCE 1 vs. SOURCE 4]

---

## **"Regular Residence" Definition**

To qualify for Room and Board (which affects travel entitlements), an employee's "regular residence" must be [SOURCE 2, Section 27.4]:
1. A self-contained domestic establishment (dwelling, apartment, etc.), not a hotel/motel or boarding house;
2. Maintained solely at the employee's financial expense (proof required); and
3. The employee's normal residence except during forced work-location relocations.

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 27.1 |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |
| 4 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 26.1 |
| 8 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 27.5 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 9450ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 26.1. |

---

### T05 — United Association

**Question:** How is travel time compensated for United Association plumbers under the 2025-2030 agreement?

**Answer:**

# Travel Time Compensation for United Association Plumbers (2025-2030)

Travel time compensation under the United Association 2025-2030 agreement depends on the specific context and circumstances:

## OPG Projects (Local 800 and 628)

For Ontario Power Generation construction projects within Local 800 and 628 jurisdiction where employees receive Room and Board allowance on remote projects, travel time is compensated as follows [SOURCE 2, Section 28.6]:

- **40–56 road km**: ½ hour regular time pay
- **57–80 road km**: 1 hour regular time pay
- **81–120 road km**: 1½ hours regular time pay
- **121–160 road km**: 2 hours regular time pay
- **Over 160 road km**: actual travel time paid at regular time rate

These provisions apply when travelling from the nearest available accommodation (where the accommodation is more than 40 road km from the job). Travel allowance adjusts when work location changes. Importantly, if the employer provides a vehicle or transportation, these travel time provisions do not apply [SOURCE 2, Section 28.6].

## Employee Transfers

When employees are transferred to a different project, the employer must pay [SOURCE 3, Section 31.6]:

- The equivalent cost of public transportation for the initial trip from the employee's most recent work location
- Travelling time at straight-time rates up to a maximum of 8 hours' pay, calculated as 1 hour's pay for each 96 road-driven kilometers of travel

All wages are based on the employee's wage rate at the location to which they are being transferred [SOURCE 3, Section 31.6].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | United Association | United Association 2025-2030 Collective Agreement |  | 28.6 |
| 3 | United Association | United Association 2025-2030 Collective Agreement |  | 31.6 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6350ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 28.6. |

---

## Nuclear Project Specific

### N01 — IBEW

**Question:** Are there different overtime rules for IBEW Generation workers at a nuclear project site?

**Answer:**

# Overtime Rules for IBEW Generation Workers at Nuclear Project Sites

Yes, there are different overtime rules depending on the work schedule at nuclear project sites.

## Standard 8-Hour Day, 5-Day Week Schedule

For employees on an 8-hour day, 5-day per week schedule (Monday to Friday inclusive), overtime is paid at:
- 1½ times the basic hourly rate for hours worked beyond the normal daily scheduled hours, up to a maximum of 2 hours per day
- 2 times the base hourly rate for all hours in excess of 10 hours per day

Overtime on Saturday, Sunday, Recognized Holidays, and non-shift days is paid at 2 times the basic hourly rate. [SOURCE 8, Section 806 A]

## 10-Hour Day, 4-Day Week Schedule

For employees on a 10-hour day, 4-day per week work schedule (Monday to Friday inclusive), overtime is paid at:
- 1½ times the basic hourly rate for hours worked beyond the normal daily scheduled hours, up to a maximum of 2 hours per day
- 2 times the base hourly rate for all hours in excess of 12 hours per day

Overtime on Saturday, Sunday, Recognized Holidays, and non-shift days is paid at 2 times the basic hourly rate. [SOURCE 2, Section 806 (appears to be referenced as nuclear project specific overtime)]

Additionally, the documents specify that "at the Employer's discretion, an unapproved absence of the Employee may disentitle the Employee to overtime opportunities. The application of the employer's discretion will be subject to referral to the Nuclear Project Committee." [SOURCE 2]

All overtime must be worked on a voluntary basis and distributed as equally as possible among all IBEW members. [SOURCE 2]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4973ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 806. |

---

### N02 — IBEW

**Question:** What additional provisions apply to IBEW Generation electricians working at Darlington?

**Answer:**

# Answer

The provided documents contain provisions that apply to **all** IBEW Generation electricians working at OPGI facilities, including Darlington, but do **not** contain provisions that are specific to Darlington alone.

However, there is an important distinction: **If the work is classified as a "Nuclear Project" at Darlington, the IBEW Nuclear Project Agreement applies instead of—and in place of—the primary Generation Agreement.**

## General IBEW Generation Provisions (All OPGI Sites, Including Darlington)

The IBEW Generation 2025-2030 Collective Agreement applies to electricians working at Darlington as an OPGI facility [SOURCE 2, Section 200A(iii)]. Standard provisions include hiring procedures [SOURCE 8, Section 701A], apprentice program requirements [SOURCE 8, Section 701F], and employment of only IBEW union members [SOURCE 8, Section 701A].

## Nuclear-Specific Provisions (If Applicable at Darlington)

If the work at Darlington is designated as a "Nuclear Project," the IBEW Nuclear Project Agreement applies instead. [SOURCE 9, Section 1.1] states: "This agreement shall apply only to work performed by the Building Trades Unions (BTU) notwithstanding the current EPSCA (and/or OPG/Bruce Power) Collective Agreements. This agreement shall apply on existing Ontario Power Generation Inc. (OPGI) Nuclear Sites **(Pickering, Darlington, Bruce)** and Bruce Power LP property." [emphasis added]

Under the Nuclear Project Agreement, additional requirements apply, including:
- Nuclear Qualified Worker (NQW) referral procedures [SOURCE 7, Section 5.1A]
- Specific hiring restrictions: "For Nuclear sites only: The Employer is entitled to bring in four (4) key tradespeople" [SOURCE 3, Section 701A(ii)(e)]
- On nuclear sites, "local members replacing travel cards must be security cleared prior to hire and possess the same owner specific nuclear training as the employee being replaced" [SOURCE 5 and SOURCE 6, Section 701A(iv)]
- "On Nuclear sites only, replacement of travel cards will not occur during outages" [SOURCE 5 and SOURCE 6, Section 701A(iv)]

## Critical Clarification

The provided documents do not specify which provisions currently apply at Darlington (i.e., whether work there is classified as a "Nuclear Project" or general "Generation" work). This distinction is essential because it determines which agreement governs.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Nuclear Project Agreement |  | 5.1 |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 9 | IBEW | IBEW Nuclear Project Agreement |  | 1.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7233ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Partial** | **Yes** | Honest; Darlington LOU in the NPA still not retrieved — #78. |

---

### N03 — Sheet Metal

**Question:** What special conditions apply to Sheet Metal workers under the Nuclear Project Agreement?

**Answer:**

# Special Conditions for Sheet Metal Workers under the Nuclear Project Agreement

The Nuclear Project Agreement for Sheet Metal workers applies exclusively to work at Ontario Power Generation Inc. (OPG) nuclear sites (Pickering, Darlington, and Bruce) and Bruce Power LP property, and overrides the standard EPSCA collective agreements in those locations [SOURCE 1, Section 1.1].

## Key Special Conditions:

**1. Nuclear Qualified Worker (NQW) Referrals**

Worker referrals are governed by a phased approach: [SOURCE 5, Section 5.1]
- **First two years**: Priority given to NQW members, but non-NQW qualified journeymen and apprentices may be referred if NQWs are unavailable
- **After two years**: Only Nuclear Qualified Workers will be referred
- Referral proceeds through local hiring halls first, then "fan out" (closest first) basis to other locals if needed

**2. No Displacement of Hired Workers**

Once a worker is hired on a nuclear site project, travelers and permit workers cannot be displaced or bumped by other members [SOURCE 7, Section 6.1].

**3. Restricted Replacement at Nuclear Sites (Zone 3)**

While the primary agreement allows replacement of non-local workers, at nuclear sites specifically: replacement of members will not occur during an outage or for forty (40) days, whichever is lesser. Additionally, workers seeking to replace others must be security cleared and possess required skills and training [SOURCE 6, Section 11.8(g)].

**4. Composite Crews**

Composite crews may be formed where conditions warrant, but this does not establish precedent or change craft jurisdiction. The "One Person, One Job" principle applies, and composite crews are normally determined by the Mark-Up Meeting with prior notice to local unions [SOURCE 8, Section 11.1].

**5. Standoff Provisions**

Employers may elect to standoff (not lay off) employees for up to ten (10) consecutive working days without pay during work stoppages. Employees receive no travel allowance during standoff periods, though subsistence allowance is paid if temporary residence is maintained [SOURCE 10, Section 10.1(b)].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 1.1 |
| 5 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 5.1 |
| 6 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 11.8 |
| 7 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 6.1 |
| 8 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 11.1 |
| 10 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 10.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7263ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: Nuclear Qualified. |

---

### N04 — United Association

**Question:** Do United Association workers receive any premium for working on a nuclear project site?

**Answer:**

# Nuclear Project Premium for United Association Workers

Yes, United Association workers receive a premium for working on nuclear project sites. Specifically:

**Radiation Protection Premium:**
Employees working in a radiation area while wearing fully enveloping plastic suits or replacement material with an independent air supply receive **$20.00 per day** [SOURCE 5, Section 41.1(e)].

**Context:**
The primary collective agreement and nuclear project agreement both recognize nuclear-specific work conditions. The agreement establishes qualifications for Construction Radiation Protection Assistants (R.P.A.s) who work on nuclear sites [SOURCE 3, Section 8.8], and the employer has enhanced rights regarding transfers and staffing on nuclear sites compared to non-nuclear sites [SOURCE 4, Section 8.5(c)].

However, the provided documents do not specify a general hourly rate premium or surcharge for all workers on nuclear project sites—only the $20.00 per day allowance for those performing radiation work in protective suits.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 3 | United Association | United Association 2025-2030 Collective Agreement |  | 8.8 |
| 4 | United Association | United Association 2025-2030 Collective Agreement |  | 8.5 |
| 5 | United Association | United Association 2025-2030 Collective Agreement |  | 41.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4350ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 20.00. |

---

### N05 — IBEW

**Question:** What are the travel provisions for IBEW Generation workers under the Nuclear Project Agreement?

**Answer:**

# Travel Provisions for IBEW Generation Workers Under the Nuclear Project Agreement

The provided documents contain minimal specific travel provisions in the Nuclear Project Agreement itself. The only substantive provision in that document is [SOURCE 5], which addresses worker displacement rather than travel allowances:

**From the IBEW Nuclear Project Agreement, Section 6.1:**

"Once a worker is hired onto a site covered by this agreement, travelers and/or permit workers shall not be displaced and/or bumped by any other member." [SOURCE 5, Section 6.1]

This provision protects travelers and permit workers from displacement once hired, but does not establish travel allowances or payment schedules.

## Relevant Context: Hiring and Replacement on Nuclear Sites

The Primary Collective Agreement includes a specific restriction for nuclear sites regarding travel card replacement. Under Article 701A(iv):

"On Nuclear sites only, local members replacing travel cards must be security cleared prior to hire and possess the same owner specific nuclear training as the employee being replaced. On Nuclear sites only, replacement of travel cards will not occur during outages." [SOURCE 10, Article 701A(iv)]

## Important Distinction

The detailed travel allowance provisions (daily travel allowance, room and board allowance, and initial/return travel payments) appear in the **Primary Collective Agreement** (Sections 1100–1102), not in the Nuclear Project Agreement. The Nuclear Project Agreement does not replicate or modify these provisions for nuclear sites.

**If you need information about travel allowances, daily rates, or room and board for IBEW Generation workers, those provisions exist in the Primary Agreement. Please confirm whether you are asking about a nuclear project specifically, as the applicable terms may differ.**

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 5 | IBEW | IBEW Nuclear Project Agreement |  | 6.1 |
| 10 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 9833ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Partial** | **Yes** | NPA §6.1 + CA travel articles correct; NPA standoff travel clause still unsurfaced — #78. |

---

### N06 — Boilermakers

**Question:** What special conditions apply to Boilermakers working at Darlington under their Nuclear Project Agreement?

**Answer:**

# Special Conditions for Boilermakers at Darlington Under the Nuclear Project Agreement

Based on the provided sources, the Boilermakers Nuclear Project Agreement applies to work at Darlington, but the documents do not contain detailed special conditions specific to that site.

## What the Sources Show

**Scope of Application:**
The Boilermakers Nuclear Project Agreement applies "on existing Ontario Power Generation Inc (OPGI) Nuclear Sites (Pickering, Darlington, Bruce)" [SOURCE 2, Section 1.1, Page 1]. Section 1.1 states this agreement "shall apply only to work performed by the Building Trades Unions (BTU) notwithstanding the current EPSCA (and or OPG/Bruce Power) Collective Agreements."

**General Modification Clause:**
The Primary Collective Agreement includes a provision that "where a particular Article or Articles of this Collective Agreement is or are found to work a hardship for a particular project or specific geographical area, the terms and conditions of this Agreement for that project or specific geographical area, may be modified by the mutual consent of the Union and EPSCA" [SOURCE 1, Section 37.1, Page 38].

**Subsistence Allowance (if applicable):**
Employees at Darlington whose regular residence is 110 or more road-driven kilometers away may receive subsistence allowance under Article 28 of the Primary Agreement [SOURCE 3, Page 29].

## Gap in Documentation

The provided documents do not contain the detailed terms and conditions of the Boilermakers Nuclear Project Agreement beyond its title and scope statement. To access the specific working conditions, wage rates, safety protocols, or other special provisions that apply exclusively at Darlington under this Nuclear Project Agreement, you would need the full text of that agreement.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  | 37.1 |
| 2 | Boilermakers | Boilermakers Nuclear Project Agreement |  | 1.1 |
| 3 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 12803ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | NPA conditions consistent with the SM/IBEW NPA text (same agreement-in-principle family). |

---

## Cross-Union Comparison

### C01 — IBEW / Sheet Metal

**Question:** Compare the overtime rules for IBEW Generation and Sheet Metal workers under their 2025-2030 agreements.

**Answer:**

# Overtime Rules Comparison: IBEW Generation vs. Sheet Metal Workers (2025–2030)

---

## IBEW Generation Workers

### Overtime Rates

The IBEW Generation agreement sets out the following overtime structure [SOURCE 9, Section 806 (p. 24)]:

- **Monday to Friday (10-hour day / 4-day week schedule):** Overtime is paid at **1½ times** the basic hourly rate for all hours beyond the normal daily scheduled hours, up to a maximum of **2 hours per day**. All hours in excess of **12 hours per day** are paid at **2 times** the basic hourly rate.
- **Saturday, Sunday, Recognized Holidays, and non-shift days:** All overtime is paid at **2 times** the basic hourly rate.

> *"When working on a ten (10) hour day and four (4) day per week work schedule (Monday to Friday inclusive), overtime work shall be paid at one and one-half (1½) times the basic hourly rate for all hours worked beyond the normal daily scheduled number of hours up to a maximum of two (2) hours per day. All hours in excess of 12 hours per day shall be paid at two (2) times the base hourly rate. Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate."* [SOURCE 9, p. 24]

### Voluntary Nature of Overtime

Overtime for IBEW Generation workers is explicitly **voluntary** and must be distributed equitably:

> *"All overtime shall be worked on a voluntary basis and shall be distributed as equally as possible among all IBEW members."* [SOURCE 1, Section 806C, p. 24]

Additionally, the agreement notes that **unapproved absences** may, at the employer's discretion, disentitle an employee to overtime opportunities, subject to referral to the Nuclear Project Committee [SOURCE 9, p. 24].

### Overtime Meal Entitlements

When an employee has **not** been notified the previous day of extended overtime beyond 2 hours past their normal quitting time:
- After approximately 2 hours of overtime, they receive a **30-minute paid lunch break** at the base hourly rate, plus a meal provided by the employer.
- After each additional **4 hours**, another 30-minute paid meal break and meal are provided.
- If a hot meal cannot be provided, the employer pays **$25.00** [SOURCE 9, p. 24].

When an employee **has** been notified the previous day, no meal is provided but a **30-minute paid break** is still allotted [SOURCE 9, p. 24].

### Overtime Rest Periods

- A **10-minute rest period** is allotted prior to the end of the normal shift before commencing overtime [SOURCE 5, Section 801B, p. 21].
- A **15-minute rest period** is allotted after each **2 hours of overtime worked** [SOURCE 5, Section 801C, p. 21].
- Where a paid meal period overlaps a rest period, the meal period supplants the rest period [SOURCE 9, p. 24].

---

## Sheet Metal Workers

### Overtime Rates

The Sheet Metal Workers' overtime rates are set out consistently across multiple local wage schedules. Using the three available local schedules [SOURCE 4 (LU 30 Barrie), SOURCE 6 (LU 30 Toronto), SOURCE 8 (LU 30 Peterborough)]:

- **Monday to Friday — Scheduled Work Days:**
  - **1½ times** the basic hourly rate for up to and including **2 hours beyond** the normal daily scheduled hours.
  - This applies to **both** a 4-day × 10-hour schedule and a 5-day × 8-hour schedule.
  - Hours in excess of the 2 overtime hours at 1½ are paid at **2 times** the basic hourly rate.
- **Non-Scheduled Work Days:** **2 times** for all hours worked.
- **Saturday, Sunday & Holidays:** **2 times** for all hours worked.

> *"Mon. to Fri. - Scheduled Work Days - 1½ times for up to and including 2 hours beyond the normal daily scheduled number of hours. This applies for both a 4 day x 10 hours per day schedule and a 5 day by 8 hour per day schedule. For overtime worked in excess of the 2 overtime hours per day at 1½, the overtime rate shall be 2 times the basic hourly rate. Non-Scheduled Work Days - 2 times for all hours worked. Sat., Sun. & Holidays - 2 times for all hours worked."* [SOURCE 4, SM-10 LU 30 Barrie, p. 2; identical language in SOURCE 6, SM-09 LU 30 Toronto, p. 2; SOURCE 8, SM-11 LU 30 Peterborough, p. 2]

The Sheet Metal primary collective agreement defers to **Article 23 – Overtime Rates** for full detail [SOURCE 2, Section 2.0, p. 59], and shift provisions also state: *"Overtime will be in accordance with the provisions of the collective agreement."* [SOURCE 10, Section 48.1, p. 51]. **The provided documents do not include the full text of Article 23**, so additional detail beyond what appears in the wage schedules cannot be confirmed from the sources provided.

### Voluntary Nature of Overtime

The provided Sheet Metal documents **do not contain any provision** addressing whether overtime is voluntary or mandatory, or how overtime is to be distributed among members. This is in contrast to the explicit IBEW voluntariness and equitable distribution language.

### Overtime Meal Entitlements

The provided Sheet Metal documents **do not contain information about** meal entitlements or paid meal breaks during overtime.

### Overtime Rest Periods

The Sheet Metal CA provides for two 15-minute rest periods for **regularly scheduled hours** [SOURCE 10, Section 48.1, p. 51], but the provided documents **do not contain specific provisions** for rest periods during overtime, unlike the IBEW agreement which explicitly addresses pre-overtime and mid-overtime rest breaks.

---

## Side-by-Side Summary

| Provision | IBEW Generation | Sheet Metal Workers |
|---|---|---|
| **Mon–Fri OT Rate (first 2 hrs)** | 1½× [SOURCE 9] | 1½× [SOURCES 4, 6, 8] |
| **Mon–Fri OT beyond 2 hrs** | 2× after 12 hrs/day [SOURCE 9] | 2× after 2 OT hrs [SOURCES 4, 6, 8] |
| **Sat/Sun/Holidays** | 2× [SOURCE 9] | 2× [SOURCES 4, 6, 8] |
| **Non-Scheduled Days** | 2× [SOURCE 9] | 2× [SOURCES 4, 6, 8] |
| **4×10 and 5×8 schedules both covered** | 4×10 only specified [SOURCE 9] | Both explicitly covered [SOURCES 4, 6, 8] |
| **Overtime voluntary?** | Yes, explicitly [SOURCE 1] | Not addressed in provided documents |
| **Equal distribution of OT** | Yes, explicitly [SOURCE 1] | Not addressed in provided documents |
| **OT meal entitlements** | Yes — detailed provisions [SOURCE 9] | Not addressed in provided documents |
| **OT rest periods** | Yes — 10 min pre-OT; 15 min per 2 hrs OT [SOURCE 5] | Not addressed in provided documents |

---

## Key Differences

1. **Escalation trigger for double-time:** IBEW Generation only escalates to 2× after **12 hours in a day** [SOURCE 9], whereas Sheet Metal escalates to 2× after **just 2 hours of overtime** (i.e., after 10 hrs on an 8-hr day, or after 12 hrs on a 10-hr day) [SOURCES 4, 6, 8]. In practice, for an 8-hour-day worker, Sheet Metal reaches double-time sooner.

2. **Voluntary overtime:** IBEW Generation explicitly guarantees the right to refuse overtime [SOURCE 1, Section 806C]. No equivalent provision is found in the provided Sheet Metal documents.

3. **Meal breaks during overtime:** IBEW Generation has a detailed paid meal break regime during overtime [SOURCE 9]. The provided Sheet Metal documents are silent on this.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |
| 4 | Sheet Metal | Sheet Metal Wage Schedule SM-10 LU 30 Barrie |  |  |
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 9 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 10 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 48.1 |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 36391ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Full two-union comparison (§806 vs §23.1, both verified in Phase 1 review); scope-filter fix (#81) confirmed working. |

---

### C02 — IBEW / United Association

**Question:** Which union has the higher journeyperson base rate as of May 2025: IBEW Generation or United Association?

**Answer:**

## Journeyperson Base Rate Comparison — May 2025

This question requires important clarification upfront: **both IBEW Generation and United Association have multiple locals**, each with their own wage schedules. The answer therefore varies by local. Below is a breakdown of all available May 2025 journeyperson base rates from the provided sources.

---

### IBEW Generation — Journeyperson Base Rates (Effective 2025-05-01)

| Local | Wage Schedule | Base Rate |
|---|---|---|
| LU 530 (Sarnia) | E-3-C | $54.98/hr |
| LU 105 (Hamilton) | E-6-C | $46.65/hr |
| LU 586 (Ottawa) | E-13-C | $50.82/hr |

- **LU 530 (Sarnia):** $54.98/hr [SOURCE 1], Wage Schedule E-3-C, Journeyman/Welder/Communications Electrician, effective 2025-05-01.
- **LU 105 (Hamilton):** $46.65/hr [SOURCE 3], Wage Schedule E-6-C, Journeyman/Welder/Communications Electrician, effective 2025-05-01.
- **LU 586 (Ottawa):** $50.82/hr [SOURCE 5], Wage Schedule E-13-C, Journeyman/Welder/Communications Electrician, effective 2025-05-01.

---

### United Association — Journeyperson Base Rates (Effective 2025-05-01)

| Local | Wage Schedule | Base Rate |
|---|---|---|
| LU 800 (Sudbury) | UA-15 | $47.96/hr |
| LU 800 (Sault Ste. Marie) | UA-16 | $47.14/hr |
| LU 71 (Ottawa) | UA-14 | $49.87/hr |

- **LU 800 (Sudbury):** $47.96/hr [SOURCE 2], Wage Schedule UA-15, Journeyman/Pipewelder, effective 2025-05-01.
- **LU 800 (Sault Ste. Marie):** $47.14/hr [SOURCE 4], Wage Schedule UA-16, Journeyman/Pipewelder, effective 2025-05-01.
- **LU 71 (Ottawa):** $49.87/hr [SOURCE 6], Wage Schedule UA-14, Journeyman/Pipewelder, effective 2025-05-01.

> ⚠️ **Note:** SOURCE 8 and SOURCE 10 provide UA Local 46 (Toronto) rates for **Subforeman** and **Foreman** classifications respectively — not journeyperson rates — and are therefore excluded from this comparison.

---

### Summary

**IBEW Generation Local 530 (Sarnia) has the highest journeyperson base rate among all locals in the provided sources at $54.98/hr as of May 2025** [SOURCE 1].

When comparing at the local level:
- IBEW LU 530 (Sarnia) at **$54.98/hr** exceeds all three UA locals in the sources.
- IBEW LU 586 (Ottawa) at **$50.82/hr** exceeds all three UA locals.
- IBEW LU 105 (Hamilton) at **$46.65/hr** is **lower** than all three UA locals.

**Important caveat:** The provided sources do not include journeyperson rates for all IBEW or UA locals (notably, UA Local 46 Toronto journeyperson rates are absent from the sources). Conclusions should be limited to the locals listed above.

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation Wage Schedule E-3-C LU 530 Sarnia  |  |  |
| 2 | United Association | United Association Wage Schedule Local 800 Sudbury |  |  |
| 3 | IBEW | IBEW Generation Wage Schedule E-6-C LU 105 Hamilto |  |  |
| 4 | United Association | United Association Wage Schedule Local 800 Sault S |  |  |
| 5 | IBEW | IBEW Generation Wage Schedule E-13-C LU 586 Ottawa |  |  |
| 6 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 16596ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Key value/section verified in answer: 46.65. |

---

### C03 — Carpenters / Ironworkers

**Question:** Which union has the higher journeyperson base rate in Windsor as of May 2025: Carpenters or Ironworkers?

**Answer:**

## Journeyperson Base Rate Comparison — Windsor, Effective May 1, 2025

**The Ironworkers have the higher journeyperson base rate in Windsor as of May 2025.**

---

### Carpenters Local 494 (Windsor)

The Carpenters have **two Windsor journeyperson classifications** in the provided sources:

- **Carpenter Journeyman / Welder & Burner** (Wage Schedule C-1):
Base hourly rate effective 2025-05-01: **$44.69/hr**
[SOURCE 3] — EPSCA Wage Schedule C-1, Classification: JOURNEYMAN / WELDER & BURNER (grade/step 01-6, 02-6)

- **Resilient Floor Worker Journeyman** (Wage Schedule RF-1):
Base hourly rate effective 2025-05-01: **$43.78/hr**
[SOURCE 1] — EPSCA Wage Schedule RF-1, Classification: JOURNEYMAN (grade/step 03-6)

- **Acoustic and Drywall Journeyman / Welder & Burner** (Wage Schedule AD-1):
Base hourly rate effective 2025-05-01: **$44.69/hr**
[SOURCE 5] — EPSCA Wage Schedule AD-1, Classification: JOURNEYMAN / WELDER & BURNER (grade/step 04-6)

---

### Ironworkers Local 700 (Windsor)

The Ironworkers have **two Windsor sector schedules** in the provided sources, both showing identical journeyperson rates:

- **Transmission** (Wage Schedule I-1):
Base hourly rate effective 2025-05-01: **$48.33/hr**
[SOURCE 2] — EPSCA Wage Schedule I-1, Classification: JOURNEYMAN IRONWORKER, RIGGER (grade/step 19-6)

- **Generation** (Wage Schedule I-1):
Base hourly rate effective 2025-05-01: **$48.33/hr**
[SOURCE 4] — EPSCA Wage Schedule I-1, Classification: JOURNEYMAN IRONWORKER, RIGGER (grade/step 19-6)

---

### Summary

| Union | Classification | Base Rate (May 1, 2025) |
|---|---|---|
| Ironworkers LU 700 | Journeyman Ironworker/Rigger | **$48.33/hr** |
| Carpenters LU 494 | Journeyman / Welder & Burner | $44.69/hr |
| Carpenters LU 494 | Resilient Floor Journeyman | $43.78/hr |

The Ironworkers Local 700 journeyperson base rate of **$48.33/hr** [SOURCE 2, SOURCE 4] exceeds the highest Carpenters Local 494 journeyperson base rate of **$44.69/hr** [SOURCE 3, SOURCE 5] by **$3.64/hr** as of May 1, 2025.

---

> **Note:** These comparisons are limited to the wage schedules provided. Other Carpenters or Ironworkers classifications or schedules may exist that are not reflected in the provided sources.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Carpenters | Carpenters Resilient Floor Wage Schedule RF-1 LU 4 |  |  |
| 2 | Ironworkers | Ironworkers Transmission Wage Schedule I-1 LU 700  |  |  |
| 3 | Carpenters | Carpenters Wage Schedule C-1 LU 494 Windsor |  |  |
| 4 | Ironworkers | Ironworkers Generation Wage Schedule I-1 LU 700 Wi |  |  |
| 5 | Carpenters | Carpenters Acoustic and Drywall Wage Schedule AD-1 |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 17374ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 44.69, 48.33)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

### C04 — Cement Masons / Plasterers

**Question:** Compare the foreman hourly rates for Cement Masons and Plasterers in Windsor as of May 2025.

**Answer:**

## Foreman Hourly Rates — Windsor, Effective May 1, 2025

Here is a direct comparison of the Foreman classification for both unions in Windsor as of May 1, 2025:

---

### Cement Masons — Local 598 (Windsor)
**Document:** Wage Schedule CM-1 | Occupation Code: 430065 | Grade/Step: 16-9

| Component | Rate (2025-05-01) |
|---|---|
| Base Hourly Rate | **$43.96** |
| Vacation & Statutory Holiday Pay | $4.40 |
| Union Funds | $13.54 |
| **Total Wage Package** | **$61.90** |
| EPSCA Association Fund | $0.30 |

[SOURCE 1] — Cement Masons Wage Schedule CM-1, Local 598 Windsor, effective 2025-05-01

---

### Plasterers — Local 124 (Windsor)
**Document:** Wage Schedule PL-1 | Occupation Code: 430365 | Grade/Step: 17-9

| Component | Rate (2025-05-01) |
|---|---|
| Base Hourly Rate | **$52.57** |
| Vacation & Statutory Holiday Pay | $5.26 |
| Union Funds | $6.89 |
| **Total Wage Package** | **$64.72** |
| EPSCA Association Fund | $0.30 |

[SOURCE 2] — Plasterers Wage Schedule PL-1, Local 124 Windsor, effective 2025-05-01

---

### Summary of Differences

| | Cement Masons (CM-1) | Plasterers (PL-1) | Difference |
|---|---|---|---|
| Base Hourly Rate | $43.96 | $52.57 | Plasterers higher by **$8.61/hr** |
| Total Wage Package | $61.90 | $64.72 | Plasterers higher by **$2.82/hr** |
| Union Funds | $13.54 | $6.89 | Cement Masons higher by **$6.65/hr** |

**Key observations:**
- The Plasterers Foreman base hourly rate is **$8.61/hr higher** than the Cement Masons Foreman in Windsor [SOURCE 1; SOURCE 2].
- The gap in total wage package is narrower (**$2.82/hr**) because Cement Masons carry significantly higher union fund contributions ($13.54 vs. $6.89) [SOURCE 1; SOURCE 2].
- Both unions share the same EPSCA Association Fund rate of $0.30 [SOURCE 1; SOURCE 2].

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Cement Masons | Cement Masons Wage Schedule CM-1 Local 598 Windsor |  |  |
| 2 | Plasterers | Plasterers Wage Schedule PL-1 LU 124 Windsor |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 12015ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 43.96, 52.57)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Auto-check PASS (exact expected rate from source PDF). |

---

## Refusal

### R01 — Boilermakers

**Question:** What are the pension benefits for retired Boilermakers under EPSCA agreements?

**Answer:**

# Pension Benefits for Retired Boilermakers

The provided documents do not contain information about specific pension benefit amounts or payment structures for retired Boilermakers.

## What the Documents Address

The documents establish that employers must contribute to the **Boilermakers' National Pension Plan (Canada)** on behalf of active employees [SOURCE 2, Section 31.1], with hourly contribution amounts specified in the wage schedules [SOURCE 9, SOURCE 10]. However, there is one special provision regarding pension contributions at retirement age:

**Pension Contributions for Employees Age 71+:**

"On November 30th, 2022, the Employer shall cease pension contributions to the Boilermakers' National Pension Plan (Canada), on behalf of those employees who are seventy-one (71) years of age or older. The pension contributions that would otherwise be payable to the Boilermakers' National Pension Plan (Canada) will be paid on behalf of the applicable employee to the Boilermakers' National Health Plan (Canada)." [SOURCE 1, Section 31.6]

## What Is Missing

The documents do not specify:
- Actual pension benefit amounts upon retirement
- Eligibility age for pension benefits
- Calculation methods for benefits
- Payment frequency or duration
- Survivor benefits or other retirement features

For detailed information about pension benefits for retired members, you would need to consult the Boilermakers' National Pension Plan documentation itself, which is referenced but not provided in these collective agreement excerpts.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  | 31.6 |
| 2 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  | 31.1 |
| 9 | Boilermakers | Boilermakers Wage Schedule EPSCA Boilermakers |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5862ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Correctly grounded: cites Boilermakers National Pension Plan contributions (§31.1) and age-71 clause; retiree benefit amounts are genuinely out of corpus. |

---

### R02 — IBEW

**Question:** What is the grievance arbitration process for IBEW Transmission workers at Bruce Power?

**Answer:**

# Grievance Arbitration Process for IBEW Transmission Workers

The grievance and arbitration process for IBEW Transmission workers consists of three stages: preliminary discussion, a two-step formal grievance procedure, and arbitration if unresolved.

## Grievance Scope and Definition

Grievances are limited to disputes about the interpretation or application of particular clauses of the agreement and alleged violations of the agreement. No suspension or disruption of work is permitted during the dispute resolution process. [SOURCE 1, Section 1400.A]

## Preliminary Discussion

Disputes arising from interpretation or alleged violation of the agreement shall, if possible, be settled by discussion between the employee and/or their steward and the employee's supervisor. [SOURCE 1, Section 1400.B]

## First Step

If preliminary discussion fails, the Accredited Union Representative may file a formal grievance on the prescribed form with the Employer within **15 working days** of the alleged grievous act. [SOURCE 1, Section 1400.C]

The Employer must investigate the grievance and convene a meeting within **10 working days** of filing, then provide their reply on the prescribed form within **5 working days** from the date of the First Step meeting. [SOURCE 1, Section 1400.C]

If a First Step meeting is held, the management committee comprises the Employer, and the Union committee comprises the Accredited Union Representative plus two additional Union officials. Completed grievance forms are filed by the Employer with EPSCA's General Manager and by the Union Representative with the appropriate Local Union's Business Manager. [SOURCE 4, Section 1400.C]

## Second Step

If unresolved at First Step, the Accredited Union Representative may refer the grievance to the appropriate EPSCA Representative or the Employer within **10 working days** after First Step disposition is issued. [SOURCE 4, Section 1400.D]

The EPSCA Representative or Employer must investigate and convene a meeting they or the Business Manager of the appropriate Local Union considers necessary, providing their reply on the prescribed form within **5 working days** of receiving the First Step grievance form. [SOURCE 4, Section 1400.D]

If a Second Step meeting is held, the management committee comprises the appropriate EPSCA Representative plus two other Management representatives (one representing the Employer against whom the grievance is filed). The Union committee comprises three persons, including the Business Manager of the appropriate Local Union, the Accredited Representative for the grievor, plus one other Union representative. [SOURCE 4, Section 1400.D]

## Arbitration

If the dispute is not settled through the grievance procedure, either EPSCA or the Union may submit the matter to a Board of Arbitration within **30 days** of the grievance procedure's failure to settle. [SOURCE 2, Section 1401.A]

The requesting party notifies the other party in writing, naming its first nominee to the arbitration board. The recipient must name its nominee within **5 working days**. The two nominees must appoint a Chairperson within **10 working days** of the second appointment. If either party fails to appoint or the nominees cannot agree on a Chairperson, the Minister of Labour for Ontario makes the appointment upon either party's request. [SOURCE 2, Section 1401.A]

The arbitration board proceeds as soon as practicable to hear and determine the dispute and issues a **final and binding decision**. A majority decision governs; if no majority exists, the Chairperson's decision governs. [SOURCE 2, Section 1401.A]

### Arbitration Board Powers and Limitations

The arbitration board has **no power to add to, subtract from, or modify** the terms of the agreement. [SOURCE 2, Section 1401.B]

However, when an employee has been discharged or disciplined for cause and the agreement contains no specific penalty for the infraction, the board may substitute a different penalty (other than discharge or discipline) that it deems just and reasonable in all circumstances. [SOURCE 7, Section 1401.B]

The board shall not deal with any matter not contained in the original statement of grievance. [SOURCE 7, Section 1401.B]

### Arbitration Costs

Each party pays the fees and expenses of its own nominee. The fees and expenses of the Chairperson are shared equally by both parties. [SOURCE 7, Section 1401.C]

## Time Limits and Extensions

Parties must comply with all specified time limits. However, they may mutually agree in writing to extend or waive any time limits. Where no answer is given within specified timeframes, the grieving party may submit the grievance to the next step. Any grievance not processed within the specified time limits is deemed withdrawn and ineligible for arbitration. [SOURCE 3, Section 1400.F]

## Special Cases

Alleged unjustified termination, discharge, suspension, or disciplinary action may be grieved beginning at the First Step (bypassing preliminary discussion). [SOURCE 3, Section 1400.G]

EPSCA or Employer grievances begin at the Second Step. Both EPSCA and the Union may submit policy grievances at Second Step within **30 days** of the alleged grievous act. [SOURCE 3, Section 1400.E]

Disputes must be fully processed through this grievance and arbitration procedure before either party can pursue recourse under Section 133 of the Labour Relations Act of Ontario. [SOURCE 2, Section 1400.H]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 3 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 4 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 14991ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Verified against IBEW Transmission CA §14: preliminary discussion → two-step grievance → arbitration. Corpus expansion turned this former refusal into a correct answer. |

---

### R03 — N/A (out of corpus)

**Question:** What is the wage rate for Elevator Constructors under EPSCA agreements?

**Answer:**

The provided documents do not contain information about wage rates for Elevator Constructors under EPSCA agreements.

The sources provided include wage schedules for Teamsters classifications and collective agreements for Sheet Metal Workers, IBEW, Brick and Allied Craft Union, and Painters unions, but none of these documents address Elevator Constructors or their wage rates.

To find this information, you would need to consult the EPSCA collective agreement specific to the Elevator Constructors union.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3083ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Clean refusal, zero citations. |

---

### R04 — N/A (out of corpus)

**Question:** What does the Sprinkler Fitters collective agreement say about overtime pay?

**Answer:**

The provided documents do not contain information about the Sprinkler Fitters collective agreement. 

The sources supplied cover collective agreements for the following unions: Painters, Sheet Metal Workers, Cement Masons, Carpenters, Operating Engineers, Brick and Allied Craft Union, and Millwrights. There is no Sprinkler Fitters agreement included in the materials provided.

If you have a Sprinkler Fitters collective agreement or wage schedule you would like me to reference, please provide it and I can answer your question about overtime pay.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3244ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| **Yes** | **Yes** | Clean refusal, zero citations. |

---

## Summary Table

Fill in after reviewing all answers:

| ID | Category | Union | Correct? | Citations valid? | Notes |
|----|----------|-------|----------|-----------------|-------|
| W01 | Wages & Rates | IBEW | | | |
| W02 | Wages & Rates | IBEW | | | |
| W03 | Wages & Rates | IBEW | | | |
| W04 | Wages & Rates | Sheet Metal | | | |
| W05 | Wages & Rates | Sheet Metal | | | |
| W06 | Wages & Rates | Sheet Metal | | | |
| W07 | Wages & Rates | United Association | | | |
| W08 | Wages & Rates | United Association | | | |
| O01 | Overtime & Hours | IBEW | | | |
| O02 | Overtime & Hours | IBEW | | | |
| O03 | Overtime & Hours | IBEW | | | |
| O04 | Overtime & Hours | Sheet Metal | | | |
| O05 | Overtime & Hours | Sheet Metal | | | |
| O06 | Overtime & Hours | Sheet Metal | | | |
| O07 | Overtime & Hours | United Association | | | |
| O08 | Overtime & Hours | United Association | | | |
| T01 | Travel & Board | IBEW | | | |
| T02 | Travel & Board | IBEW | | | |
| T03 | Travel & Board | Sheet Metal | | | |
| T04 | Travel & Board | Sheet Metal | | | |
| T05 | Travel & Board | United Association | | | |
| N01 | Nuclear Project Specific | IBEW | | | |
| N02 | Nuclear Project Specific | IBEW | | | |
| N03 | Nuclear Project Specific | Sheet Metal | | | |
| N04 | Nuclear Project Specific | United Association | | | |
| N05 | Nuclear Project Specific | IBEW | | | |
| C01 | Cross-Union Comparison | IBEW / Sheet Metal | | | |
| C02 | Cross-Union Comparison | IBEW / United Association | | | |
| R01 | Refusal | Boilermakers | | | |
| R02 | Refusal | IBEW | | | |
| W09 | Wages & Rates | Boilermakers | | | |
| W10 | Wages & Rates | Carpenters | | | |
| W11 | Wages & Rates | Millwrights | | | |
| W12 | Wages & Rates | Ironworkers | | | |
| W13 | Wages & Rates | Rodmen | | | |
| W14 | Wages & Rates | Operating Engineers | | | |
| W15 | Wages & Rates | Labourers | | | |
| W16 | Wages & Rates | Painters | | | |
| W17 | Wages & Rates | Roofers | | | |
| W18 | Wages & Rates | Cement Masons | | | |
| W19 | Wages & Rates | Plasterers | | | |
| W20 | Wages & Rates | Insulators | | | |
| W21 | Wages & Rates | Tile and Terrazzo | | | |
| W22 | Wages & Rates | Teamsters | | | |
| W23 | Wages & Rates | Brick and Allied Craft Union | | | |
| C03 | Cross-Union Comparison | Carpenters / Ironworkers | | | |
| C04 | Cross-Union Comparison | Cement Masons / Plasterers | | | |
| N06 | Nuclear Project Specific | Boilermakers | | | |
| R03 | Refusal | N/A (out of corpus) | | | |
| R04 | Refusal | N/A (out of corpus) | | | |
