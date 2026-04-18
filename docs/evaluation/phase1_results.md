# Phase 1 POC Evaluation Results

**Run date:** 2026-04-18 13:16 UTC  
**Questions:** 30  
**API errors:** 0  

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

The provided documents do not contain information about a single journeyperson hourly rate for IBEW Generation electricians effective May 1, 2025.

However, the documents show that wage rates vary by geographic location and Local Union. For example:

- **Local 530 (Sarnia)**: The wage schedule shows a journeyperson base rate of $53.35/hour effective May 1, 2025 [SOURCE 5, Wage Schedule E-3-C, page 1]

- **Local 586 (Ottawa)**: A wage schedule exists for this Local effective May 1, 2025, but the journeyperson hourly rate is not displayed in the provided excerpt [SOURCE 8, Wage Schedule E-13-C]

- **Local 402 (Thunder Bay)**: A wage schedule exists for this Local effective May 1, 2025, but the journeyperson hourly rate is not displayed in the provided excerpt [SOURCE 9, Wage Schedule E-16-C]

- **Local 105 (Hamilton)**: A wage schedule exists for this Local effective May 1, 2025, but the journeyperson hourly rate is not displayed in the provided excerpt [SOURCE 10, Wage Schedule E-6-C]

To obtain the complete journeyperson rates for all geographic areas, you would need access to the full wage schedule pages for each Local Union.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 5 | IBEW | IBEW Generation Wage Schedule E-3-C LU 530 Sarnia |  |  |
| 8 | IBEW | IBEW Generation Wage Schedule E-13-C LU 586 Ottawa |  |  |
| 9 | IBEW | IBEW Generation Wage Schedule E-16-C LU 402 Thunde |  |  |
| 10 | IBEW | IBEW Generation Wage Schedule E-6-C LU 105 Hamilto |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4675ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | x Yes / ☐ No |There must be issues reading the schedules, answer cited that journeymen wages are not listed but they are ![alt text](image.png)|

---

### W02 — IBEW

**Question:** What is the foreman wage premium for IBEW Generation electricians?

**Answer:**

Based on the provided documents, the foreman wage premium for IBEW Generation electricians is as follows:

**Foreperson:** The greater of 12% above the journeyperson base hourly rate OR the established percentage above the journeyperson rate differential as set out in the existing wage schedules. [SOURCE 10, Section 6, Subsection F]

**Subforeperson:** The greater of 6% above the journeyperson base hourly rate OR the established percentage differential above the journeyperson rate as set out in the existing wage schedules. [SOURCE 10, Section 6, Subsection F]

The agreement further notes that "The rates of pay for all forepeople and subforepeople covered by this Agreement will be set forth in the current wage schedules." [SOURCE 10, Section 6, Subsection F]

The provided documents do not contain the actual wage schedules showing the specific dollar amounts for these premiums. To determine the exact foreman wage premium in dollars per hour, you would need to consult the current wage schedules referenced in the agreement.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 10 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3173ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | ☐ Yes / x No | Should have went to the wage schedules, al wages are clearly laud out, that said, IBEW has 14 wage schedules on generation side alone, so answer should provide a couple results but then try to clarify specific schedule or ask for averages or something.

---

### W03 — IBEW

**Question:** What is the tool allowance for IBEW Generation electricians?

**Answer:**

Based on the provided documents, there is **no tool allowance specified** for IBEW Generation electricians.

The collective agreement includes a **tool list** that specifies which tools journeypeople electricians are required to have [SOURCE 1, Page 49], but it does not state a monetary allowance or reimbursement for those tools.

The tool list includes items such as:
- Centre punch, cold chisel, files, hammers, hacksaws
- Pliers (5 pairs in various types)
- Screwdrivers (6 total)
- Square, steel tape, tap wrench
- Tool box and tool pouch/belt

[SOURCE 1, Pages 49-50]

The agreement does address tool replacement procedures [SOURCE 3, Page 35], indicating that employees receiving tools from a tool crib are responsible for their return in good condition, and the employer must reimburse employees within 60 days if tools are lost or damaged. However, there is no stated hourly or lump-sum tool allowance.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4610ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | looks good|

---

### W04 — Sheet Metal

**Question:** What is the journeyperson hourly rate for Sheet Metal workers effective May 1, 2025?

**Answer:**

The provided documents do not contain the specific journeyperson hourly rate for Sheet Metal workers effective May 1, 2025.

While the sources include the 2025-2030 Sheet Metal Workers Collective Agreement and wage schedules effective May 1, 2025, the actual base hourly rate amounts are not shown in the excerpts provided. The documents reference shift differentials, overtime multiples, and deductions (such as union dues and training fund contributions) that apply to the base rate, but do not display the base hourly rate itself.

To find the journeyperson hourly rate, you would need to consult the complete wage schedule documents (such as SM-03, SM-05, SM-13, etc.) for the specific local union geographic area where work is being performed, as rates may vary by location.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3066ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | x Yes / ☐ No | Again all wages are in the wage schedule documents. In this case there are 16 of them. Results should have found examples from there and queried to get more specific results per region. |

---

### W05 — Sheet Metal

**Question:** What apprentice wage rates apply to Sheet Metal workers under the 2025-2030 collective agreement?

**Answer:**

The provided documents do not contain information about specific apprentice wage rates for Sheet Metal workers under the 2025-2030 collective agreement.

While the agreement references that wage schedules are "attached hereto" [SOURCE 6, Article 13.1], the actual wage schedule tables are not included in the source materials provided to me. The documents confirm that apprentice wage rates exist and are set out in those schedules [SOURCE 2, Section 12.4 and SOURCE 6, Article 13.1], but the specific dollar amounts or rate percentages are not present in the excerpts available.

To obtain the apprentice wage rates, you would need to consult the complete wage schedule appendix to the Sheet Metal Workers 2025-2030 Collective Agreement.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 12.4 |
| 6 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 13.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3378ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | x Yes / ☐ No | See above|

---

### W06 — Sheet Metal

**Question:** What is the general foreman wage rate for Sheet Metal workers?

**Answer:**

The provided documents do not contain information about a "general foreman" wage rate for Sheet Metal workers.

The documents reference foreperson and subforeperson classifications. According to [SOURCE 5, Section 20.5, Page 26], the rate of pay structure is:

- **Foreperson**: fifteen percent (15%) above the journeyperson rate
- **Subforeperson**: seven percent (7%) above the journeyperson rate

However, the actual dollar amounts for the journeyperson rate (which would be needed to calculate the foreperson rate) are not included in the sources provided. The documents indicate that [SOURCE 2, Section 13.1, Page 22] establishes that "rates of pay for employees in the classifications listed in Article 2 of this Agreement shall be as set forth in the wage schedules, attached hereto," but the wage schedules themselves are not provided in these sources.

If you are looking for the specific dollar wage rate, you would need access to the wage schedules that are referenced throughout the agreement.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 13.1 |
| 5 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 20.5 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3815ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | x Yes / ☐ No | General Foreman are usually not covered under these agreements so therefore the answer was correct, but I am not sure if it got it correct for the right reasons. |

---

### W07 — United Association

**Question:** What is the journeyperson hourly rate for United Association plumbers effective May 1, 2025?

**Answer:**

# United Association Journeyperson Plumber Hourly Rates — May 1, 2025

The journeyperson hourly rate for United Association plumbers effective May 1, 2025 **varies by local union and geographic area**. There is no single rate across Ontario. Here are the rates:

| Local | Geographic Area | Journeyperson Base Hourly Rate |
|-------|-----------------|--------------------------------|
| 628 | Thunder Bay | $48.98 |
| 71 | Ottawa | $49.87 |
| 800 | Sault Ste. Marie | $47.14 |
| 67 | Brantford/Hamilton | $50.14 |
| 67 | Niagara | $49.29 |
| 401 | Kingston | $50.33 |
| 46 | Barrie | $49.20 |
| 800 | Sudbury | $47.96 |
| 401 | Belleville | $50.29 |

**Source Citations:**

- Local 628 Thunder Bay: [SOURCE 1], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 71 Ottawa: [SOURCE 2], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 800 Sault Ste. Marie: [SOURCE 3], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 67 Brantford/Hamilton: [SOURCE 4], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 67 Niagara: [SOURCE 5], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 401 Kingston: [SOURCE 6], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 46 Barrie: [SOURCE 7], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 800 Sudbury: [SOURCE 8], Grade 13-6 Journeyman-450035, effective 2025-05-01
- Local 401 Belleville: [SOURCE 9], Grade 13-6 Journeyman-450035, effective 2025-05-01

These are **base hourly rates only** and do not include vacation, statutory holiday, welfare, pension, or union funds components, which are listed separately in the wage schedules.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association Wage Schedule Local 628 Thunder |  |  |
| 2 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 3 | United Association | United Association Wage Schedule Local 800 Sault S |  |  |
| 4 | United Association | United Association Wage Schedule Local 67 Brantfor |  |  |
| 5 | United Association | United Association Wage Schedule Local 67 Niagara |  |  |
| 6 | United Association | United Association Wage Schedule Local 401 Kingsto |  |  |
| 7 | United Association | United Association Wage Schedule Local 46 Barrie |  |  |
| 8 | United Association | United Association Wage Schedule Local 800 Sudbury |  |  |
| 9 | United Association | United Association Wage Schedule Local 401 Bellevi |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 6499ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | Pretty good job here |

---

### W08 — United Association

**Question:** What is the foreman premium percentage for United Association workers?

**Answer:**

# Foreman Premium for United Association Workers

The foreman premium for United Association workers is **15% above the journeyperson base hourly rate** [SOURCE 3, Section 9.5].

## Supporting Clause Text

Section 9.5 of the United Association 2025-2030 Collective Agreement states:

> "The forepeople's differential shall be 15% above the journeyperson base hourly rate. The increase in forepeople rate shall not apply to Greenpeople rates. The subforepeople's differential shall be 7.5% above the journeyperson base hourly rate." [SOURCE 3, Section 9.5, Page 15]

This 15% differential is consistently reflected across all wage schedules provided, including schedules for Local 46 Barrie [SOURCE 4], Local 401 Kingston [SOURCE 5], Local 67 Niagara [SOURCE 7], Local 71 Ottawa [SOURCE 8], Local 628 Thunder Bay [SOURCE 9], and Local 401 Belleville [SOURCE 10].

Additionally, for subforemen, a differential of 7.5% above the journeyperson base hourly rate applies [SOURCE 3, Section 9.5].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 3 | United Association | United Association 2025-2030 Collective Agreement |  | 9.5 |
| 4 | United Association | United Association Wage Schedule Local 46 Barrie |  |  |
| 5 | United Association | United Association Wage Schedule Local 401 Kingsto |  |  |
| 7 | United Association | United Association Wage Schedule Local 67 Niagara |  |  |
| 8 | United Association | United Association Wage Schedule Local 71 Ottawa |  |  |
| 9 | United Association | United Association Wage Schedule Local 628 Thunder |  |  |
| 10 | United Association | United Association Wage Schedule Local 401 Bellevi |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4629ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

## Overtime & Hours

### O01 — IBEW

**Question:** What constitutes overtime for IBEW Generation electricians under the 2025-2030 agreement?

**Answer:**

# Overtime Definition for IBEW Generation Electricians (2025-2030)

The IBEW Generation agreement does not provide an explicit general definition of what "constitutes" overtime. Instead, it specifies **when overtime rates apply** based on hours worked, which effectively defines overtime by its triggers.

## Overtime Triggers Under Standard Schedule

For employees working on an **eight (8) hour day and five (5) day per week work schedule (Monday to Friday)**:

> "overtime work shall be paid at one and one-half (1 ½) times the basic hourly rate for all hours worked beyond the normal daily scheduled number of hours up to a maximum of two (2) hours per day. All hours in excess of 10 hours per day shall be paid at two (2) times the base hourly rate." [SOURCE 6, Section 806 A]

This means:
- **Hours 9-10 per day** = 1.5× rate (overtime)
- **Hours 11+ per day** = 2× rate (double time)

## Three-Shift Operations

Under three-shift operations, the agreement establishes different daily hour thresholds by shift type [SOURCE 8, Section 800 B]. However, the provided documents do not contain Section 806 language specific to three-shift operations, so the overtime triggers for those shifts are not provided in these sources.

## Voluntary Distribution

Importantly, the agreement states: "All overtime shall be worked on a voluntary basis and shall be distributed as equally as possible among all IBEW members." [SOURCE 1, Page 24]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 6 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5587ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O02 — IBEW

**Question:** What is the overtime rate for IBEW Generation workers on a Saturday?

**Answer:**

# Overtime Rate for IBEW Generation Workers on Saturday

**The overtime rate for IBEW Generation workers performing overtime work on a Saturday is two (2) times the basic hourly rate.**

## Supporting Clause

Section 806 A states:

> "Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate." [SOURCE 2, Page 24]

This provision applies regardless of the work schedule type (whether the employee is on an eight-hour five-day schedule or a ten-hour four-day schedule). The rate applies to all overtime hours worked on Saturday, not just hours beyond a certain threshold.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3176ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O03 — IBEW

**Question:** What is the maximum number of regular daily hours for IBEW Generation workers?

**Answer:**

# Maximum Regular Daily Hours for IBEW Generation Workers

The maximum regular daily hours depend on the shift operation established by the employer:

**For One (1) or Two (2) Shift Operations:**
The agreement establishes a **40-hour weekly schedule** (Monday to Friday inclusive), but does not specify a maximum daily hour limit in the primary hours clause. [SOURCE 1, Article 800 A]

However, the daily hour structure is clarified through the overtime provisions:
- For an **8-hour day schedule**: The normal daily scheduled hours are 8 hours. Overtime is paid for hours beyond 8 hours per day, with a maximum of 2 hours at time-and-a-half, and all hours in excess of 10 hours per day at double time. [SOURCE 2, Article 806 A]

- For a **10-hour day schedule** (4 days per week): The normal daily scheduled hours are 10 hours. Overtime is paid for hours beyond 10 hours per day, with a maximum of 2 hours at time-and-a-half, and all hours in excess of 12 hours per day at double time. [SOURCE 7, Article 806]

**For Three (3) Shift Operations:**
- Day shift: **8 hours** [SOURCE 6, Article 800 B]
- Afternoon shift: **7.5 hours** [SOURCE 6, Article 800 B]
- Night shift: **7 hours** [SOURCE 6, Article 800 B]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 6 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 7 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4348ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O04 — Sheet Metal

**Question:** What are the regular daily hours of work for Sheet Metal workers?

**Answer:**

# Regular Daily Hours of Work for Sheet Metal Workers

The regular daily hours of work for Sheet Metal workers depend on the operational structure:

## Standard Operations (One or Two Shift):

For employers operating on a one or two shift basis, employees work **40 hours per week** (Monday to Friday) with daily hours established as either:
- **Four (4) consecutive ten-hour shifts**, or  
- **Five (5) consecutive eight-hour shifts**

Daily hours must be established for a minimum of 30 days, with at least five days' written notice required before any changes. [SOURCE 1, Section 22.1, Page 27]

## Remote/Northern Operations:

For work north of the French River in remote locations, employers may establish a schedule of **fourteen (14) consecutive days** of work followed by seven (7) consecutive days off. [SOURCE 5, Section 22.6, Page 28]

## Project-Specific Schedules:

For certain projects (Appendix B - 7 Day Coverage), employees may work **four consecutive shifts** (day, afternoon, or night) followed by four scheduled days off, with regularly scheduled hours of **ten (10) hours per day** Monday to Friday. [SOURCE 2, Section 48.1, Page 51]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.1 |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 48.1 |
| 5 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.6 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5511ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O05 — Sheet Metal

**Question:** What is the overtime rate for Sheet Metal workers on a Sunday?

**Answer:**

# Overtime Rate for Sheet Metal Workers on Sunday

The overtime rate for Sheet Metal workers on a Sunday is **2 times (double time) the basic hourly rate for all hours worked**.

## Supporting Documentation

This rate is consistently specified across multiple sources:

**Primary Collective Agreement:**
"Overtime work performed on Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at two (2) times the basic hourly rate." [SOURCE 2, Section 23.1, Page 28]

**Wage Schedules (all localities):**
Multiple wage schedules confirm the same rate with identical language:
- "Sat., Sun. & Holidays - 2 times for all hours worked." [SOURCE 1, Sheet Metal Wage Schedule SM-13 LU 47 Ottawa, Page 1]
- [SOURCE 3, Sheet Metal Wage Schedule SM-16 LU 397 Thunder Bay, Page 1]
- [SOURCE 5, Sheet Metal Wage Schedule SM-14 LU 504 Sudbury, Page 1]
- [SOURCE 7, Sheet Metal Wage Schedule SM-11 LU 30 Peterborough, Page 2]
- [SOURCE 8, Sheet Metal Wage Schedule SM-01 LU 235 Windsor, Page 2]
- [SOURCE 9, Sheet Metal Wage Schedule SM-05 LU 562 Kitchener, Page 2]
- [SOURCE 10, Sheet Metal Wage Schedule SM-03 LU 235 Sarnia, Page 2]

This rate applies regardless of whether Sunday work is overtime or regularly scheduled work. [SOURCE 4, Section 2.0, Page 58]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Wage Schedule SM-13 LU 47 Ottawa |  |  |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 23.1 |
| 3 | Sheet Metal | Sheet Metal Wage Schedule SM-16 LU 397 Thunder Bay |  |  |
| 4 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 2.0 |
| 5 | Sheet Metal | Sheet Metal Wage Schedule SM-14 LU 504 Sudbury |  |  |
| 7 | Sheet Metal | Sheet Metal Wage Schedule SM-11 LU 30 Peterborough |  |  |
| 8 | Sheet Metal | Sheet Metal Wage Schedule SM-01 LU 235 Windsor |  |  |
| 9 | Sheet Metal | Sheet Metal Wage Schedule SM-05 LU 562 Kitchener |  |  |
| 10 | Sheet Metal | Sheet Metal Wage Schedule SM-03 LU 235 Sarnia |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5442ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O06 — Sheet Metal

**Question:** What are the daily overtime rules for Sheet Metal workers under the 2025-2030 agreement?

**Answer:**

# Daily Overtime Rules for Sheet Metal Workers (2025-2030)

The 2025-2030 Sheet Metal Workers Collective Agreement establishes the following daily overtime rules:

## For 8-Hour Day / 5-Day Week Schedule

For hours worked beyond the normal daily scheduled number of hours:
- **Up to 2 hours per day**: 1½ times the basic hourly rate
- **All hours in excess of 10 hours per day**: 2 times the basic hourly rate

[SOURCE 10, Section 23.1, Page 28]

## For 10-Hour Day / 4-Day Week Schedule

For hours worked beyond the normal daily scheduled number of hours:
- **Up to 2 hours per day**: 1½ times the basic hourly rate
- **All hours in excess of 12 hours per day**: 2 times the basic hourly rate

[SOURCE 10, Section 23.1, Page 28]

## Weekend and Holiday Work

Overtime work performed on Saturday, Sunday, Recognized Holidays, and non-shift days shall be paid at **2 times the basic hourly rate** regardless of the schedule type.

[SOURCE 10, Section 23.1, Page 28]

**Note:** These rules apply to Monday–Friday scheduled work. Shift differentials are not paid on overtime hours. [SOURCE 2, Section 22.1, Page 27]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 22.1 |
| 10 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 23.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3421ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O07 — United Association

**Question:** What is the double-time rate provision for United Association workers?

**Answer:**

# Double-Time Rate Provision for United Association Workers

Based on the provided collective agreement, United Association workers receive double-time (two times the base hourly rate) under the following circumstances:

## Regular Hours on Weekends and Holidays

Regularly scheduled hours of work on **Saturday, Sunday, Statutory and Recognized Holidays** are paid at two times the straight time hourly rate. [SOURCE 1, Section 9.1, Page 51]

For the 10-hour shift schedule, the same provision applies: regularly scheduled hours on Saturday and Sunday, and Statutory and Recognized Holidays, are paid at two times the straight time hourly rate. [SOURCE 6, Section 48.1, Page 44]

## Overtime Hours

Double-time rates also apply to **overtime work**:

- When working an 8-hour day/5-day week schedule: all hours in excess of 10 hours per day are paid at two times the base hourly rate. [SOURCE 10, Section 24.1, Page 25]

- When working a 10-hour day/4-day week schedule: all hours in excess of 12 hours per day are paid at two times the base hourly rate. [SOURCE 10, Section 24.1, Page 25]

- Overtime work performed on Saturday, Sunday, Recognized Holidays, and non-shift days is paid at two times the basic hourly rate. [SOURCE 10, Section 24.1, Page 25]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association 2025-2030 Collective Agreement |  | 9.1 |
| 6 | United Association | United Association 2025-2030 Collective Agreement |  | 48.1 |
| 10 | United Association | United Association 2025-2030 Collective Agreement |  | 24.1 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4055ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### O08 — United Association

**Question:** What time does a regular shift start for United Association workers under the 2025-2030 agreement?

**Answer:**

# Start Time for Regular Shifts

The start time for the day shift under the United Association 2025-2030 agreement depends on the work location:

**For nuclear locations:** The day shift start time shall be between **6:00 AM and 9:00 AM** [SOURCE 1, Section 23.2]

**For all other locations:** The day shift start time shall be **8:00 AM with a possible one (1) hour variance either way** (meaning between 7:00 AM and 9:00 AM) [SOURCE 1, Section 23.2]

The agreement also notes that "Crews may have staggered start times" and that "The afternoon shift shall be immediately following the day shift or within two (2) hours either way at the end of the day shift." [SOURCE 1, Section 23.2]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | United Association | United Association 2025-2030 Collective Agreement |  | 23.2 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3376ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

## Travel & Board

### T01 — IBEW

**Question:** What is the board allowance for IBEW Generation workers working away from home?

**Answer:**

# Board Allowance for IBEW Generation Workers Working Away from Home

The provided documents do not contain a specific monetary "board allowance" stated as a single fixed amount.

Instead, the IBEW Generation collective agreement provides **room and board provisions with multiple options**, depending on the worker's circumstances:

## Primary Provision

When an employee's regular residence is greater than or equal to 110 road-driven kilometers from a project and the employee maintains temporary accommodation at or near the project, the employer may supply either:

- Free room and board in camp or good standard board and lodging within reasonable distance; **or**
- A subsistence allowance; **or**  
- A travel allowance [SOURCE 8, Article 1101 A(i)]

## If Employee Exercises Option Not to Stay in Camp

If an employee chooses not to stay in camp or accept free room and board, they receive a **subsistence allowance** (the amount varies by project location—North or South of the French River, or specific projects like Pickering, Darlington, and Bruce Power) [SOURCE 8, Article 1101 A(ii); SOURCE 2, Article 1101(b)-(e)].

## Travel Allowance Within Locals 402 and 1687

If receiving room and board allowance, employees receive **travel time compensation** based on distance from nearest available accommodation:
- 40–56 road km: ½ hour regular time pay
- 57–80 road km: 1 hour regular time pay
- 81–120 road km: 1½ hours regular time pay
- 121–160 road km: 2 hours regular time pay
- Over 160 road km: actual travel time at regular time rate [SOURCE 1, Article 1100, Section D]

The specific subsistence allowance rates are referenced but not fully detailed in the provided source pages.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7577ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### T02 — IBEW

**Question:** How far from home must an IBEW Generation worker be to qualify for board allowance?

**Answer:**

# Board Allowance Distance Threshold for IBEW Generation Workers

An IBEW Generation worker must be **greater than or equal to 110 road-driven kilometers** from their regular residence to the project to qualify for room and board allowance.

## Supporting Clause

Article 1101 A states:

> "The following conditions will apply for employees whose Room and Board regular residence* is greater than or equal to 110 road-driven kilometers from the project: (i) An Employer may supply either: (a) free room and board in camp or a good standard of board and lodging within a reasonable distance of a project; or (b) a subsistence allowance; or (c) a travel allowance." [SOURCE 4, Article 1101 A]

This threshold applies across multiple project locations (North of French River, South of French River, Pickering, Darlington, and Bruce Power Projects), though the specific allowance amounts and conditions may vary by location. [SOURCE 2, SOURCE 3, SOURCE 4]

For employees living less than 110 kilometers from the project, the daily travel allowance provisions under Article 1100 A apply instead. [SOURCE 6, Article 1100 A(i)–(iv)]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 4 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 6 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5018ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### T03 — Sheet Metal

**Question:** What is the subsistence allowance for Sheet Metal workers working away from home?

**Answer:**

# Subsistence Allowance for Sheet Metal Workers Working Away from Home

The provided documents establish that Sheet Metal workers qualify for subsistence allowance if their regular residence is **greater than or equal to 110 road-driven kilometers** from the project work location, but the documents do not specify the actual dollar amounts of the subsistence allowance rates themselves. The rate tables are referenced but not fully detailed in the provided excerpts.

## Eligibility and Structure

**Northern Region:** An employee working in the Northern Region (geographic area north of a line drawn between the mouth of the French River and Mattawa) whose regular residence is ≥110 road-driven kilometers from the Project shall be paid a subsistence allowance [SOURCE 2, page 37, Article 32.1(b)(ii)].

**Southern Region:** An employee working in the Southern Region whose regular residence is ≥110 road-driven kilometers from the Project in the Southern Region shall be paid a subsistence allowance [SOURCE 2, page 37, Article 32.1(b)(iii)].

**Employee Choice:** An employee may exercise their option not to stay in camp or accept free room and board, and if they choose not to, they receive subsistence allowance instead [SOURCE 2, page 37, Article 32.1(b)].

The documents reference that "the rates as set out below" apply to each day worked or reported for, but the actual rate tables showing the specific dollar amounts are not included in the provided source excerpts.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5221ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### T04 — Sheet Metal

**Question:** What are the travel zone provisions for Sheet Metal workers?

**Answer:**

# Travel Zone Provisions for Sheet Metal Workers

Sheet Metal workers are covered by **two different travel zone systems** depending on the project context:

## Standard Projects (Article 26)

For standard projects, travel zones are based on road-driven distance from the employee's residence to the project [SOURCE 2, Section 26.1]:

- **Less than 50 km**: No travel allowance [SOURCE 2, 26.1(a)]
- **50–70 km**: Travel allowance applies [SOURCE 2, 26.1(b)]
- **70–96 km**: Travel allowance applies [SOURCE 2, 26.1(c)]
- **96–110 km**: Travel allowance applies [SOURCE 2, 26.1(d)]
- **110 km or greater**: $60.00 per day (effective May 1, 2025) if employee does not qualify for subsistence allowance or does not maintain temporary accommodation [SOURCE 2, 26.1(e); SOURCE 4]

**Specific daily travel rates by zone** (2025–2029) [SOURCE 4]:
- Zone 26.1(b): $33.14–$36.58 per day
- Zone 26.1(c): $38.50–$42.50 per day
- Zone 26.1(d): $42.00–$46.36 per day
- Zone 26.1(e): $60.00 per day

## OPG Generation Construction Projects (Article 27)

For OPG Generation Construction Projects, travel zones apply from the **work location or declared assembly point** [SOURCE 1, Section 27.1; SOURCE 3, Section 27.2]:

- **Less than 50 km**: No travel allowance [SOURCE 1, 27.1(a)]
- **50–70 km**: Travel allowance applies [SOURCE 1, 27.1(b)]
- **70–96 km**: Travel allowance applies [SOURCE 1, 27.1(c)]
- **96–110 km**: Travel allowance applies [SOURCE 1, 27.1(d)]
- **110 km or greater**: Travel allowance applies if employee does not live in camp, receive subsistence, or maintain temporary accommodation [SOURCE 1, 27.1(e)]

**Daily travel rates by zone** (2025–2029) [SOURCE 3]:
- Zone 27.1(b): $32.56–$35.94 per day
- Zone 27.1(c): $37.14–$41.00 per day
- Zone 27.1(d): $42.00–$46.36 per day
- Zone 27.1(e): $60.00 per day

## Key Definitions and Rules

**"Road-driven kilometers"** is measured as the shortest available road-driven distance from the employee's residence to the project (or work location/assembly point for OPG projects), as determined through Google Maps [SOURCE 2, 26.1; SOURCE 3, 27.3].

**Employees using company vehicles** are not entitled to daily travel allowance [SOURCE 2, 26.1(f); SOURCE 1, 27.1(f)].

**No travel allowance** is paid if an employee reports for work but does not remain for their scheduled daily hours, unless excused by an authorized employer representative [SOURCE 2, 26.3; SOURCE 1, 27.5].

## Room and Board Alternative (110 km+)

For employees whose regular residence is 110 km or greater from the project, the employer may provide either free room and board or a subsistence allowance as an alternative to daily travel allowance [SOURCE 4, Section 26.2].

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 27.1 |
| 2 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  | 26.1 |
| 3 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |
| 4 | Sheet Metal | Sheet Metal Workers 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 7749ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### T05 — United Association

**Question:** How is travel time compensated for United Association plumbers under the 2025-2030 agreement?

**Answer:**

# Travel Time Compensation for United Association Plumbers (2025-2030)

Travel time compensation under the United Association 2025-2030 Collective Agreement varies depending on the context and distance involved. There is no single travel time compensation rule; instead, the agreement specifies different provisions for different scenarios:

## Remote Projects (OPG Construction)

For Ontario Power Generation construction projects within the jurisdiction of Locals 800 and 628, where an employee receives Room and Board allowance on remote projects more than 40 road kilometers from accommodation, travel time is compensated as follows [SOURCE 1, Section 28.6]:

- **40–56 road km:** ½ hour regular time pay
- **57–80 road km:** 1 hour regular time pay
- **81–120 road km:** 1½ hours regular time pay
- **121–160 road km:** 2 hours regular time pay
- **Over 160 road km:** Actual travel time paid at regular time rate

However, if the employer provides a vehicle or transportation, these travel time provisions do not apply [SOURCE 1, Section 28.6].

## Recruitment/Transfer of Employees

For employees being transferred between projects, the employer shall pay travelling time at straight-time rates up to a maximum of 8 hours' pay, calculated at one hour's pay for each 96 road-driven kilometers of travel [SOURCE 3, Section 30.6; SOURCE 5, Section 31.6].

For recruitment of Ontario residents beyond 189 road kilometers from a project, travel time is based on one hour's pay for each 96 road-driven kilometers, to a maximum of 8 hours' pay [SOURCE 8, Section 30.2; SOURCE 9, Section 31.2].

For recruitment of non-Ontario residents beyond 189 road kilometers, the same travel time formula applies: one hour's pay per 96 road-driven kilometers, maximum 8 hours' pay [SOURCE 4, Section 30.3; SOURCE 7, Section 31.3].

## Apprentices

Apprentices who do not qualify for Room and Board but live more than 110 road kilometers from the project receive daily travel rates as per Article 28.1(e) [SOURCE 10, Letter of Understanding #8].

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
**Latency:** 5728ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

## Nuclear Project Specific

### N01 — IBEW

**Question:** Are there different overtime rules for IBEW Generation workers at a nuclear project site?

**Answer:**

# Overtime Rules for IBEW Generation Workers at Nuclear Project Sites

Yes, there are different overtime rules depending on the work schedule. IBEW Generation workers at nuclear project sites are subject to different overtime pay scales based on whether they work an 8-hour/5-day schedule or a 10-hour/4-day schedule.

## 8-Hour / 5-Day Schedule

When working on an eight (8) hour day and five (5) day per week work schedule (Monday to Friday inclusive):
- Overtime work shall be paid at **1½ times the basic hourly rate** for all hours worked beyond the normal daily scheduled number of hours up to a maximum of 2 hours per day
- All hours in excess of 10 hours per day shall be paid at **2 times the base hourly rate**

[SOURCE 5, Section 806 A]

## 10-Hour / 4-Day Schedule

When working on a ten (10) hour day and four (4) day per week work schedule (Monday to Friday inclusive):
- Overtime work shall be paid at **1½ times the basic hourly rate** for all hours worked beyond the normal daily scheduled number of hours up to a maximum of 2 hours per day
- All hours in excess of 12 hours per day shall be paid at **2 times the base hourly rate**

[SOURCE 1, Section 806 A]

## Common Rules for Both Schedules

Regardless of which schedule applies:
- Overtime work performed on **Saturday, Sunday, Recognized Holidays and non-shift days shall be paid at 2 times the basic hourly rate**
- **All overtime shall be worked on a voluntary basis** and shall be distributed as equally as possible among all IBEW members
- Unapproved absences may disentitle an employee to overtime opportunities at the Employer's discretion, subject to referral to the Nuclear Project Committee

[SOURCE 1, Section 806 A and C]

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5368ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### N02 — IBEW

**Question:** What additional provisions apply to IBEW Generation electricians working at Darlington?

**Answer:**

The provided documents do not contain information about additional provisions that apply specifically to IBEW Generation electricians working at Darlington.

While the sources reference "Ontario Power Generation Inc. (OPGI) and Bruce Power LP facilities" generally [SOURCE 2, Section 200 A (iii)], they do not identify Darlington as a specific location or describe any unique provisions that would apply there.

To obtain information about Darlington-specific provisions, you would need to consult:
- Any supplementary agreements or letters of understanding specific to the Darlington facility
- Project-specific addenda to the primary collective agreement
- Qualified labour relations counsel familiar with EPSCA agreements

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3274ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | x Yes / ☐ No | |

---

### N03 — Sheet Metal

**Question:** What special conditions apply to Sheet Metal workers under the Nuclear Project Agreement?

**Answer:**

# Special Conditions for Sheet Metal Workers Under the Nuclear Project Agreement

Sheet Metal workers under the Nuclear Project Agreement are subject to several special conditions that differ from standard EPSCA collective agreements:

## Scope of Application
The Nuclear Project Agreement applies only to work on existing Ontario Power Generation Inc. nuclear sites (Pickering, Darlington, Bruce) and Bruce Power LP property, and supersedes the standard EPSCA collective agreements for that work [SOURCE 1, Section 1.1].

## Key Special Conditions:

**1. Nuclear Qualified Worker (NQW) Requirements**
Workers must obtain Nuclear Qualified Worker status. During the first two years of the agreement, priority is given to NQWs but non-NQW qualified journeymen/apprentices may be referred. After two years, only NQWs will be referred [SOURCE 10, Section 5.1].

**2. Worker Protection Against Displacement**
Once hired onto a nuclear site, travelers and permit workers cannot be displaced or bumped by other members. Unresolved disputes go to the Project Committee [SOURCE 2, Section 6.1].

**3. Transfer Restrictions**
Transfers between employers, between sites, or between sectors are permitted only under specific conditions:
- Between employers: limited to short-term assignments (14 days), emergent work with specific skills, or radiological dose management [SOURCE 6, Section 5.2(A)]
- Between sites: only if employees are already NQWs and the local union has no NQWs available [SOURCE 6, Section 5.2(B)]
- Between sectors: only if employees are already NQWs [SOURCE 6, Section 5.2(C)]

**4. Composite Crew Restrictions**
Composite crews (crews with mixed trades) must follow the "One Person, One Job" principle and cannot be used to assign workers outside their skill classification under regular operating conditions [SOURCE 4, Section 11.1].

**5. Standoff Provisions**
Employers may elect to standoff (not layoff) employees for up to 10 consecutive working days without pay, with no travel allowance and subsistence allowance only if temporary residence is maintained [SOURCE 8, Section 10.1(b)].

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
**Latency:** 10649ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### N04 — United Association

**Question:** Do United Association workers receive any premium for working on a nuclear project site?

**Answer:**

# Nuclear Project Premium for United Association Workers

Yes, United Association workers receive a premium for working on nuclear project sites, but only under specific radiation protection conditions.

## Radiation Protection Premium

Employees working in radiation areas while wearing fully enveloping plastic suits or replacement material with an independent air supply receive **$20.00 per day effective May 1, 2025** [SOURCE 2, Section 41.1(e), Page 42].

## Radiation Protection Assistant (R.P.A.) Premium

Additionally, Construction Radiation Protection Assistants (R.P.A.s) who have completed the required radiation qualification training receive premium wages when performing R.P.A. functions. The agreement states that "R.P.A. will be paid as set out in the wage schedules attached hereto when performing an R.P.A. function" [SOURCE 6, Section 8.8, Page 14]. However, the provided documents do not include the actual wage schedule amounts for R.P.A. positions.

## Scope Note

These premiums apply specifically to radiation work at nuclear facilities operated by Ontario Power Generation Inc. and Bruce Power LP [SOURCE 2, Section 41.1, Page 42]. The provided documents do not contain information about whether United Association workers receive additional premiums for non-radiation work on nuclear project sites.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | United Association | United Association 2025-2030 Collective Agreement |  | 41.1 |
| 6 | United Association | United Association 2025-2030 Collective Agreement |  | 8.8 |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 4850ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

### N05 — IBEW

**Question:** What are the travel provisions for IBEW Generation workers under the Nuclear Project Agreement?

**Answer:**

# Travel Provisions for IBEW Generation Workers Under the Nuclear Project Agreement

The provided documents do not contain comprehensive travel provisions specifically under the IBEW Nuclear Project Agreement. 

The only provision in the Nuclear Project Agreement itself addresses worker displacement, not travel: [SOURCE 2, Section 6.1] states that "Once a worker is hired onto a site covered by this agreement, travelers and/or permit workers shall not be displaced and/or bumped by any other member."

For detailed travel provisions applicable to IBEW Generation workers (including those on nuclear sites), the documents reference the IBEW Generation 2025-2030 Collective Agreement, which includes:

- **Daily Travel Allowance** [SOURCE 8, Article 1100 A] based on distance from the project (ranging from no allowance if living less than 50 km away, to $49.37–$54.50 per day effective May 1, 2025–2029 for employees living 110+ road-driven kilometers away)

- **Room and Board/Subsistence Allowance** [SOURCE 9, Article 1101 A] for employees whose regular residence is 110+ road-driven kilometers from the project

- **Initial and Return Travel Expenses** [SOURCE 3, Article 1102] covering recruitment travel for employees living 110+ road-driven kilometers away, with varying rates based on distance and location

The documents note that on nuclear sites specifically, certain hiring and replacement rules apply [SOURCE 10, Section 701A(iv)], but detailed travel-specific provisions unique to nuclear projects are not separately elaborated in the Nuclear Project Agreement excerpt provided.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 2 | IBEW | IBEW Nuclear Project Agreement |  | 6.1 |
| 3 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 9 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 10 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 5779ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | |

---

## Cross-Union Comparison

### C01 — IBEW / Sheet Metal

**Question:** Compare the overtime rules for IBEW Generation and Sheet Metal workers under their 2025-2030 agreements.

**Answer:**

# Overtime Rules Comparison: IBEW Generation vs. Sheet Metal Workers (2025–2030)

---

## ⚠️ Important Preliminary Note

The provided source documents **only contain provisions from the IBEW Generation 2025–2030 Collective Agreement**. **No Sheet Metal Workers' 2025–2030 collective agreement has been provided** in the source documents for this conversation.

Therefore, a full side-by-side comparison cannot be completed at this time.

---

## IBEW Generation — Overtime Rules

### Standard 8-Hour / 5-Day Schedule (Monday–Friday)

> **Section 806 A** [SOURCE 8]:
> "When working on an eight (8) hour day and five (5) day per week work schedule (Monday to Friday inclusive), overtime work shall be paid at **one and one-half (1½) times** the basic hourly rate for all hours worked beyond the normal daily scheduled number of hours up to a maximum of two (2) hours per day. All hours in excess of **10 hours per day** shall be paid at **two (2) times** the base hourly rate."

---

### 10-Hour / 4-Day Schedule (Monday–Friday)

> **Section 806 A (continued)** [SOURCE 5, SOURCE 7]:
> "When working on a ten (10) hour day and four (4) day per week work schedule (Monday to Friday inclusive), overtime work shall be paid at **one and one-half (1½) times** the basic hourly rate for all hours worked beyond the normal daily scheduled number of hours up to a maximum of two (2) hours per day. All hours in excess of **12 hours per day** shall be paid at **two (2) times** the base hourly rate."

---

### Saturday, Sunday, Recognized Holidays & Non-Shift Days

> **Section 806 A** [SOURCE 5, SOURCE 7]:
> "Overtime work performed on **Saturday, Sunday, Recognized Holidays and non-shift days** shall be paid at **two (2) times** the basic hourly rate."

> **Note:** This double-time premium is **not applicable to the first eight (8) hours worked on Saturdays, Sundays and Recognized Holidays** [SOURCE 5, SOURCE 7].

---

### Voluntary Nature & Distribution of Overtime

> **Section 806 C** [SOURCE 1, SOURCE 5]:
> "All overtime shall be worked on a **voluntary basis** and shall be **distributed as equally as possible** among all IBEW members."

---

### Absenteeism and Overtime Entitlement

> **Section 806 A** [SOURCE 5, SOURCE 7]:
> "At the Employer's discretion, an unapproved absence of the Employee **may disentitle** the Employee to overtime opportunities. The application of the employer's discretion will be subject to referral to the Nuclear Project Committee."

---

### Overtime Meal Breaks

> **Section 806 B** [SOURCE 5, SOURCE 7]:
> - If **not notified the previous day** of extended overtime beyond two (2) hours: employer must provide a lunch and 30 paid minutes after approximately two hours of overtime; then again after each additional four (4) hours. If a hot meal cannot be supplied, the employer pays **$25.00**.
> - If **notified the previous day**: no meal provided, but employee receives 30 paid minutes to eat.
> - A paid meal period **supplants** any overlapping rest period.

---

### Rest Periods During Overtime

> **Section 801 B & C** [SOURCE 2]:
> - A **ten (10) minute rest period** prior to the end of the normal shift before commencing overtime.
> - A **fifteen (15) minute rest period** after each **two (2) hours of overtime worked**.

---

### Shift-Specific Overtime Clarification (Letter of Understanding)

> **LOU re: Shift Schedules** [SOURCE 4]:
> "This is to clarify that overtime will be paid in accordance with **Section 806 – Overtime**."

---

## Sheet Metal Workers — Overtime Rules

**The provided documents do not contain information about the Sheet Metal Workers' 2025–2030 Collective Agreement.**

No provisions regarding overtime rates, voluntary overtime, distribution rules, meal breaks during overtime, or rest periods during overtime are available for Sheet Metal Workers in the supplied sources. A comparison on these points cannot be made.

---

## Summary

| Provision | IBEW Generation | Sheet Metal Workers |
|---|---|---|
| OT rate (beyond daily hours, up to 2 hrs) | 1.5× [SOURCE 8] | *Not available* |
| OT rate beyond 10 hrs/day (8-hr schedule) | 2× [SOURCE 8] | *Not available* |
| OT rate beyond 12 hrs/day (10-hr schedule) | 2× [SOURCE 5] | *Not available* |
| Saturday/Sunday/Holiday OT rate | 2× [SOURCE 5] | *Not available* |
| Voluntary basis | Yes [SOURCE 1] | *Not available* |
| Equal distribution required | Yes [SOURCE 1] | *Not available* |
| Overtime rest periods | 10 min pre-OT; 15 min per 2 hrs OT [SOURCE 2] | *Not available* |

---

To complete this comparison, the Sheet Metal Workers' 2025–2030 Collective Agreement would need to be provided as a source document.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 2 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 4 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 5 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |
| 8 | IBEW | IBEW Generation 2025-2030 Collective Agreement |  |  |

**Model used:** `claude-sonnet-4-6`  
**Latency:** 24490ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | x Yes / ☐ No | Not sure why it was unable to locate the Sheet Metal CA, it was part of the ingestion. |

---

### C02 — IBEW / United Association

**Question:** Which union has the higher journeyperson base rate as of May 2025: IBEW Generation or United Association?

**Answer:**

I cannot answer this question based on the provided documents.

The sources contain wage schedules for **IBEW Generation** workers as of May 2025 [SOURCE 1, SOURCE 7]. For example, the IBEW Generation journeyperson base rate effective May 1, 2025, is $54.98/hour for Local 530 [SOURCE 7, E-3-C LU 530 Sarnia, 07-6 JOURNEYMAN, 2025-05-01 line].

However, **the provided documents do not contain any information about United Association wages or collective agreements**. Without United Association wage data, I cannot compare the two unions' journeyperson base rates.

To answer your question, you would need to provide United Association collective agreement or wage schedule documents covering the same time period (May 2025).

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

| # | Union | Document | Article | Section |
|---|-------|----------|---------|---------|
| 1 | IBEW | IBEW Generation Wage Schedule E-3-C LU 530 Sarnia |  |  |
| 7 | IBEW | IBEW Generation Wage Schedule E-3-C LU 530 Sarnia |  |  |

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 3994ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / x No / ☐ Partial | x Yes / ☐ No | All wages to the 3 test unions have been ingested. |

---

## Refusal

### R01 — N/A (out of corpus)

**Question:** What are the pension benefits for retired Boilermakers under EPSCA agreements?

**Answer:**

The provided documents do not contain information about pension benefits for retired Boilermakers under EPSCA agreements.

The sources provided cover collective agreements for the United Association (plumbers and pipe fitters), Sheet Metal Workers, and IBEW (electricians) unions. There is no Boilermakers union agreement or specific information about retired Boilermakers' pension benefits included in these documents.

To obtain information about Boilermakers pension benefits under EPSCA agreements, you would need to consult the relevant Boilermakers collective agreement or contact EPSCA directly.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2859ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| x Yes / ☐ No / ☐ Partial | x Yes / ☐ No | This is good, we haven't ingested anything for the boilermakers yet, so it should not have made anything up, good that it did not halucinate. |

---

### R02 — N/A (out of corpus)

**Question:** What is the grievance arbitration process for IBEW Transmission workers at Bruce Power?

**Answer:**

I don't have the provided sources needed to answer your question. You've asked about the grievance arbitration process for IBEW Transmission workers at Bruce Power, but no collective agreement documents have been included in this conversation yet.

To provide you with an accurate, cited answer about the grievance arbitration process, I would need access to:

- The relevant IBEW collective agreement covering Bruce Power workers, or
- A Bruce Power-specific project agreement, or
- EPSCA collective agreement documentation that addresses this dispute resolution procedure

Please provide the relevant source documents, and I'll be able to cite the specific articles and sections governing the grievance arbitration process.

⚠️ This answer is for reference only and does not constitute legal advice.

**Citations:**

_No citations returned._

**Model used:** `claude-haiku-4-5-20251001`  
**Latency:** 2695ms  
**Query log ID:** `N/A`

**Manual review:**

| Correct? | Citations valid? | Notes |
|----------|-----------------|-------|
| ☐ Yes / ☐ No / x Partial | ☐ Yes / x No | not sure about this one|

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
| R01 | Refusal | N/A (out of corpus) | | | |
| R02 | Refusal | N/A (out of corpus) | | | |
