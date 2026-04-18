# Chunk Length Test Report

## Overview

- Files tested: 45
- Failed batches: 45
- Common error: `the input length exceeds the context length`
- Average chunks per file: 7.2
- Average max chunk length: 6577.4
- Smallest max chunk length: 4109
- Largest max chunk length: 9539

## Summary Table

| File | Chunks | Max Chunk Length | Status | Error |
|---|---:|---:|---|---|
| E-1-C LU 773 Windsor - May 1, 2025.pdf | 8 | 6303 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-3-C LU 530 Sarnia - May 1, 2025 (1).pdf | 5 | 6236 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-4-C LU 120 London - May 1, 2025 (1).pdf | 7 | 6704 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-6-C LU 105 Hamilton - May 1, 2025.pdf | 8 | 6704 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-7-C LU 303 Niagara Penninsula - May 1, 2025.pdf | 8 | 7001 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-8A-C LU 804 Central Ontario - May 1, 2025.pdf | 6 | 6684 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-9-C LU 353 South - May 1, 2025 (1).pdf | 8 | 6747 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-9A-C LU 353 Pickering Project - May 1, 2025.pdf | 8 | 6614 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-10-C LU 353 Oshawa-Port Hope - May 1, 2025.pdf | 8 | 6614 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-12-C LU 115 Quinte- St. Lawrence - May 1, 2025.pdf | 5 | 6159 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-13-C LU 586 Ottawa - May 1, 2025 (1).pdf | 6 | 6698 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-14-C LU 353 North - May 1, 2025 (1).pdf | 7 | 6614 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-15-C LU 1687 Sudbury - July 24, 2025.pdf | 6 | 6337 | FAIL | `{"error":"the input length exceeds the context length"}` |
| E-16-C LU 402 Thunder Bay - May 1, 2025.pdf | 7 | 6700 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 01 LU 235 Windsor - May 1, 2025.pdf | 7 | 8461 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 02 LU 235 Chatham - May 1, 2025.pdf | 5 | 8146 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 03 LU 235 Sarnia - May 1, 2025.pdf | 8 | 8745 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM-04 LU 473 London - May 1 2026 .pdf | 5 | 7350 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 05 LU 562 Kitchener - May 1, 2025.pdf | 7 | 8493 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM-06 LU 537 Hamilton - May 1 2026 .pdf | 5 | 7576 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM-07 LU 537 Brantford - May 1 2026 .pdf | 8 | 8633 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM-08 LU 537 St Catherines - May 1 2026 .pdf | 14 | 5750 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 09 LU 30 Toronto - Sep 15, 2025.pdf | 7 | 8728 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 10 LU 30 Barrie - Sep 15, 2025.pdf | 10 | 8732 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 11 LU 30 Peterborough - Sep 15, 2025.pdf | 9 | 8469 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM-12 LU 269 Kingston - May 1 2026 .pdf | 6 | 7121 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 13 LU 47 Ottawa - May 1, 2025.pdf | 6 | 8492 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 14 LU 504 Sudbury - May 1, 2025.pdf | 6 | 9539 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 15 LU 504 Sault Ste. Marie - May 1, 2025.pdf | 5 | 8133 | FAIL | `{"error":"the input length exceeds the context length"}` |
| SM - 16 LU 397 Thunder Bay - May 1, 2025.pdf | 4 | 8754 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 46 Barrie UA - May 1 2025 (1).pdf | 8 | 4905 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 46 Toronto UA - May 1 2025 (1).pdf | 11 | 5436 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 67 Brantford Hamilton UA - May 1 2025 (1).pdf | 10 | 4932 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 67 Niagara UA - May 1 2025 (1).pdf | 9 | 4958 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 71 Ottawa UA - May 1 2025 (1).pdf | 6 | 4978 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 401 Belleville UA - May 1 2025 (1).pdf | 9 | 4963 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 401 Kingston - May 1 2025.pdf | 7 | 5025 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 401 Oshawa UA - May 1 2025 (1).pdf | 6 | 5486 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 527 Kitchener UA - May 1 2026.pdf | 8 | 4585 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 527 London UA - May 1 2026.pdf | 8 | 4418 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 527 Windsor UA - May 1 2026.pdf | 6 | 4109 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 628 Thunder Bay - May 1 2025.pdf | 8 | 4889 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 663 Sarnia UA - May 1 2026.pdf | 6 | 4143 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 800 Sault Ste. Marie UA - May 1 2025.pdf | 7 | 4928 | FAIL | `{"error":"the input length exceeds the context length"}` |
| Local 800 Sudbury UA - May 1 2025 (1).pdf | 8 | 4993 | FAIL | `{"error":"the input length exceeds the context length"}` |

## Per File Details

### E-1-C LU 773 Windsor - May 1, 2025.pdf

- Chunks: 8
- Max chunk length: 6303
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 259 |
| 1 | 6303 |
| 2 | 443 |
| 3 | 314 |
| 4 | 40 |
| 5 | 493 |
| 6 | 54 |
| 7 | 384 |

### E-3-C LU 530 Sarnia - May 1, 2025 (1).pdf

- Chunks: 5
- Max chunk length: 6236
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 251 |
| 1 | 6236 |
| 2 | 476 |
| 3 | 1334 |
| 4 | 32 |

### E-4-C LU 120 London - May 1, 2025 (1).pdf

- Chunks: 7
- Max chunk length: 6704
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 290 |
| 1 | 6704 |
| 2 | 484 |
| 3 | 314 |
| 4 | 601 |
| 5 | 186 |
| 6 | 408 |

### E-6-C LU 105 Hamilton - May 1, 2025.pdf

- Chunks: 8
- Max chunk length: 6704
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 252 |
| 1 | 6704 |
| 2 | 456 |
| 3 | 381 |
| 4 | 40 |
| 5 | 1132 |
| 6 | 54 |
| 7 | 678 |

### E-7-C LU 303 Niagara Penninsula - May 1, 2025.pdf

- Chunks: 8
- Max chunk length: 7001
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 261 |
| 1 | 7001 |
| 2 | 203 |
| 3 | 315 |
| 4 | 314 |
| 5 | 2548 |
| 6 | 159 |
| 7 | 508 |

### E-8A-C LU 804 Central Ontario - May 1, 2025.pdf

- Chunks: 6
- Max chunk length: 6684
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 225 |
| 1 | 6684 |
| 2 | 203 |
| 3 | 1343 |
| 4 | 170 |
| 5 | 571 |

### E-9-C LU 353 South - May 1, 2025 (1).pdf

- Chunks: 8
- Max chunk length: 6747
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 250 |
| 1 | 6747 |
| 2 | 442 |
| 3 | 314 |
| 4 | 40 |
| 5 | 902 |
| 6 | 54 |
| 7 | 431 |

### E-9A-C LU 353 Pickering Project - May 1, 2025.pdf

- Chunks: 8
- Max chunk length: 6614
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 262 |
| 1 | 6614 |
| 2 | 456 |
| 3 | 329 |
| 4 | 702 |
| 5 | 176 |
| 6 | 54 |
| 7 | 401 |

### E-10-C LU 353 Oshawa-Port Hope - May 1, 2025.pdf

- Chunks: 8
- Max chunk length: 6614
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 254 |
| 1 | 6614 |
| 2 | 446 |
| 3 | 314 |
| 4 | 760 |
| 5 | 176 |
| 6 | 54 |
| 7 | 510 |

### E-12-C LU 115 Quinte- St. Lawrence - May 1, 2025.pdf

- Chunks: 5
- Max chunk length: 6159
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 264 |
| 1 | 6159 |
| 2 | 1717 |
| 3 | 68 |
| 4 | 432 |

### E-13-C LU 586 Ottawa - May 1, 2025 (1).pdf

- Chunks: 6
- Max chunk length: 6698
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 85 |
| 1 | 163 |
| 2 | 6698 |
| 3 | 1734 |
| 4 | 54 |
| 5 | 458 |

### E-14-C LU 353 North - May 1, 2025 (1).pdf

- Chunks: 7
- Max chunk length: 6614
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 255 |
| 1 | 6614 |
| 2 | 443 |
| 3 | 314 |
| 4 | 702 |
| 5 | 176 |
| 6 | 585 |

### E-15-C LU 1687 Sudbury - July 24, 2025.pdf

- Chunks: 6
- Max chunk length: 6337
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 78 |
| 1 | 165 |
| 2 | 6337 |
| 3 | 203 |
| 4 | 2013 |
| 5 | 290 |

### E-16-C LU 402 Thunder Bay - May 1, 2025.pdf

- Chunks: 7
- Max chunk length: 6700
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 244 |
| 1 | 6700 |
| 2 | 452 |
| 3 | 204 |
| 4 | 744 |
| 5 | 296 |
| 6 | 421 |

### SM - 01 LU 235 Windsor - May 1, 2025.pdf

- Chunks: 7
- Max chunk length: 8461
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8461 |
| 1 | 971 |
| 2 | 318 |
| 3 | 840 |
| 4 | 3098 |
| 5 | 266 |
| 6 | 565 |

### SM - 02 LU 235 Chatham - May 1, 2025.pdf

- Chunks: 5
- Max chunk length: 8146
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 193 |
| 1 | 8146 |
| 2 | 1994 |
| 3 | 1996 |
| 4 | 511 |

### SM - 03 LU 235 Sarnia - May 1, 2025.pdf

- Chunks: 8
- Max chunk length: 8745
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8745 |
| 1 | 968 |
| 2 | 318 |
| 3 | 39 |
| 4 | 105 |
| 5 | 163 |
| 6 | 1718 |
| 7 | 912 |

### SM-04 LU 473 London - May 1 2026 .pdf

- Chunks: 5
- Max chunk length: 7350
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 191 |
| 1 | 7350 |
| 2 | 477 |
| 3 | 4293 |
| 4 | 314 |

### SM - 05 LU 562 Kitchener - May 1, 2025.pdf

- Chunks: 7
- Max chunk length: 8493
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8493 |
| 1 | 1097 |
| 2 | 316 |
| 3 | 39 |
| 4 | 105 |
| 5 | 1994 |
| 6 | 687 |

### SM-06 LU 537 Hamilton - May 1 2026 .pdf

- Chunks: 5
- Max chunk length: 7576
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 7576 |
| 1 | 1410 |
| 2 | 1048 |
| 3 | 1994 |
| 4 | 821 |

### SM-07 LU 537 Brantford - May 1 2026 .pdf

- Chunks: 8
- Max chunk length: 8633
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8633 |
| 1 | 101 |
| 2 | 472 |
| 3 | 316 |
| 4 | 205 |
| 5 | 360 |
| 6 | 1994 |
| 7 | 721 |

### SM-08 LU 537 St Catherines - May 1 2026 .pdf

- Chunks: 14
- Max chunk length: 5750
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 207 |
| 1 | 5750 |
| 2 | 301 |
| 3 | 142 |
| 4 | 2600 |
| 5 | 283 |
| 6 | 472 |
| 7 | 315 |
| 8 | 39 |
| 9 | 308 |
| 10 | 758 |
| 11 | 1668 |
| 12 | 824 |
| 13 | 380 |

### SM - 09 LU 30 Toronto - Sep 15, 2025.pdf

- Chunks: 7
- Max chunk length: 8728
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8728 |
| 1 | 1083 |
| 2 | 316 |
| 3 | 194 |
| 4 | 1660 |
| 5 | 1354 |
| 6 | 880 |

### SM - 10 LU 30 Barrie - Sep 15, 2025.pdf

- Chunks: 10
- Max chunk length: 8732
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8732 |
| 1 | 338 |
| 2 | 72 |
| 3 | 472 |
| 4 | 316 |
| 5 | 39 |
| 6 | 94 |
| 7 | 883 |
| 8 | 1722 |
| 9 | 1037 |

### SM - 11 LU 30 Peterborough - Sep 15, 2025.pdf

- Chunks: 9
- Max chunk length: 8469
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8469 |
| 1 | 539 |
| 2 | 472 |
| 3 | 316 |
| 4 | 39 |
| 5 | 107 |
| 6 | 883 |
| 7 | 1991 |
| 8 | 550 |

### SM-12 LU 269 Kingston - May 1 2026 .pdf

- Chunks: 6
- Max chunk length: 7121
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 85 |
| 1 | 7121 |
| 2 | 484 |
| 3 | 1866 |
| 4 | 1346 |
| 5 | 1053 |

### SM - 13 LU 47 Ottawa - May 1, 2025.pdf

- Chunks: 6
- Max chunk length: 8492
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8492 |
| 1 | 964 |
| 2 | 167 |
| 3 | 39 |
| 4 | 1990 |
| 5 | 762 |

### SM - 14 LU 504 Sudbury - May 1, 2025.pdf

- Chunks: 6
- Max chunk length: 9539
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 9539 |
| 1 | 966 |
| 2 | 319 |
| 3 | 209 |
| 4 | 1999 |
| 5 | 1839 |

### SM - 15 LU 504 Sault Ste. Marie - May 1, 2025.pdf

- Chunks: 5
- Max chunk length: 8133
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 203 |
| 1 | 8133 |
| 2 | 1788 |
| 3 | 1998 |
| 4 | 541 |

### SM - 16 LU 397 Thunder Bay - May 1, 2025.pdf

- Chunks: 4
- Max chunk length: 8754
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 8754 |
| 1 | 1995 |
| 2 | 1997 |
| 3 | 449 |

### Local 46 Barrie UA - May 1 2025 (1).pdf

- Chunks: 8
- Max chunk length: 4905
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 540 |
| 1 | 4905 |
| 2 | 478 |
| 3 | 416 |
| 4 | 753 |
| 5 | 171 |
| 6 | 1458 |
| 7 | 526 |

### Local 46 Toronto UA - May 1 2025 (1).pdf

- Chunks: 11
- Max chunk length: 5436
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 165 |
| 1 | 353 |
| 2 | 5436 |
| 3 | 481 |
| 4 | 412 |
| 5 | 707 |
| 6 | 171 |
| 7 | 301 |
| 8 | 40 |
| 9 | 754 |
| 10 | 455 |

### Local 67 Brantford Hamilton UA - May 1 2025 (1).pdf

- Chunks: 10
- Max chunk length: 4932
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 168 |
| 1 | 350 |
| 2 | 4932 |
| 3 | 475 |
| 4 | 416 |
| 5 | 252 |
| 6 | 40 |
| 7 | 1374 |
| 8 | 1195 |
| 9 | 791 |

### Local 67 Niagara UA - May 1 2025 (1).pdf

- Chunks: 9
- Max chunk length: 4958
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 85 |
| 1 | 350 |
| 2 | 4958 |
| 3 | 522 |
| 4 | 1908 |
| 5 | 166 |
| 6 | 939 |
| 7 | 111 |
| 8 | 441 |

### Local 71 Ottawa UA - May 1 2025 (1).pdf

- Chunks: 6
- Max chunk length: 4978
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 86 |
| 1 | 346 |
| 2 | 4978 |
| 3 | 475 |
| 4 | 2497 |
| 5 | 227 |

### Local 401 Belleville UA - May 1 2025 (1).pdf

- Chunks: 9
- Max chunk length: 4963
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 82 |
| 1 | 345 |
| 2 | 4963 |
| 3 | 473 |
| 4 | 416 |
| 5 | 804 |
| 6 | 171 |
| 7 | 855 |
| 8 | 227 |

### Local 401 Kingston - May 1 2025.pdf

- Chunks: 7
- Max chunk length: 5025
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 78 |
| 1 | 353 |
| 2 | 5025 |
| 3 | 476 |
| 4 | 1286 |
| 5 | 1100 |
| 6 | 420 |

### Local 401 Oshawa UA - May 1 2025 (1).pdf

- Chunks: 6
- Max chunk length: 5486
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 541 |
| 1 | 5486 |
| 2 | 492 |
| 3 | 432 |
| 4 | 800 |
| 5 | 1540 |

### Local 527 Kitchener UA - May 1 2026.pdf

- Chunks: 8
- Max chunk length: 4585
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 557 |
| 1 | 4585 |
| 2 | 495 |
| 3 | 416 |
| 4 | 736 |
| 5 | 254 |
| 6 | 893 |
| 7 | 806 |

### Local 527 London UA - May 1 2026.pdf

- Chunks: 8
- Max chunk length: 4418
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 555 |
| 1 | 4418 |
| 2 | 471 |
| 3 | 1122 |
| 4 | 297 |
| 5 | 386 |
| 6 | 54 |
| 7 | 550 |

### Local 527 Windsor UA - May 1 2026.pdf

- Chunks: 6
- Max chunk length: 4109
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 527 |
| 1 | 4109 |
| 2 | 480 |
| 3 | 1364 |
| 4 | 1018 |
| 5 | 176 |

### Local 628 Thunder Bay - May 1 2025.pdf

- Chunks: 8
- Max chunk length: 4889
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 82 |
| 1 | 341 |
| 2 | 4889 |
| 3 | 482 |
| 4 | 1245 |
| 5 | 172 |
| 6 | 740 |
| 7 | 577 |

### Local 663 Sarnia UA - May 1 2026.pdf

- Chunks: 6
- Max chunk length: 4143
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 182 |
| 1 | 345 |
| 2 | 4143 |
| 3 | 471 |
| 4 | 1145 |
| 5 | 1139 |

### Local 800 Sault Ste. Marie UA - May 1 2025.pdf

- Chunks: 7
- Max chunk length: 4928
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 90 |
| 1 | 354 |
| 2 | 4928 |
| 3 | 529 |
| 4 | 408 |
| 5 | 1025 |
| 6 | 1355 |

### Local 800 Sudbury UA - May 1 2025 (1).pdf

- Chunks: 8
- Max chunk length: 4993
- Status: FAIL
- Error: `{"error":"the input length exceeds the context length"}`

| Chunk Index | Length |
|---:|---:|
| 0 | 541 |
| 1 | 4993 |
| 2 | 478 |
| 3 | 424 |
| 4 | 1063 |
| 5 | 179 |
| 6 | 1019 |
| 7 | 725 |
