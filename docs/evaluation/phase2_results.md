# Phase 2 Full-Corpus Evaluation — BASELINE (pre-#94)

> This run is the **pre-nomic-prefix baseline** against the full 18-union corpus
> (317 documents, 7,585+ chunks). The authoritative Phase 2 gate run happens after
> PRs #93/#94/#95 merge and the prefixed reingest completes; compare against this
> baseline to measure the embedding-prefix improvement.
>
> **Auto-check: 14/17 PASS.** The three failures are root-caused:
> - **W14** (Operating Engineers): answer lists five correct O-4 Hamilton group rates
>   but the OPERATING ENGINEER classification ($50.40) missed the five wage slots —
>   slot-count limitation with 6+ classification groups; #89 (structured rate lookup).
> - **W15** (Labourers Sarnia generation): wage pass ignored agreement_scope and
>   surfaced the Sarnia TRANSMISSION schedule — fixed in PR #95.
> - **W21** (Tile & Terrazzo): "Marble/Tile/Terrazzo" did not match union
>   "Tile and Terrazzo"; no union filter applied — alias added in PR #95.

**Run date:** 2026-07-12 10:58 UTC  
**Questions:** 50  
**API errors:** 0  
**Auto-checked (expected_contains):** 14 pass / 3 fail / 33 manual-only  

> **Note:** Correctness and citation accuracy scores require manual review against
> the source PDFs. Fill in the `Correct?` and `Citations valid?` columns below.

## Acceptance Criteria

| Criterion | Threshold | Result |
|-----------|-----------|--------|
| Correctness | ≥ 85% | _pending review_ |
| Citation accuracy | 100% | _pending review_ |
| Zero hallucinated facts on refusal questions | 0 | _pending review_ |
| Cross-union comparison valid | Pass/Fail | _pending review_ |
| Nuclear context includes NPA chunks | Pass/Fail | _pending review_ |

---

## Wages & Rates

### W01 — IBEW

**Question:** What is the journeyperson hourly rate for IBEW Generation electricians effective May 1, 2025?

**Answer:**

Based on your question, I need to clarify which "Generation" context you're asking about, as the rates vary by local jurisdiction.

**For IBEW Local 115 (Quinte-St. Lawrence) Generation:**

The journeyperson hourly base rate effective May 1, 2025 is **$48.63** [SOURCE 1, Wage Schedule E-12-C, Journeyman classification, effective 2025-05-01]. The total wage package including vacation & statutory holiday pay, welfare, pension, and union funds is **$72.18** per hour [SOURCE 1].

**For IBEW Local 1687 (Sudbury) Generation:**

The journeyperson hourly base rate effective May 1, 2025 is **$50.25** [SOURCE 3, Wage Schedule E-15-C, Journeyman classification, effective 2025-05-01]. The total wage package is **$72.78** per hour [SOURCE 3].

**The difference:** The two IBEW locals have different negotiated rates. Local 115 applies to the Quinte-St. Lawrence region, while Local 1687 applies to the Sudbury region. Both are under EPSCA Generation agreements effective May 1, 2025.

If you need the rate for a specific local or region, please clarify and I can provide the precise figure.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation Wage Schedule E-12-C LU 115 Quinte |  |  |
| 3 | IBEW | IBEW Generation Wage Schedule E-15-C LU 1687 Sudbu |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 8514ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W02 — IBEW

**Question:** What is the foreman wage premium for IBEW Generation electricians?

**Answer:**

The provided documents do not contain information about a specific foreman wage premium for IBEW Generation electricians.

What the documents do show is that foreman positions have their own separate wage rates listed on the wage schedules [SOURCE 1, SOURCE 2]. For example, in the IBEW Local 402 Thunder Bay Generation schedule, the "ELECTRICIAN / FOREMAN" classification has a base hourly rate of $59.43 effective May 1, 2025 [SOURCE 1], while the journeyman/welder/communications electrician rate in the transmission schedule for the same local is $52.51 for the same period [SOURCE 4]. However, the documents do not explicitly state what premium (if any) is paid for the foreman position, nor do they provide a formula or percentage for calculating a foreman premium.

If you are looking for information about how foreman wages are determined relative to journeyperson rates, or whether there is a formal premium structure, that information is not present in the provided sources.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation Wage Schedule E-16-C LU 402 Thunde |  |  |
| 4 | IBEW | IBEW Transmission Wage Schedule ET-16-C LU 402 - T |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4456ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W03 — IBEW

**Question:** What is the tool allowance for IBEW Generation electricians?

**Answer:**

The provided documents do not contain information about a specific tool allowance amount (such as a dollar value or payment) for IBEW Generation electricians.

What the documents do specify is a **tool list** that all journeypeople electricians are required to have. According to [SOURCE 1, Page 49-50], the required tools include:

- 1 Centre Punch
- 1 1/2" Cold Chisel
- 1 Half-round File
- 1 Ball Peen Hammer
- 1 Adjustable Hacksaw Frame
- 1 Knife
- 1 Medium Level
- 5 pairs of Pliers (8" Sidecutters, Diagonal, Longnose and 2 pairs of Channelock)
- 6 Screwdrivers (Robertson and Standard types)
- 1 6" Square or Combination Square
- 1 Steel Tape (10 or 12-foot)
- 1 Small Tap Wrench
- 1 Tool box
- 1 Tool Pouch and belt for hand tools

The agreement also states that employees are responsible for maintaining these personal tools, and that the Employer is responsible for "gang tools" issued to forepersons [SOURCE 3, Page 35-36, Section on Gang Tools].

If you are looking for a monetary tool allowance or replacement reimbursement amount, that information is not present in the provided sources.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5455ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W04 — Sheet Metal

**Question:** What is the journeyperson hourly rate for Sheet Metal workers effective May 1, 2025?

**Answer:**

The journeyperson hourly rate for Sheet Metal workers effective May 1, 2025 varies by local union jurisdiction. There is no single rate across all EPSCA Sheet Metal Workers locals.

**The base hourly rates effective May 1, 2025 are:**

- Sheet Metal Local 235 (Windsor): $48.16 [SOURCE 1, Wage Schedule SM-1]
- Sheet Metal Local 562 (Kitchener): $48.63 [SOURCE 2, Wage Schedule SM-5]
- Sheet Metal Local 235 (Chatham): $48.08 [SOURCE 3, Wage Schedule SM-2]
- Sheet Metal Local 504 (Sudbury): $48.06 [SOURCE 4, Wage Schedule SM-14]
- Sheet Metal Local 504 (Sault Ste. Marie): $47.42 [SOURCE 5, Wage Schedule SM-15]

All rates apply to the classification "JOURNEYMAN AND WELDER" (occupation code 445535; grade/step 93-6).

These base hourly rates do not include the full total wage package, which adds vacation & statutory holiday pay, welfare, pension, union funds, provincial training fund, and EPSCA association fund contributions. The total wage package ranges from approximately $65.42 to $67.16 depending on the local.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-01 LU 235 Windsor |  |  |
| 2 | Sheet Metal | Sheet Metal Wage Schedule SM-05 LU 562 Kitchener |  |  |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-02 LU 235 Chatham |  |  |
| 4 | Sheet Metal | Sheet Metal Wage Schedule SM-14 LU 504 Sudbury |  |  |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-15 LU 504 Sault Ste.  |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4860ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W05 — Sheet Metal

**Question:** What apprentice wage rates apply to Sheet Metal workers under the 2025-2030 collective agreement?

**Answer:**

# Apprentice Wage Rates for Sheet Metal Workers (2025-2030)

The apprentice wage rates under the 2025-2030 Sheet Metal Workers collective agreement vary by **apprenticeship period and by local union jurisdiction**. The provided documents contain specific wage schedules for multiple locals.

## Examples by Apprenticeship Period:

**1st Period Apprentice (50% of Journeyman) – Local 269 Kingston:**
- Effective 2025-05-01: Base hourly rate $22.26, total wage package $34.46 [SOURCE 1]
- Effective 2026-05-01: Base hourly rate $23.46, total wage package $35.81 [SOURCE 1]
- Effective 2027-05-01: Base hourly rate $24.49, total wage package $36.94 [SOURCE 1]
- Effective 2028-05-01: Base hourly rate $25.57, total wage package $38.13 [SOURCE 1]
- Effective 2029-05-01: Base hourly rate $26.13, total wage package $38.74 [SOURCE 1]

**2nd Period Apprentice (60% of Journeyman) – Local 269 Kingston:**
- Effective 2025-05-01: Base hourly rate $26.71, total wage package $40.58 [SOURCE 5]
- Effective 2026-05-01: Base hourly rate $28.15, total wage package $42.21 [SOURCE 5]

**3rd Period Apprentice (70% of Journeyman) – Local 473 London:**
- Effective 2025-05-01: Base hourly rate $31.83, total wage package $49.13 [SOURCE 3]
- Effective 2026-05-01: Base hourly rate $33.71, total wage package $51.43 [SOURCE 3]

**5th Period Apprentice (80% of Journeyman) – Local 269 Kingston:**
- Effective 2025-05-01: Base hourly rate $35.61, total wage package $54.00 [SOURCE 2]
- Effective 2026-05-01: Base hourly rate $37.53, total wage package $56.16 [SOURCE 2]

The wage package includes base hourly rate, vacation & statutory holiday pay, welfare, pension, union funds, provincial training fund, and EPSCA association fund. Each local has its own wage schedule, so rates differ by jurisdiction.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-12 LU 269 Kingston |  |  |
| 2 | Sheet Metal | Sheet Metal Wage Schedule SM-12 LU 269 Kingston |  |  |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-04 LU 473 London |  |  |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-12 LU 269 Kingston |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5995ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W06 — Sheet Metal

**Question:** What is the general foreman wage rate for Sheet Metal workers?

**Answer:**

# Sheet Metal Foreman Wage Rates

There is **no single "general foreman" wage rate** for Sheet Metal workers. Instead, wage rates for foremen vary by:

1. **Local union jurisdiction** (different geographic areas)
2. **Specific foreman classification** (general Foreman vs. Foreman Sheeter/Decker)
3. **Effective date** within the 2025-2030 agreement period

## Examples of Current Foreman Rates (Effective May 1, 2026):

**FOREMAN (Occupation Code 445565):**
- Sheet Metal Local 269 (Kingston): base hourly rate $53.95, total wage package $77.28 [SOURCE 1]
- Sheet Metal Local 537 (Hamilton): base hourly rate $57.68, total wage package $78.68 [SOURCE 5]
- Sheet Metal Local 537 (St. Catharines): base hourly rate $57.98, total wage package $79.01 [SOURCE 2]

**FOREMAN SHEETER/DECKER (Occupation Code 445566):**
- Sheet Metal Local 537 (Brantford): base hourly rate $57.55, total wage package $78.54 [SOURCE 3]
- Sheet Metal Local 537 (St. Catharines): base hourly rate $57.78, total wage package $78.79 [SOURCE 4]

Per the collective agreement, "the rates of pay for employees in the classifications listed in Article 2 of this Agreement shall be as set forth in the wage schedules, attached hereto" [SOURCE 7, Section 13.1].

To determine the applicable rate, you must identify the specific local union and foreman classification for the relevant work location and effective date.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-12 LU 269 Kingston |  |  |
| 2 | Sheet Metal | Sheet Metal Wage Schedule SM-08 LU 537 St Catharin |  |  |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-07 LU 537 Brantford |  |  |
| 4 | Sheet Metal | Sheet Metal Wage Schedule SM-08 LU 537 St Catharin |  |  |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-06 LU 537 Hamilton |  |  |
| 7 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 13.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6417ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W07 — United Association

**Question:** What is the journeyperson hourly rate for United Association plumbers effective May 1, 2025?

**Answer:**

# United Association Journeyperson Plumber Hourly Rates — Effective May 1, 2025

The journeyperson hourly rate for United Association plumbers effective May 1, 2025 **varies by local**. There is no single rate across Ontario. Here are the rates by location:

| Local | Location | Base Hourly Rate | Total Wage Package |
|-------|----------|------------------|-------------------|
| UA-14 | Ottawa | $49.87 | $69.86 |
| UA-15 | Sudbury | $47.96 | $69.32 |
| UA-16 | Sault Ste. Marie | $47.14 | $68.40 |
| UA-17 | Thunder Bay | $48.98 | $69.40 |
| UA-2 | Sarnia | $50.94 | $70.96 |

---

## Supporting Citations

**Local 71 (Ottawa):** Base hourly rate $49.87 effective May 1, 2025 [SOURCE 1, Wage Schedule UA-14, Journeyman/Pipewelder classification, Effective 2025-05-01]

**Local 800 (Sudbury):** Base hourly rate $47.96 effective May 1, 2025 [SOURCE 4, Wage Schedule UA-15, Journeyman/Pipewelder classification, Effective 2025-05-01]

**Local 800 (Sault Ste. Marie):** Base hourly rate $47.14 effective May 1, 2025 [SOURCE 2, Wage Schedule UA-16, Journeyman/Pipewelder classification, Effective 2025-05-01]

**Local 628 (Thunder Bay):** Base hourly rate $48.98 effective May 1, 2025 [SOURCE 3, Wage Schedule UA-17, Journeyman/Pipewelder classification, Effective 2025-05-01]

**Local 663 (Sarnia):** Base hourly rate $50.94 effective May 1, 2025 [SOURCE 5, Wage Schedule UA-2, Journeyman/Pipewelder classification, Effective 2025-05-01]

All rates are for classification **Journeyman/Pipewelder** (occupation codes 450035, 450036; grade/step 13-6).

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 2 | United Association | United Association Wage Schedule Local 800 Sault S |  |  |
| 3 | United Association | United Association Wage Schedule Local 628 Thunder |  |  |
| 4 | United Association | United Association Wage Schedule Local 800 Sudbury |  |  |
| 5 | United Association | United Association Wage Schedule Local 663 Sarnia |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5244ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W08 — United Association

**Question:** What is the foreman premium percentage for United Association workers?

**Answer:**

Based on the provided sources, the foreman premium percentage for United Association workers is **15% above the journeymen base hourly rate**.

This premium applies consistently across all United Association locals in the wage schedules provided:

- United Association Local 71 (Ottawa): "Classification: FOREMAN (occupation code 450065; grade/step 13-9). (15% above journeymen base hourly rate)" [SOURCE 1]
- United Association Local 46 (Toronto): "Classification: FOREMAN (occupation code 450065; grade/step 13-9). (15% above journeymen base hourly rate)" [SOURCE 4]
- United Association Local 800 (Sault Ste. Marie): "Classification: FOREMAN (occupation code 450065; grade/step 13-9). (15% above journeymen base hourly rate)" [SOURCE 6]
- United Association Local 46 (Barrie): "Classification: FOREMAN (occupation code 450065; grade/step 13-9). (15% above journeymen base hourly rate)" [SOURCE 7]
- United Association Local 628 (Thunder Bay): "Classification: FOREMAN (occupation code 450065; grade/step 13-9). (15% above journeymen base hourly rate)" [SOURCE 10]

For comparison, the subforeman classification carries a 7.5% premium above the journeymen base hourly rate [SOURCES 3, 5, 9].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 4 | United Association | United Association Wage Schedule Local 46 Toronto |  |  |
| 6 | United Association | United Association Wage Schedule Local 800 Sault S |  |  |
| 7 | United Association | United Association Wage Schedule Local 46 Barrie |  |  |
| 10 | United Association | United Association Wage Schedule Local 628 Thunder |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3480ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W09 — Boilermakers

**Question:** What is the Boilermakers journeyperson hourly rate effective May 1, 2025?

**Answer:**

# Boilermakers Journeyperson Hourly Rate – Effective May 1, 2025

The Boilermakers journeyperson base hourly rate effective May 1, 2025 is **$52.72**. The total wage package (including vacation & statutory holiday pay, welfare, pension, supplementary fund, and union funds) is **$70.48** per hour. [SOURCE 1]

## Supporting Detail

**Classification:** Journeyman (occupation code 445835; grade/step 15-6)

**Effective May 1, 2025 wage breakdown:**
- Base hourly rate: $52.72
- Vacation & statutory holiday pay: $4.75
- Welfare: $1.58
- Pension: $3.95
- Supplementary fund: $6.50
- Union funds: $0.98
- Total wage package: $70.48
- Additional amount 1: $0.33
- Additional amount 2: $0.30

[SOURCE 1, Boilermakers Wage Schedule EPSCA Boilermakers, effective May 1, 2025, revised April 1, 2025]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Boilermakers | Boilermakers Wage Schedule EPSCA Boilermakers |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4940ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 52.72)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W10 — Carpenters

**Question:** What is the journeyperson hourly rate for Carpenters in Windsor effective May 1, 2025?

**Answer:**

The journeyperson hourly rate for Carpenters in Windsor effective May 1, 2025, depends on the specific trade classification:

**For Carpenters (general C-1 classification):**
The base hourly rate is **$44.69**, with a total wage package of **$63.04** [SOURCE 2, Carpenters Wage Schedule C-1 LU 494 Windsor, effective 2025-05-01].

**For Resilient Floor Workers (RF-1 classification):**
The base hourly rate is **$43.78**, with a total wage package of **$62.04** [SOURCE 1, Carpenters Resilient Floor Wage Schedule RF-1 LU 494 Windsor, effective 2025-05-01].

**For Acoustic and Drywall Workers (AD-1 classification):**
The base hourly rate is **$44.69**, with a total wage package of **$63.04** [SOURCE 3, Carpenters Acoustic and Drywall Wage Schedule AD-1 LU 494 Windsor, effective 2025-05-01].

The total wage package includes the base hourly rate plus vacation & statutory holiday pay, union funds, administration & training fund, and EPSCA association fund.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Carpenters | Carpenters Resilient Floor Wage Schedule RF-1 LU 4 |  |  |
| 2 | Carpenters | Carpenters Wage Schedule C-1 LU 494 Windsor |  |  |
| 3 | Carpenters | Carpenters Acoustic and Drywall Wage Schedule AD-1 |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3772ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 44.69)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W11 — Millwrights

**Question:** What is the Millwrights journeyperson hourly rate effective May 1, 2025?

**Answer:**

The Millwrights journeyperson hourly rate effective May 1, 2025 is **$50.14 base hourly rate**, with a **total wage package of $69.85** [SOURCE 1].

This total wage package breaks down as follows:
- Base hourly rate: $50.14
- Vacation & statutory holiday pay: $5.01
- Welfare: $4.20
- Pension: $8.65
- Union funds: $1.85
- Benefits stabilization fund: $0.35
- EPSCA association fund: $0.30

[SOURCE 1, Millwrights Wage Schedule, Classification: JOURNEYMAN, Effective 2025-05-01]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Millwrights | Millwrights Wage Schedule Millwright |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2474ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 50.14)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W12 — Ironworkers

**Question:** What is the journeyperson rate for Ironworkers in Windsor on a generation project effective May 1, 2025?

**Answer:**

Based on the provided sources, the journeyperson rate for Ironworkers in Windsor on a generation project effective May 1, 2025 is:

**Base hourly rate: $48.33**
**Total wage package: $66.95/hour**

The wage package breakdown is:
- Base hourly rate: $48.33
- Vacation & statutory holiday pay: $4.83
- Welfare: $4.75
- Pension: $8.82
- Union funds: $0.22
- EPSCA association fund: $0.30

**Supporting source:**

This rate is found in [SOURCE 2] Ironworkers Generation Wage Schedule I-1 for Ironworkers Local 700 (Windsor), effective May 1, 2025. The classification is JOURNEYMAN IRONWORKER, RIGGER (occupation code 445035; grade/step 19-6).

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Ironworkers | Ironworkers Generation Wage Schedule I-1 LU 700 Wi |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3829ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 48.33)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W13 — Rodmen

**Question:** What is the Rodmen journeyperson hourly rate in Toronto on a generation project effective May 1, 2025?

**Answer:**

# Answer

For Toronto Rodmen on a generation project effective May 1, 2025, the journeyperson hourly rate is:

**Base rate: $46.94/hour**
**Total wage package: $65.18/hour**

The total wage package comprises:
- Base hourly rate: $46.94
- Vacation & statutory holiday pay: $4.69
- Welfare: $4.45
- Pension: $8.99
- Union funds: $0.11
- EPSCA association fund: $0.30

[SOURCE 2] Rodmen Generation Wage Schedule R-5 LU 721 Toronto Rodmen Generation, effective May 1, 2025, Journeyman classification.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Rodmen | Rodmen Generation Wage Schedule R-5 LU 721 Toronto |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3073ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 46.94)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W14 — Operating Engineers

**Question:** What is the operating engineer hourly rate in Hamilton effective May 1, 2025?

**Answer:**

The Operating Engineers hourly rates effective May 1, 2025 in Hamilton vary by classification group. The provided documents contain five different wage schedules for Hamilton (O-4), each with different base hourly rates:

- **GROUP 2 (grade/step 54-6) (B)**: Base hourly rate **$48.25** [SOURCE 1]
- **GROUP 2 (grade/step 53-6) (A)**: Base hourly rate **$48.85** [SOURCE 3]
- **GROUP 1 (grade/step 52-6) (B)**: Base hourly rate **$49.81** [SOURCE 5]
- **GROUP 5 (grade/step 57-6)**: Base hourly rate **$44.45** [SOURCE 2]
- **GROUP 6 (grade/step 58-6)**: Base hourly rate **$43.18** [SOURCE 4]

All of these are effective May 1, 2025, per the Operating Engineers Local 793 (Hamilton) — OPERATING ENGINEERS EPSCA Wage Schedule O-4.

**Which rate applies depends on the employee's classification group.** The documents do not specify which classification is the standard or most common for Operating Engineers in Hamilton.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |
| 2 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |
| 3 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |
| 4 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |
| 5 | Operating Engineers | Operating Engineers Wage Schedule O-4 Hamilton |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3938ms  
**Query log ID:** `N/A`

**Auto-check:** FAIL — missing: 50.40

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ **Partial** | ✓ | Five real O-4 group rates, but OPERATING ENGINEER ($50.40) missed the wage slots — see #89. |

---

### W15 — Labourers

**Question:** What is the Labourers Foreman Group IX rate in Sarnia on a generation project effective May 1, 2025?

**Answer:**

The provided documents do not contain information about a "Labourers Foreman Group IX" rate for a generation project in Sarnia effective May 1, 2025.

The sources include:
- Labourers wage schedules for **Transmission** projects in Sarnia (Sources 1–5), which list various foreman classifications but no "Foreman Group IX"
- Labourers wage schedules for **Generation** projects in Kingston and Windsor/Chatham (Sources 6–10), which do not cover Sarnia

To locate the rate you're seeking, you would need the wage schedule for Labourers on a generation project in Sarnia, which is not provided in the current document set.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3329ms  
**Query log ID:** `N/A`

**Auto-check:** FAIL — missing: 46.51

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ **No** | n/a | Honest refusal, but the Sarnia GENERATION schedule exists (FOREMAN GROUP IX $46.51); wage pass lacked scope filter — fixed in #95. |

---

### W16 — Painters

**Question:** What is the painter journeyperson hourly rate in Windsor effective May 1, 2025?

**Answer:**

Based on the provided source documents, the **Painter Journeyperson hourly base rate in Windsor effective May 1, 2025 is $39.41** [SOURCE 1].

**Supporting Detail:**

The full wage package breakdown for the Painter Journeyman / Lead Abatement Worker classification (occupation code 405735, grade/step 42-6) effective May 1, 2025 is:

- Base hourly rate: $39.41
- Vacation & statutory holiday pay: $3.94
- Welfare: $4.23
- Pension: $8.25
- Union funds: $1.14
- **Total wage package: $56.97**
- EPSCA association fund: $0.30

[SOURCE 1, Painters Local 1494 (Windsor) — PAINTERS EPSCA Wage Schedule P-1, revised April 1, 2025]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Painters | Painters Wage Schedule P-1 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3683ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 39.41)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W17 — Roofers

**Question:** What is the journeyperson roofer hourly rate in Windsor effective May 1, 2025?

**Answer:**

# Journeyperson Roofer Hourly Rate in Windsor – Effective May 1, 2025

The journeyperson roofer base hourly rate in Windsor effective May 1, 2025 is **$42.57** [SOURCE 1, Roofers Local 235 (Windsor) Wage Schedule RO-1, effective May 1, 2025].

The complete wage package effective that date is:
- Base hourly rate: $42.57
- Vacation & statutory holiday pay: $4.26
- Welfare: $9.45
- Union funds: $1.68
- **Total wage package: $57.96**
- Administration & training fund: $0.10
- EPSCA association fund: $0.30

[SOURCE 1, Roofers Wage Schedule RO-01 LU 235 Windsor]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Roofers | Roofers Wage Schedule RO-01 LU 235 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3392ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 42.57)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W18 — Cement Masons

**Question:** What is the Cement Masons foreman hourly rate in Windsor effective May 1, 2025?

**Answer:**

# Cement Masons Foreman Hourly Rate in Windsor – May 1, 2025

Effective May 1, 2025, the Cement Masons foreman hourly rate in Windsor is:

- **Base hourly rate: $43.96**
- **Total wage package: $61.90** (which includes vacation & statutory holiday pay of $4.40, union funds of $13.54, and EPSCA association fund of $0.30)

**Source:** [SOURCE 1] Cement Masons Local 598 (Windsor) — CEMENT MASONS EPSCA Wage Schedule CM-1, revised April 1, 2025, Foreman classification (occupation code 430065; grade/step 16-9), effective 2025-05-01 entry.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Cement Masons | Cement Masons Wage Schedule CM-1 Local 598 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2786ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 43.96)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W19 — Plasterers

**Question:** What is the Plasterers foreman hourly rate in Windsor effective May 1, 2025?

**Answer:**

# Plasterers Foreman Hourly Rate — Windsor, Effective May 1, 2025

The Plasterers foreman hourly rate in Windsor effective May 1, 2025 is:

- **Base hourly rate: $52.57**
- **Total wage package: $64.72** (which includes vacation & statutory holiday pay of $5.26, union funds of $6.89, and EPSCA association fund of $0.30)

**Source:** [SOURCE 1] Plasterers Local 124 (Windsor) — PLASTERERS EPSCA Wage Schedule PL-1, revised April 1, 2025, Classification: FOREMAN (occupation code 430365; grade/step 17-9), Effective 2025-05-01.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Plasterers | Plasterers Wage Schedule PL-1 LU 124 Windsor |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3059ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 52.57)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W20 — Insulators

**Question:** What is the Insulators foreman hourly rate for Local 95 Zone 1 effective May 1, 2025?

**Answer:**

For Insulators Local 95 Zone 1, the foreman hourly rate effective May 1, 2025 is:

**Base hourly rate: $55.74**
**Total wage package: $73.04**

The total wage package comprises: base hourly rate $55.74, vacation & statutory holiday pay $5.57, welfare $7.50, union funds $4.23, and EPSCA association fund $0.30. [SOURCE 1, Insulators Local 95 (Zone 1) — INSULATORS EPSCA Wage Schedule IN-1, Foreman classification, effective 2025-05-01]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Insulators | Insulators Wage Schedule IN-1 LU 95 Zone 1 Insulat |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2548ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 55.74)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W21 — Tile and Terrazzo

**Question:** What is the working foreman rate for Marble/Tile/Terrazzo workers in Windsor effective May 1, 2025?

**Answer:**

The provided documents do not contain information about a working foreman rate for Marble/Tile/Terrazzo workers in Windsor effective May 1, 2025.

The wage schedules provided cover the following trades in Windsor: Plumbers (United Association Local 527), Roofers (Local 235), Resilient Floor Workers (Carpenters Local 494), Plasterers (Local 124), and Cement Masons (Local 598). None of these documents address Marble/Tile/Terrazzo workers or their foreman rates.

To find this information, you would need to consult the EPSCA wage schedule specifically for the Marble/Tile/Terrazzo trade in the Windsor jurisdiction.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3591ms  
**Query log ID:** `N/A`

**Auto-check:** FAIL — missing: 50.52

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ **No** | n/a | Union detection failed on 'Marble/Tile/Terrazzo'; schedule exists (WORKING FOREMAN $50.52) — alias added in #95. |

---

### W22 — Teamsters

**Question:** What is the Teamsters Group 1 hourly rate effective May 1, 2025?

**Answer:**

The Teamsters Group 1 hourly rate effective May 1, 2025 depends on the specific grade/step classification, as the provided documents show multiple Group 1 rates:

**GROUP 1 (grade/step 46-10):** Base hourly rate of **$43.13** [SOURCE 1]

**GROUP 1 (grade/step 46-7):** Base hourly rate of **$40.50** [SOURCE 2]

**TEAMSTERS FOREPERSON / GROUP 1 (grade/step 46-9):** Base hourly rate of **$41.50** [SOURCE 5]

All three classifications fall under "Teamsters Group 1" but carry different wage rates depending on the grade/step level. The documents do not specify which grade/step applies to a particular employee without additional context about their specific role or seniority level.

If you need the rate for a particular grade/step or job classification, please clarify which one applies.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Teamsters | Teamsters Wage Schedule Teamsters - Province of On |  |  |
| 2 | Teamsters | Teamsters Wage Schedule Teamsters - Province of On |  |  |
| 5 | Teamsters | Teamsters Wage Schedule Teamsters - Province of On |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4258ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 43.13)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### W23 — Brick and Allied Craft Union

**Question:** What is the BACU bricklayer journeyperson hourly rate in Niagara effective May 1, 2025?

**Answer:**

Based on the provided wage schedule for BACU Local 1 (Niagara), the journeyperson bricklayer hourly rate effective May 1, 2025 is:

**Base hourly rate: $46.45**

**Total wage package: $63.92**

The total wage package breaks down as follows [SOURCE 1]:
- Base hourly rate: $46.45
- Vacation & statutory holiday pay: $4.65
- Welfare: $3.47
- Pension: $0.60
- Supplementary fund: $1.00
- Union funds: $7.75
- Additional amount: $0.30

[SOURCE 1, Brick and Allied Craft Union Wage Schedule BACU-01 Local 1 Niagara, Effective 2025-05-01]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Brick and Allied Craft Union | Brick and Allied Craft Union Wage Schedule BACU-01 |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3295ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 46.45)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

## Overtime & Hours

### O01 — IBEW

**Question:** What constitutes overtime for IBEW Generation electricians under the 2025-2030 agreement?

**Answer:**

# Overtime for IBEW Generation Electricians (2025-2030)

Overtime for IBEW Generation electricians is defined based on the work schedule in place. The primary overtime provision applies to employees on an eight (8) hour day and five (5) day per week work schedule.

## Standard Overtime Rule (Monday-Friday Schedule)

**For hours beyond the normal daily scheduled number of hours:**
- Hours 1-2 beyond the normal shift: paid at **1½ times** the basic hourly rate
- Hours beyond 10 per day: paid at **2 times** the base hourly rate

[SOURCE 6, Section 806 A]

The specific clause states:

> "When working on an eight (8) hour day and five (5) day per week work schedule (Monday to Friday inclusive), overtime work shall be paid at one and one-half (1 ½) times the basic hourly rate for all hours worked beyond the normal daily scheduled number of hours up to a maximum of two (2) hours per day. All hours in excess of 10 hours per day shall be paid at two (2) times the base hourly rate."

## Voluntary Basis

All overtime **must be worked on a voluntary basis** and shall be distributed as equally as possible among all IBEW members. [SOURCE 1, Section 800 C (implied from page 24 context)]

## Important Note

The provided documents do not contain detailed overtime provisions for alternative shift schedules (such as three-shift operations or seven-day coverage schedules at nuclear sites). For those scenarios, you would need to consult the specific appendices or additional sections of the agreement that address overtime under different operational structures.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 6 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5935ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O02 — IBEW

**Question:** What is the overtime rate for IBEW Generation workers on a Saturday?

**Answer:**

The overtime rate for IBEW Generation workers on a Saturday is **two (2) times the basic hourly rate**.

**Supporting clause:**

"Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate." [SOURCE 7, IBEW Generation 2025-2030 Collective Agreement, Page 24, Section 806.A]

This provision applies regardless of whether the worker is on an eight (8) hour day/five (5) day per week schedule [SOURCE 6, Page 23] or a ten (10) hour day/four (4) day per week schedule [SOURCE 7, Page 24].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 6 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3406ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O03 — IBEW

**Question:** What is the maximum number of regular daily hours for IBEW Generation workers?

**Answer:**

# Maximum Regular Daily Hours for IBEW Generation Workers

The maximum regular daily hours depend on the shift operation established by the employer:

**One or Two Shift Operations:**
The weekly hours are 40 hours Monday to Friday inclusive, which typically translates to **8 hours per day** [SOURCE 1, Article 800 A].

**Three Shift Operations:**
- Day shift: **8 hours** [SOURCE 6, Article 800 B]
- Afternoon shift: **7½ hours** [SOURCE 6, Article 800 B]
- Night shift: **7 hours** [SOURCE 6, Article 800 B]

**Ten-Hour Day Schedules:**
When a ten (10) hour day and four (4) day per week work schedule is implemented, the regular daily hours are **10 hours** [SOURCE 7, Overtime section].

The applicable maximum depends on which shift operation the employer establishes at the specific worksite. Article 800 F notes that "It may be necessary from time to time to vary the hours of work established in this Article. Any amendments to the hours of work will be established by mutual agreement between EPSCA and the Union." [SOURCE 6, Article 800 F]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 6 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4609ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O04 — Sheet Metal

**Question:** What are the regular daily hours of work for Sheet Metal workers?

**Answer:**

# Regular Daily Hours of Work for Sheet Metal Workers

The regular daily hours of work for Sheet Metal workers depend on the operational structure established by the employer:

**Standard Operations (One or Two Shift):**

Sheet Metal workers may work either **four (4) consecutive ten-hour shifts** or **five (5) consecutive eight-hour shifts** per week, with a total of 40 hours worked Monday through Friday. [SOURCE 1, Section 22.1, Page 27]

The specific daily hours must be established for a minimum period of 30 days. If the employer intends to change the daily hours of work, they must provide at least five (5) days written notice to the Local Union. [SOURCE 1, Section 22.1, Page 27]

**Remote/Northern Operations:**

For work North of the French River in remote locations, an employer may establish a shift consisting of fourteen (14) consecutive days, followed by seven (7) consecutive days off. [SOURCE 5, Section 22.6, Page 28]

**Special Schedules:**

Other shift arrangements may apply depending on the specific project or location, as outlined in Letters of Understanding for particular locals, which may include six (6) or eight (8) hour shifts with different rotation patterns. [SOURCE 9, Section 2.0, Page 58]

The day shift start time shall be between 6:00 a.m. to 9:00 a.m., with the afternoon shift starting immediately following the day shift or within two (2) hours either way to coincide with the end of the day shift. [SOURCE 1, Section 22.1, Page 27]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.1 |
| 5 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.6 |
| 9 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5419ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O05 — Sheet Metal

**Question:** What is the overtime rate for Sheet Metal workers on a Sunday?

**Answer:**

Based on the provided sources, Sheet Metal workers receive **2 times the basic hourly rate for all hours worked on Sunday**.

This rate applies consistently across all Sheet Metal locals in the provided documents. The Primary Collective Agreement states:

"Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate." [SOURCE 6, Section 23.1]

This is further confirmed in the wage schedules for multiple locals, which specify: "Sat., Sun. & Holidays - 2 times for all hours worked." [SOURCE 1, SOURCE 2, SOURCE 3, SOURCE 4, SOURCE 5]

Additionally, the shift provisions clarify that "Regularly scheduled hours of work on Saturday, Sunday, non-shift days, Statutory and Recognized Holidays shall be paid at two times the straight time hourly rate." [SOURCE 7, Section 2.0]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-12 LU 269 Kingston |  |  |
| 6 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 23.1 |
| 7 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3941ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O06 — Sheet Metal

**Question:** What are the daily overtime rules for Sheet Metal workers under the 2025-2030 agreement?

**Answer:**

# Daily Overtime Rules for Sheet Metal Workers (2025-2030)

The daily overtime rules for Sheet Metal workers under the 2025-2030 agreement depend on the work schedule:

## 8-Hour Day / 5-Day Week Schedule

When working on an eight (8) hour day and five (5) day per week schedule (Monday to Friday):
- **1.5× rate** for all hours worked beyond the normal daily scheduled number of hours up to a maximum of 2 hours per day
- **2× rate** for all hours in excess of 10 hours per day

[SOURCE 3, Section 23.1]

## 10-Hour Day / 4-Day Week Schedule

When working on a ten (10) hour day and four (4) day per week schedule (Monday to Friday):
- **1.5× rate** for all hours worked beyond the normal daily scheduled number of hours up to a maximum of 2 hours per day
- **2× rate** for all hours in excess of 12 hours per day

[SOURCE 3, Section 23.1]

## Weekend and Holiday Overtime

Overtime work performed on Saturday, Sunday, Recognized Holidays, and non-shift days shall be paid at **2× the basic hourly rate** regardless of the daily schedule structure.

[SOURCE 3, Section 23.1]

## Additional Provision

Employees required to work two (2) hours of overtime are entitled to a ten (10) minute rest period prior to the end of the normal shift before commencing overtime work.

[SOURCE 10, Section 24.2]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 3 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 23.1 |
| 10 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 24.2 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3941ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O07 — United Association

**Question:** What is the double-time rate provision for United Association workers?

**Answer:**

The provided documents do not contain information about a double-time rate provision for United Association workers.

While [SOURCE 6, Section 9.1] establishes that work on Saturday, Sunday, Statutory and Recognized Holidays, and non-shift days shall be paid at "two times the straight time hourly rate," this addresses premium pay for specific days or circumstances rather than a general "double-time rate provision" as a defined contractual term.

If you are asking about premium pay rates for specific circumstances (such as weekend or holiday work, overtime, or shift differentials), please clarify and I can provide the relevant provisions.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 6 | United Association | United Association 2025-2030 Collective Agreement |  | 9.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3415ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### O08 — United Association

**Question:** What time does a regular shift start for United Association workers under the 2025-2030 agreement?

**Answer:**

# Start Time for Regular Day Shift

Under the 2025-2030 United Association collective agreement, the day shift start time depends on the work location:

- **Nuclear projects**: Between 6:00 AM and 9:00 AM [SOURCE 1, Section 23.2, page 24]
- **All other locations**: 8:00 AM with a possible one (1) hour variance either way (meaning 7:00 AM to 9:00 AM) [SOURCE 1, Section 23.2, page 24]

**Full clause text:**
> "The start time for the day shift shall be between 6:00 AM and 9:00 AM (nuclear only) or a start time of 8:00 AM with a possible one (1) hour variance either way (all other locations)." [SOURCE 1, Section 23.2, page 24]

The agreement also notes that "Crews may have staggered start times" and that the employer must notify the Local Union of the weekly hours of work, with at least 5 days' notice if changes are intended [SOURCE 1, Section 23.2, page 24].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association 2025-2030 Collective Agreement |  | 23.2 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5240ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

## Travel & Board

### T01 — IBEW

**Question:** What is the board allowance for IBEW Generation workers working away from home?

**Answer:**

# Board/Room and Board Allowance for IBEW Generation Workers Working Away from Home

The provided documents do not contain a single "board allowance" amount stated as a fixed daily rate. Instead, the collective agreement provides three distinct options that employers may offer to employees whose regular residence is 110+ road-driven kilometers from the project:

**The three options are:** [SOURCE 8, Article 1101 A(i)]

1. **Free room and board in camp** or a good standard of board and lodging within a reasonable distance of a project
2. **A subsistence allowance** (specific rates not shown in the excerpts provided)
3. **A travel allowance** (with rates varying by distance bands, as shown below)

**If an employee chooses not to stay in camp or accept free room and board**, they may elect to receive a **room and board allowance**, but the agreement then directs them to subsistence allowance rates based on whether they maintain temporary accommodation or commute daily. [SOURCE 8, Article 1101 A(ii)]

**Travel time compensation** (when receiving room and board allowance under Article 1100 B) is paid based on distance from accommodation to the project site: [SOURCE 1, Article 1100 D]

- 40–56 road km: ½ hour regular time pay
- 57–80 road km: 1 hour regular time pay
- 81–120 road km: 1½ hours regular time pay
- 121–160 road km: 2 hours regular time pay
- Over 160 road km: actual travel time at regular rate

To obtain the specific subsistence allowance dollar amounts, you would need to consult the full rate tables in the agreement, which are referenced but not fully reproduced in these excerpts.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6557ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### T02 — IBEW

**Question:** How far from home must an IBEW Generation worker be to qualify for board allowance?

**Answer:**

# Board Allowance Distance Threshold for IBEW Generation Workers

An IBEW Generation worker must be **greater than or equal to 110 road-driven kilometers** from their home (regular residence) to qualify for room and board allowance.

## Supporting Clause Text

According to Article 1101 A of the IBEW Generation 2025-2030 Collective Agreement:

> "The following conditions will apply for employees whose Room and Board regular residence* is greater than or equal to 110 road-driven kilometers from the project" [SOURCE 4, Article 1101 A]

This threshold is consistently applied across different project locations:

- **North of the French River:** "When an employee's regular residence is greater than or equal to 110 road-driven kilometers from a Project located North of the French River and the employee maintains temporary accommodation at or near the Project, the employee shall be paid a subsistence allowance" [SOURCE 5, Article 1101 A(ii)(a)]

- **South of the French River:** "When an employee's regular residence is greater than or equal to 110 road-driven kilometers from a Project located South of the French River and the employee maintains temporary accommodation at or near the project, the employee shall be paid a subsistence allowance" [SOURCE 2, Article 1101 A(ii)(b)]

- **Pickering, Darlington, and Bruce Power Projects:** "At the Pickering and Darlington Projects, employees who live beyond 110 road-driven kilometers from the Project, shall receive the rates as set out below" [SOURCE 2, Article 1101 A(ii)(d)]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 4 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4832ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### T03 — Sheet Metal

**Question:** What is the subsistence allowance for Sheet Metal workers working away from home?

**Answer:**

# Subsistence Allowance for Sheet Metal Workers Working Away from Home

The provided documents reference subsistence allowance but **do not contain the specific dollar amounts** for Sheet Metal workers.

## What the Documents Show

The collective agreement establishes that Sheet Metal workers qualify for subsistence allowance under the following conditions:

**Eligibility:** An employee whose regular residence is greater than or equal to 110 road-driven kilometers from the project may exercise the option not to stay in camp or accept free room and board, and shall receive a subsistence allowance instead [SOURCE 2, Section 32.1(b) and SOURCE 7, Section 26.2(b)].

**Regional Variation:** The agreement divides Ontario into regions with different subsistence allowance rates:
- Northern region (geographic area north of a line drawn between the mouth of the French River and Mattawa)
- Southern region (all remaining geographic areas except the Northern region)
- Special provisions for the Bruce Project and Pickering/Darlington Nuclear Projects [SOURCE 2, Section 32.1(b)(i)-(v) and SOURCE 7, Section 26.2(b)(i)-(v)]

However, the actual subsistence allowance rates are noted as "to be set out below" in the clauses [SOURCE 2, SOURCE 7] but the rate tables themselves are **not included in the provided documents**.

The provided documents do not contain the specific dollar amounts for subsistence allowance by region or year.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5243ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### T04 — Sheet Metal

**Question:** What are the travel zone provisions for Sheet Metal workers?

**Answer:**

# Travel Zone Provisions for Sheet Metal Workers

Sheet Metal workers are subject to **two different travel zone systems** depending on the type of project. The documents contain conflicting provisions, so you must determine which applies to your specific work location.

## System 1: Nuclear/OPG Generation Projects (Articles 26.1-26.3)

[SOURCE 2, Section 26.1] and [SOURCE 4] establish five travel zones based on distance from the **project**:

- **Less than 50 km**: No travel allowance [SOURCE 2, 26.1(a)]
- **50–70 km**: $33.14–$36.58 per day (depending on year) [SOURCE 4, rates table]
- **70–96 km**: $38.50–$42.50 per day [SOURCE 4, rates table]
- **96–110 km**: $42.00–$46.36 per day [SOURCE 4, rates table]
- **≥110 km**: $60.00 per day, provided employee travels ≥110 km daily and does not receive room and board [SOURCE 2, 26.1(e)]

Distance is measured as "the shortest available road-driven distance from where an employee lives to the project as measured through Google Maps." [SOURCE 2, 26.1]

## System 2: Other Work Locations (Articles 27.1-27.5)

[SOURCE 1, Section 27.1] and [SOURCE 3] establish five travel zones based on distance to either the **work location or declared assembly point**:

- **Less than 50 km**: No travel allowance [SOURCE 1, 27.1(a)]
- **50–70 km**: $32.56–$35.94 per day (depending on year) [SOURCE 3, rates table]
- **70–96 km**: $37.14–$41.00 per day [SOURCE 3, rates table]
- **96–110 km**: $42.00–$46.36 per day [SOURCE 3, rates table]
- **≥110 km**: $60.00 per day, provided employee travels ≥110 km daily and does not receive room and board [SOURCE 1, 27.1(e)]

Distance is measured as "the shortest available road-driven distance from where an employee lives to either the work location or declared assembly point, depending on where the employee is directed to report, as measured through Google Maps." [SOURCE 3, 27.3]

## Key Exclusions

Employees are **disqualified** from travel allowance if they report for work but do not remain for their scheduled hours, unless excused by an authorized employer representative [SOURCE 6, 27.5] and [SOURCE 8, 26.3].

Employees using company vehicles are not entitled to daily travel allowance [SOURCE 1, 27.1(f)] and [SOURCE 2, 26.1(f)].

## Remote Project Travel Time (Locals 397 & 504)

For OPG Generation Construction Projects in the jurisdiction of Locals 397 and 504, when employees receive room and board on remote projects with loose-surface roads and accommodation >50 km away, additional travel time compensation applies: ½ to 2 hours regular pay depending on distance, or actual time if over 160 km [SOURCE 7, Section 2.0].

## Non-Ontario Residents

For tradespeople living outside Ontario and >189 km from the project, employers must pay public transportation costs plus travel time (1 hour per 96 km, max 8 hours) for the initial trip [SOURCE 10, 29.3].

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 27.1 |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 26.1 |
| 3 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |
| 4 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |
| 6 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 27.5 |
| 7 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |
| 8 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 26.3 |
| 10 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 29.3 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 8554ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### T05 — United Association

**Question:** How is travel time compensated for United Association plumbers under the 2025-2030 agreement?

**Answer:**

# Travel Time Compensation for United Association Plumbers (2025-2030)

Travel time compensation under the United Association 2025-2030 agreement varies significantly depending on the context and circumstances. Here are the main provisions:

## 1. **OPG Remote Projects (Local 800 & 628)**

For employees on remote Ontario Power Generation construction projects receiving Room and Board allowance, where accommodation is more than 40 road kilometers from the job site, compensation is based on distance traveled from the nearest accommodation [SOURCE 1, Section 28.6]:

- **40–56 km:** ½ hour regular time pay
- **57–80 km:** 1 hour regular time pay
- **81–120 km:** 1½ hours regular time pay
- **121–160 km:** 2 hours regular time pay
- **Over 160 km:** Actual travel time paid at regular time rate

**Important limitation:** If the employer provides a vehicle or transportation, these travel time provisions do not apply [SOURCE 1, Section 28.6]. Additionally, return travel from the work location to the assembly point is unpaid [SOURCE 1, Section 28.6].

## 2. **Employee Transfers**

When employees are transferred to a new project location, the employer pays travelling time at straight-time rates based on one hour's pay for each 96 road-driven kilometers of travel, capped at a maximum of 8 hours' pay [SOURCE 3, Section 30.6 and SOURCE 5, Section 31.6]. The employer also covers the equivalent cost of public transportation for the initial trip [SOURCE 3, Section 30.6; SOURCE 5, Section 31.6].

## 3. **New Recruitment – Ontario Residents**

For Ontario residents recruited from beyond 189 road-driven kilometers from the project, travel time is calculated at one hour's pay for each 96 road-driven kilometers, capped at 8 hours' pay [SOURCE 8, Section 30.2 and SOURCE 9, Section 31.2]. Additionally, employers pay 35¢ per road-driven kilometer and the equivalent cost of public transportation [SOURCE 8, Section 30.2; SOURCE 9, Section 31.2].

## 4. **New Recruitment – Non-Ontario Residents**

For non-Ontario residents recruited from beyond 189 road-driven kilometers from the project, travel time is calculated at one hour's pay for each 96 road-driven kilometers, capped at 8 hours' pay [SOURCE 4, Section 30.3 and SOURCE 7, Section 31.3]. The employer also pays the equivalent cost of public transportation [SOURCE 4, Section 30.3; SOURCE 7, Section 31.3].

## 5. **Apprentices**

Apprentices who do not qualify for Room and Board but live more than 110 road-driven kilometers from the project receive daily travel rates as specified in Article 28.1(e) [SOURCE 10, Letter of Understanding #8].

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association 2025-2030 Collective Agreement |  | 28.6 |
| 3 | United Association | United Association 2025-2030 Collective Agreement |  | 30.6 |
| 4 | United Association | United Association 2025-2030 Collective Agreement |  | 30.3 |
| 8 | United Association | United Association 2025-2030 Collective Agreement |  | 30.2 |
| 10 | United Association | United Association 2025-2030 Collective Agreement |  | 9.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7047ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

## Nuclear Project Specific

### N01 — IBEW

**Question:** Are there different overtime rules for IBEW Generation workers at a nuclear project site?

**Answer:**

# IBEW Generation Overtime Rules at Nuclear Project Sites

Yes, there are different overtime rules for IBEW Generation workers depending on their work schedule, including specific provisions that apply to nuclear project sites.

## Overtime Rules by Work Schedule

**For 8-hour, 5-day per week schedules:**
Overtime is paid at 1½ times the basic hourly rate for all hours worked beyond the normal daily scheduled hours up to a maximum of 2 hours per day. All hours in excess of 10 hours per day are paid at 2 times the base hourly rate. [SOURCE 5, Section 806 A]

**For 10-hour, 4-day per week schedules (including nuclear sites):**
Overtime is paid at 1½ times the basic hourly rate for all hours worked beyond the normal daily scheduled hours up to a maximum of 2 hours per day. All hours in excess of 12 hours per day are paid at 2 times the base hourly rate. [SOURCE 1, Section 806 A]

## Additional Nuclear Project Considerations

At nuclear project sites specifically, the start time for the day shift shall be between 6:00 AM and 9:00 AM, which differs from other locations that have 8:00 AM with a possible one-hour variance. [SOURCE 2, Page 19]

Additionally, unapproved absences may result in the loss of overtime opportunities at the Employer's discretion, with such applications subject to referral to the Nuclear Project Committee. [SOURCE 1, Section 806 A]

All overtime must be worked on a voluntary basis and distributed as equally as possible among all IBEW members. [SOURCE 1, Section 806 C]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5734ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### N02 — IBEW

**Question:** What additional provisions apply to IBEW Generation electricians working at Darlington?

**Answer:**

Based on the provided sources, I cannot identify any provisions that apply specifically to IBEW Generation electricians working at Darlington.

The documents describe the scope of the IBEW Generation 2025-2030 Collective Agreement as applying to work on "Ontario Power Generation Inc. (OPGI) and Bruce Power LP facilities" [SOURCE 2, Section 200 A (iii)]. However, the provided sources do not mention Darlington by name, nor do they contain any facility-specific provisions that would distinguish Darlington from other OPGI or Bruce Power LP generating stations.

The agreement does contain special provisions for "Nuclear sites" in contexts such as security clearance requirements and training [SOURCE 4, Section 701 A (iv) and SOURCE 6, Section 701 A (iv)], but these are presented as general nuclear site provisions rather than Darlington-specific terms.

To answer your question comprehensively, I would need access to:
- Facility-specific appendices or schedules identifying Darlington
- Any separate Darlington Project Agreement
- Additional pages of the Generation Agreement that may contain location-specific provisions

The provided documents do not contain information about Darlington-specific provisions.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 4 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4407ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### N03 — Sheet Metal

**Question:** What special conditions apply to Sheet Metal workers under the Nuclear Project Agreement?

**Answer:**

# Sheet Metal Workers — Special Conditions Under the Nuclear Project Agreement

Several special conditions apply to Sheet Metal workers under the Nuclear Project Agreement:

## 1. **Scope of Application**

The Nuclear Project Agreement applies only to work performed by Building Trades Unions on existing Ontario Power Generation Inc. (OPG) nuclear sites (Pickering, Darlington, Bruce) and Bruce Power LP property, and it supersedes the current EPSCA collective agreement for these projects. [SOURCE 1, Section 1.1]

## 2. **Nuclear Qualified Worker (NQW) Requirements**

Workers must obtain Nuclear Qualified Worker (NQW) status to access certain referral and transfer opportunities:

- During the first two years of the agreement, priority is given to NQWs but referral of NQWs is not mandatory. After the first two years, only NQWs will be referred. [SOURCE 10, Section 5.1]
- Transfers between sites are permitted only if employees are already NQWs and the local union with jurisdiction has no NQWs available. [SOURCE 6, Section 5.2(B)]
- Transfers to the same employer in different sectors require NQW status. [SOURCE 6, Section 5.2(C)]

## 3. **Protection Against Displacement**

Once hired onto a nuclear site, travelers and permit workers cannot be displaced or bumped by other members. Any disputes are referred to the Project Committee. [SOURCE 2, Section 6.1]

## 4. **Restricted Transfers Between Employers**

Transfers between employers are limited to: short-term work assignments (14 calendar days); emergent work with specific skill requirements; or radiological dose management. [SOURCE 6, Section 5.2(A)]

## 5. **Composite Crew Restrictions**

The "One Person, One Job" principle governs composite crew formation, which does not establish precedent or authorize assignment of workers outside their usual skill classification under regular operating conditions. Composite crews are determined no later than at the Mark-Up Meeting with prior notice to the Local Unions involved. [SOURCE 4, Section 11.1]

## 6. **Standoff Provisions**

Employers may standoff employees (without pay) for up to ten consecutive working days without triggering layoff procedures. No travel allowance is paid during standoff, and subsistence allowance is only paid when proof of temporary residence is provided. [SOURCE 8, Section 10.1(b)]

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 1.1 |
| 2 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 6.1 |
| 4 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 11.1 |
| 6 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 5.2 |
| 8 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 10.1 |
| 10 | Sheet Metal | Sheet Metal Nuclear Project Agreement |  | 5.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7975ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### N04 — United Association

**Question:** Do United Association workers receive any premium for working on a nuclear project site?

**Answer:**

# Nuclear Project Premium Pay for United Association Workers

Yes, United Association workers receive a premium for working on nuclear project sites. Specifically, employees working in radiation areas receive an additional daily payment:

**Radiation Protection Premium:**
Employees working in a radiation area while wearing plastic suits or replacement material of the fully enveloping type with an independent air supply will receive **$20.00 per day effective May 1, 2025** [SOURCE 2, Section 41.1(e)].

This premium is paid in addition to regular wages and applies to work on Ontario Power Generation Inc. and Bruce Power LP nuclear projects, which fall under the scope of this collective agreement [SOURCE 1, Section 1.1; SOURCE 2, Section 41.1(a)].

The agreement also includes radiation protection regulations compliance provisions [SOURCE 2, Section 41.1(a)-(d)], protections for employees who reach exposure limits, and guaranteed employment periods for affected workers.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association 2025-2030 Collective Agreement |  | 48.1 |
| 2 | United Association | United Association 2025-2030 Collective Agreement |  | 41.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4371ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### N05 — IBEW

**Question:** What are the travel provisions for IBEW Generation workers under the Nuclear Project Agreement?

**Answer:**

# Travel Provisions for IBEW Generation Workers Under the Nuclear Project Agreement

The provided documents do not contain detailed travel provisions specific to the Nuclear Project Agreement. 

**What is available:**

The IBEW Nuclear Project Agreement [SOURCE 2, Section 6.1, Page 3] addresses worker displacement, stating: "Once a worker is hired onto a site covered by this agreement, travelers and/or permit workers shall not be displaced and/or bumped by any other member."

However, the substantive travel allowance, accommodation, and transportation terms are contained in the **IBEW Generation 2025-2030 Collective Agreement** [SOURCE 1, 3, 4, 5, 6, 8, 9], which covers:

- **Daily Travel Allowances** based on distance from project (Article 1100) [SOURCE 8]
- **Room and Board/Subsistence Allowances** for employees living 110+ km from the project (Article 1101) [SOURCE 9]
- **Initial and Return Travel Expenses** for recruits from distances of 110-189 km and beyond (Article 1102) [SOURCE 3, 4]

**Critical Note:** The sources do not clarify whether the detailed travel provisions in the Generation agreement apply to workers on nuclear sites or whether different terms govern nuclear projects specifically. The Nuclear Project Agreement excerpt provided addresses only worker protection against displacement, not the payment structure for travel or accommodation. You may need to consult the complete Nuclear Project Agreement or labour relations counsel to determine whether the Generation agreement provisions apply or whether separate nuclear-specific travel terms exist.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Nuclear Project Agreement |  | 6.1 |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 9 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 11228ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### N06 — Boilermakers

**Question:** What special conditions apply to Boilermakers working at Darlington under their Nuclear Project Agreement?

**Answer:**

# Special Conditions for Boilermakers at Darlington Under the Nuclear Project Agreement

The provided documents establish that a separate **Nuclear Project Agreement** governs work at Darlington, which supersedes the Primary Collective Agreement in that context.

## Key Special Conditions:

**1. Agreement Scope and Applicability**

The Nuclear Project Agreement applies specifically to Darlington and other Ontario Power Generation nuclear sites. [SOURCE 5, Section 1.1] states: "This agreement shall apply only to work performed by the Building Trades Unions (BTU) notwithstanding the current EPSCA (and or OPG/Bruce Power) Collective Agreements. This agreement shall apply on existing Ontario Power Generation Inc (OPGI) Nuclear Sites (Pickering, Darlington, Bruce) and Bruce Power LP property."

**2. Transfer Restrictions**

[SOURCE 7, Section 5.2] establishes special transfer conditions:
- Transfers between employers at Darlington are limited to: short-term work assignments (14 calendar days); emergent work requiring specific skills; or radiological dose management.
- Transfers to other nuclear sites require employees to be Nuclear Qualified Workers (NQWs) and require notification to the Local Union.
- Previously dispatched employees cannot be laid off to accommodate such transfers.

**3. Harmonious Work Requirement**

[SOURCE 8, Section 11.3] requires that "all employees will work together harmoniously as a group and as directed by the Employer."

**4. Subsistence Allowance**

Boilermakers employed at Darlington whose regular residence is 110+ kilometers from the project and who maintain temporary accommodation receive a subsistence allowance. [SOURCE 6, page 29]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 5 | Boilermakers | Boilermakers Nuclear Project Agreement |  | 1.1 |
| 6 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  |  |
| 7 | Boilermakers | Boilermakers Nuclear Project Agreement |  | 5.2 |
| 8 | Boilermakers | Boilermakers Nuclear Project Agreement |  | 11.3 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4669ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

## Cross-Union Comparison

### C01 — IBEW / Sheet Metal

**Question:** Compare the overtime rules for IBEW Generation and Sheet Metal workers under their 2025-2030 agreements.

**Answer:**

## Overtime Rules Comparison: IBEW Generation vs. Sheet Metal Workers (2025–2030)

---

### 1. Overtime Pay Rates

**IBEW Generation:**

- **8-hour/5-day schedule:** The provided sources do not explicitly state the 1.5x threshold for the standard 8-hour day schedule in the excerpts available, though the 10-hour schedule is detailed.
- **10-hour/4-day schedule (Monday–Friday):** Overtime is paid at **1.5× the basic hourly rate** for all hours beyond the normal daily scheduled hours, up to a maximum of **2 hours per day**. All hours **in excess of 12 hours per day** are paid at **2× the base hourly rate**. [SOURCE 9, Page 24]
- **Saturday, Sunday, Recognized Holidays, and non-shift days:** Overtime is paid at **2× the basic hourly rate**. [SOURCE 9, Page 24]

**Sheet Metal Workers:**

- **8-hour/5-day schedule (Monday–Friday):** Overtime is paid at **1.5× the basic hourly rate** for all hours beyond the normal daily scheduled hours, up to a maximum of **2 hours per day**. All hours **in excess of 10 hours per day** are paid at **2× the base hourly rate**. [SOURCE 10, Article 23.1, Page 28]
- **10-hour/4-day schedule (Monday–Friday):** Overtime is paid at **1.5× the basic hourly rate** for all hours beyond the normal daily scheduled hours, up to a maximum of **2 hours per day**. All hours **in excess of 12 hours per day** are paid at **2× the base hourly rate**. [SOURCE 10, Article 23.1, Page 28]
- **Saturday, Sunday, Recognized Holidays, and non-shift days:** Overtime is paid at **2× the basic hourly rate**. [SOURCE 10, Article 23.1, Page 28]

> **⚠️ Key Difference – 8-hour day double-time threshold:** Under the Sheet Metal agreement, the double-time trigger on an 8-hour schedule is **10 hours per day** [SOURCE 10, Article 23.1]. The provided IBEW Generation sources do not contain an equivalent explicit provision for the 8-hour/5-day schedule — this gap should not be assumed to mean the provision does not exist; it may appear elsewhere in the full agreement.

---

### 2. Overtime Rest Periods

**IBEW Generation:**

- Employees **required to work overtime** receive a **10-minute rest period** prior to the end of the normal shift before commencing overtime. [SOURCE 3, Page 21, Subsection B]
- Employees **working overtime** receive a **15-minute rest period**, at the time directed by the Employer, **after each 2 hours of overtime worked**. [SOURCE 3, Page 21, Subsection C]

**Sheet Metal Workers:**

- Employees **required to work two (2) hours of overtime** receive a **10-minute rest period** prior to the end of the normal shift before commencing overtime. [SOURCE 6, Article 24.2, Page 29]
- Employees **working overtime** receive a **15-minute rest period**, at the time directed by the Employer, **after each 2 hours of overtime worked**. [SOURCE 8, Article 24.3, Page 29]

> **Observation:** The rest period entitlements are substantively identical between the two agreements, though a minor textual distinction exists: the Sheet Metal agreement qualifies the pre-overtime rest period as applying when "two (2) hours of overtime" are required [SOURCE 6, Article 24.2], while the IBEW Generation agreement applies it more broadly to employees "required to work overtime" without that specific qualifier [SOURCE 3, Page 21].

---

### 3. Overtime Meal Provisions

**IBEW Generation:**

- If an employee has **not been notified the previous day** that they will work more than 2 hours beyond normal quitting time: after approximately 2 hours of overtime, they shall receive a **lunch and 30 minutes paid at base hourly rate** to consume it. After each additional **4 hours**, the same entitlement applies. If a hot meal cannot be supplied, the Employer pays **$25.00**. [SOURCE 9, Page 24]
- If an employee **has been notified the previous day**: no lunch is provided, but the employee receives **30 minutes paid at base hourly rate** to eat. [SOURCE 9, Page 24]
- A paid meal period **supplants** any overlapping rest period. [SOURCE 9, Page 24]
- These meal provisions are **not applicable to the first 8 hours** worked on Saturdays, Sundays, and Recognized Holidays. [SOURCE 9, Page 24]

**Sheet Metal Workers:**

The provided Sheet Metal sources reference that "overtime will be paid in accordance with Article 23 – Overtime Rates" [SOURCE 2, Page 59] but do **not include specific meal period provisions** for overtime in the excerpts provided.

> **The provided documents do not contain information about Sheet Metal Workers' overtime meal entitlements.** This should not be interpreted as an absence of such provisions in the full agreement.

---

### 4. Voluntary Nature of Overtime

**IBEW Generation:**

- **All overtime shall be worked on a voluntary basis** and shall be distributed as equally as possible among all IBEW members. [SOURCE 1, Page 24, Section C]
- An unapproved employee absence may, at the **Employer's discretion**, disentitle the employee to overtime opportunities; this is subject to referral to the **Nuclear Project Committee**. [SOURCE 9, Page 24]

**Sheet Metal Workers:**

The provided Sheet Metal sources are **silent on whether overtime is voluntary** or how overtime opportunities are distributed. This should not be assumed to mean no such provision exists in the full agreement.

---

### Summary Table

| Provision | IBEW Generation | Sheet Metal Workers |
|---|---|---|
| **OT rate (8hr day, beyond normal hours, up to 2 hrs)** | Not explicit in provided sources | **1.5×** [SOURCE 10, Art. 23.1] |
| **Double-time trigger (8hr schedule)** | Not explicit in provided sources | **>10 hrs/day** [SOURCE 10, Art. 23.1] |
| **OT rate (10hr day, beyond normal hours, up to 2 hrs)** | **1.5×** [SOURCE 9, p.24] | **1.5×** [SOURCE 10, Art. 23.1] |
| **Double-time trigger (10hr schedule)** | **>12 hrs/day** [SOURCE 9, p.24] | **>12 hrs/day** [SOURCE 10, Art. 23.1] |
| **Saturday/Sunday/Holiday OT rate** | **2×** [SOURCE 9, p.24] | **2×** [SOURCE 10, Art. 23.1] |
| **Pre-overtime rest period** | 10 min [SOURCE 3, p.21] | 10 min [SOURCE 6, Art. 24.2] |
| **During-overtime rest period** | 15 min per 2 hrs [SOURCE 3, p.21] | 15 min per 2 hrs [SOURCE 8, Art. 24.3] |
| **Overtime meal provisions** | Detailed provisions [SOURCE 9, p.24] | Not in provided sources |
| **Voluntary overtime** | Yes, equally distributed [SOURCE 1, p.24] | Not in provided sources |

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 6 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 24.2 |
| 8 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 24.3 |
| 9 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 10 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 23.1 |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 33667ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### C02 — IBEW / United Association

**Question:** Which union has the higher journeyperson base rate as of May 2025: IBEW Generation or United Association?

**Answer:**

## Journeyperson Base Rate Comparison as of May 1, 2025: IBEW Generation vs. United Association

The answer depends on which specific local is used for comparison, as both unions have multiple locals with different rates. Below is a structured comparison using all available May 2025 data from the provided sources.

---

### IBEW Generation Locals (May 1, 2025)

**IBEW Local 115 (Quinte/St. Lawrence) — Journeyman/Welder/Communications Electrician:**
Base hourly rate = **$48.63**
[SOURCE 5] — Wage Schedule E-12-C, Effective 2025-05-01

**IBEW Local 530 (Sarnia) — Journeyman (implied from apprentice rates):**
The provided documents for LU 530 [SOURCE 7, SOURCE 9] only show **apprentice** classifications (1st Period at 40% and 2nd Period at 50% of journeyman rate). Working backwards from the 1st Period rate of $21.99 (40% of journeyman), the implied journeyman rate would be approximately $54.98 — **however, no journeyman wage schedule for LU 530 is directly provided in the source documents.** I cannot confirm this figure as a cited rate.

---

### United Association Locals (May 1, 2025)

**UA Local 71 (Ottawa) — Journeyman/Pipewelder:**
Base hourly rate = **$49.87**
[SOURCE 2] — Wage Schedule UA-14, Effective 2025-05-01

**UA Local 800 (Sudbury) — Journeyman/Pipewelder:**
Base hourly rate = **$47.96**
[SOURCE 4] — Wage Schedule UA-15, Effective 2025-05-01

**UA Local 800 (Sault Ste. Marie) — Journeyman/Pipewelder:**
Base hourly rate = **$47.14**
[SOURCE 6] — Wage Schedule UA-16, Effective 2025-05-01

---

### Summary Table (May 1, 2025 — Journeyperson Base Rates)

| Union & Local | Base Rate (May 2025) | Source |
|---|---|---|
| IBEW LU 115 (Quinte/St. Lawrence) — Generation | $48.63 | [SOURCE 5] |
| IBEW LU 530 (Sarnia) — Generation | Not directly provided | [SOURCE 7, 9] |
| UA LU 71 (Ottawa) | $49.87 | [SOURCE 2] |
| UA LU 800 (Sudbury) | $47.96 | [SOURCE 4] |
| UA LU 800 (Sault Ste. Marie) | $47.14 | [SOURCE 6] |

---

### Key Findings

- Among the **directly confirmed journeyman rates**, **UA Local 71 (Ottawa) has the highest base rate at $49.87/hr** as of May 1, 2025, exceeding the only confirmed IBEW Generation journeyman rate (LU 115 at $48.63/hr) by **$1.24/hr**.
- **UA Local 800 (Sudbury) at $47.96** and **UA Local 800 (Sault Ste. Marie) at $47.14** are both **below** the IBEW LU 115 Generation rate of $48.63.
- **The IBEW LU 530 (Sarnia) Generation journeyman rate is not directly stated** in the provided documents and cannot be cited with certainty.

> ⚠️ **Important limitation:** The provided sources cover only a subset of IBEW Generation and United Association locals. Other locals not represented in these documents may have different rates. A complete comparison would require all applicable wage schedules.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 4 | United Association | United Association Wage Schedule Local 800 Sudbury |  |  |
| 5 | IBEW | IBEW Generation Wage Schedule E-12-C LU 115 Quinte |  |  |
| 6 | United Association | United Association Wage Schedule Local 800 Sault S |  |  |
| 7 | IBEW | IBEW Generation Wage Schedule E-3-C LU 530 Sarnia  |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 18856ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### C03 — Carpenters / Ironworkers

**Question:** Which union has the higher journeyperson base rate in Windsor as of May 2025: Carpenters or Ironworkers?

**Answer:**

## Journeyperson Base Rate Comparison — Windsor, Effective May 1, 2025

**The Ironworkers have the higher journeyperson base rate in Windsor as of May 2025.**

Here is the breakdown by union:

---

### Carpenters — Local 494 (Windsor)

The Carpenters have **two relevant journeyperson classifications** in Windsor for May 2025:

- **Journeyman (Carpenter / Welder & Burner):** base hourly rate **$44.69**
[SOURCE 3] — Carpenters Wage Schedule C-1 LU 494 Windsor, Classification: JOURNEYMAN / WELDER & BURNER (grade/step 01-6, 02-6), effective 2025-05-01.

- **Journeyman (Resilient Floor Worker):** base hourly rate **$43.78**
[SOURCE 1] — Carpenters Wage Schedule RF-1 LU 494 Windsor, Classification: JOURNEYMAN (grade/step 03-6), effective 2025-05-01.

The highest Carpenters journeyperson base rate in Windsor as of May 2025 is **$44.69/hr**.

---

### Ironworkers — Local 700 (Windsor)

- **Journeyman Ironworker / Rigger:** base hourly rate **$48.33**
[SOURCE 2] — Ironworkers Generation Wage Schedule I-1 LU 700 Windsor, Classification: JOURNEYMAN IRONWORKER, RIGGER (grade/step 19-6), effective 2025-05-01.
[SOURCE 4] — Ironworkers Transmission Wage Schedule I-1 LU 700 Windsor, same classification and rate, effective 2025-05-01.

Both the Generation and Transmission schedules for Ironworkers LU 700 Windsor confirm the same journeyperson base rate of **$48.33/hr**.

---

### Summary

| Union | Classification | Base Rate (May 1, 2025) | Source |
|---|---|---|---|
| Carpenters LU 494 | Journeyman (Carpenter) | $44.69/hr | [SOURCE 3] |
| Carpenters LU 494 | Journeyman (Resilient Floor) | $43.78/hr | [SOURCE 1] |
| Ironworkers LU 700 | Journeyman Ironworker/Rigger | **$48.33/hr** | [SOURCE 2], [SOURCE 4] |

The **Ironworkers Local 700 Windsor** journeyperson base rate of **$48.33/hr** exceeds the highest Carpenters Local 494 Windsor journeyperson base rate of **$44.69/hr** by **$3.64/hr** as of May 1, 2025.

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Carpenters | Carpenters Resilient Floor Wage Schedule RF-1 LU 4 |  |  |
| 2 | Ironworkers | Ironworkers Generation Wage Schedule I-1 LU 700 Wi |  |  |
| 3 | Carpenters | Carpenters Wage Schedule C-1 LU 494 Windsor |  |  |
| 4 | Ironworkers | Ironworkers Transmission Wage Schedule I-1 LU 700  |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 12479ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 44.69, 48.33)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### C04 — Cement Masons / Plasterers

**Question:** Compare the foreman hourly rates for Cement Masons and Plasterers in Windsor as of May 2025.

**Answer:**

## Foreman Hourly Rates — Windsor, Effective May 1, 2025

Here is a direct comparison of the Foreman classification base hourly rates and total wage packages for the two Windsor unions as of May 1, 2025:

---

### Cement Masons — Local 598 (Windsor)

**Source:** Wage Schedule CM-1, Foreman classification (occupation code 430065; grade/step 16-9)

| Component | Rate (2025-05-01) |
|---|---|
| Base Hourly Rate | **$43.96** |
| Vacation & Statutory Holiday Pay | $4.40 |
| Union Funds | $13.54 |
| **Total Wage Package** | **$61.90** |
| EPSCA Association Fund | $0.30 |

[SOURCE 1]

---

### Plasterers — Local 124 (Windsor)

**Source:** Wage Schedule PL-1, Foreman classification (occupation code 430365; grade/step 17-9)

| Component | Rate (2025-05-01) |
|---|---|
| Base Hourly Rate | **$52.57** |
| Vacation & Statutory Holiday Pay | $5.26 |
| Union Funds | $6.89 |
| **Total Wage Package** | **$64.72** |
| EPSCA Association Fund | $0.30 |

[SOURCE 2]

---

### Summary of Differences

| | Cement Masons LU 598 (Windsor) | Plasterers LU 124 (Windsor) | Difference |
|---|---|---|---|
| Base Hourly Rate | $43.96 | $52.57 | **+$8.61 in favour of Plasterers** |
| Total Wage Package | $61.90 | $64.72 | **+$2.82 in favour of Plasterers** |

**Key observations:**
- The Plasterers Foreman base hourly rate ($52.57) is **$8.61 higher** than the Cement Masons Foreman base rate ($43.96) as of May 1, 2025. [SOURCE 1; SOURCE 2]
- However, the gap narrows significantly at the **total wage package** level ($2.82 difference), largely because the Cement Masons carry substantially higher union funds ($13.54 vs. $6.89). [SOURCE 1; SOURCE 2]
- The EPSCA Association Fund is identical for both unions at $0.30. [SOURCE 1; SOURCE 2]

---

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Cement Masons | Cement Masons Wage Schedule CM-1 Local 598 Windsor |  |  |
| 2 | Plasterers | Plasterers Wage Schedule PL-1 LU 124 Windsor |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 12160ms  
**Query log ID:** `N/A`

**Auto-check:** PASS (found: 43.96, 52.57)

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

## Refusal

### R01 — Boilermakers

**Question:** What are the pension benefits for retired Boilermakers under EPSCA agreements?

**Answer:**

Based on the provided sources, the documents do not contain comprehensive information about pension benefits for retired Boilermakers under EPSCA agreements.

**What the sources do address:**

The Boilermakers - 2025 to 2030 Collective Agreement discusses pension contributions but not retirement benefits themselves:

[SOURCE 2, Section 31.1] states: "The Employer agrees to pay into operative health and pension funds established by agreement between the Union and contractors engaged in construction work the hourly contributions specified in the attached wage schedules for all hours paid excluding travel time."

[SOURCE 1, Section 31.6] addresses a special rule for employees aged 71 and older: "On November 30th, 2022, the Employer shall cease pension contributions to the Boilermakers' National Pension Plan (Canada), on behalf of those employees who are seventy-one (71) years of age or older. The pension contributions that would otherwise be payable to the Boilermakers' National Pension Plan (Canada) will be paid on behalf of the applicable employee to the Boilermakers' National Health Plan (Canada)."

**What is not in the sources:**

The provided documents do not specify what pension benefits are actually paid to retirees, the formula for calculating benefits, vesting requirements, or other details about retirement income. The documents reference "the Boilermakers' National Pension Plan (Canada)" but do not include the plan document itself.

To obtain information about actual retirement benefits, you would need to consult the Boilermakers' National Pension Plan document or contact the plan administrator directly.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  | 31.6 |
| 2 | Boilermakers | Boilermakers - 2025 to 2030 Collective Agreement 2 |  | 31.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5406ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### R02 — IBEW

**Question:** What is the grievance arbitration process for IBEW Transmission workers at Bruce Power?

**Answer:**

# Grievance Arbitration Process for IBEW Transmission Workers

The grievance and arbitration process for IBEW Transmission workers consists of three main stages: preliminary discussion, a formal two-step grievance procedure, and arbitration if unresolved.

## Grievance Definition and Scope

Grievances are limited to disputes about the interpretation or application of the collective agreement, or alleged violations of it [SOURCE 1, Section 1400A]. The parties must attempt resolution without work disruption [SOURCE 1, Section 1400A].

## Grievance Procedure Steps

**Preliminary Discussion:** Disputes should first be settled by discussion between the employee and/or their steward and the employee's supervisor [SOURCE 1, Section 1400B].

**First Step:** If unresolved, the Accredited Union Representative may file a formal grievance within fifteen (15) working days of the alleged grievous act [SOURCE 1, Section 1400C]. The Employer must investigate and convene a meeting within ten (10) working days, then provide a reply within five (5) working days [SOURCE 1, Section 1400C]. For disciplinary matters (unjustified termination, discharge, suspension, or disciplinary action), grievances may begin at the First Step [SOURCE 2, Section 1400G].

**Second Step:** If unresolved at First Step, the Accredited Union Representative may refer the grievance to the appropriate EPSCA Representative within ten (10) working days after the First Step disposition [SOURCE 5, Section 1400D]. EPSCA or the Employer must investigate and reply within five (5) working days from receipt [SOURCE 5, Section 1400D].

## Arbitration Process

If the grievance is not settled through the two-step procedure, either party may submit the matter to a **Board of Arbitration** within thirty (30) days of the grievance procedure's failure to settle [SOURCE 3, Section 1401A].

**Arbitration Board Composition:** The board consists of three members—one nominee appointed by each party and a Chairperson jointly appointed by the two nominees within ten (10) working days [SOURCE 3, Section 1401A]. If either party fails to appoint a nominee or if the nominees cannot agree on a Chairperson, the Minister of Labour for Ontario makes the appointment [SOURCE 3, Section 1401A].

**Authority and Decision:** The arbitration board's decision is final and binding [SOURCE 3, Section 1401A]. A majority decision governs; if there is no majority, the Chairperson's decision controls [SOURCE 3, Section 1401A]. The board cannot add to, subtract from, or modify the agreement terms, except that it may substitute a just and reasonable penalty for discharge or discipline when the agreement contains no specific penalty for the infraction [SOURCE 4, Section 1401B].

**Costs:** Each party pays the fees and expenses of its nominee; the Chairperson's fees and expenses are shared equally by the parties [SOURCE 4, Section 1401C].

## Time Limits and Extensions

Time limits must be complied with; however, parties may mutually agree in writing to extend or waive time limits [SOURCE 2, Section 1400F]. If no answer is given within specified timeframes, the grieving party may submit to the next step [SOURCE 2, Section 1400F]. Any grievance not processed within the specified time limits is deemed withdrawn and ineligible for arbitration [SOURCE 2, Section 1400F].

## Exclusive Remedy

Disputes cannot be processed under Section 133 of the Labour Relations Act of Ontario until the grievance and arbitration provisions of the agreement have been fully exhausted [SOURCE 2, Section 1400H].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 3 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 4 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |
| 5 | IBEW | IBEW Transmission - 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 11335ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### R03 — N/A (out of corpus)

**Question:** What is the wage rate for Elevator Constructors under EPSCA agreements?

**Answer:**

The provided documents do not contain information about wage rates for Elevator Constructors under EPSCA agreements.

The sources provided include wage schedules for Teamsters classifications (Sources 1–5) and collective agreement references for Ironworkers, Labourers, and Brick and Allied Craft Union (Sources 6–10), but none of these documents specify an Elevator Constructors classification or wage rates for that trade.

To find Elevator Constructors wage rates, you would need to consult the specific EPSCA collective agreement or wage schedule that covers that trade classification.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2862ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

---

### R04 — N/A (out of corpus)

**Question:** What does the Sprinkler Fitters collective agreement say about overtime pay?

**Answer:**

The provided documents do not contain information about a Sprinkler Fitters collective agreement or overtime pay provisions specific to Sprinkler Fitters.

The sources provided cover overtime pay terms for the following trades:
- Painters [SOURCE 1, SOURCE 2, SOURCE 7]
- Sheet Metal Workers [SOURCE 3]
- Roofers [SOURCE 8, SOURCE 9]
- Carpenters [SOURCE 6]
- Operating Engineers [SOURCE 10]

To answer your question about Sprinkler Fitters overtime pay, you would need to provide the relevant Sprinkler Fitters collective agreement or wage schedule documents.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3420ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / ☐ Partial | ☐ Yes / ☐ No | |

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
