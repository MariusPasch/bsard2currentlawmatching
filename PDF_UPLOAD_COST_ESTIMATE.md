# PDF Upload Cost Estimation — BSARD Corpus (49 PDFs)

**Author:** Marios Paschalidis | **Date:** 2026-04-01  
**Project:** BSARD RAG Thesis — Dataset Creation

---

## Methodology

Cost estimates are derived from a **linear regression** fit on two calibration data points
taken from the other pipeline's output (`MyDocuments.csv`):

| Calibration document | Pages | Actual total cost |
|---|---:|---:|
| DECISION (EU) 2017/340 | 17 | $0.1082524 |
| LIVRE 1ER DISPOSITIONS COMMUNES ET GÉNÉRALES (PARTIE DÉCRÉTALE) | 615 | $5.24849495 |

**Fitted model:** `cost = $0.008596 × pages − $0.037875` (intercept floored at $0)

Page counts come from PyMuPDF (`fitz`) reading each PDF directly.  
Two PDFs (`1899`, `1932`) are 1-page placeholder files and are excluded from the total.

> **Uncertainty:** Only 2 calibration points are available; actual costs may vary by ±20–30%
> depending on document density, number of definitions extracted, and LLM model pricing.

---

## Results — Ranked by Number of Pages

| # | Law Code | PDF Filename | Pages | Est. Cost |
|---|----------|--------------|------:|----------:|
| 1 | Code Réglementaire Wallon de l'Action sociale et de la Santé | `img_l_pdf_2013_07_04_2013A27132_F.pdf` | 736 | $6.29 |
| 2 | Code de Droit Economique | `img_l_pdf_2013_02_28_2013A11134_F.pdf` | 730 | $6.24 |
| 3 | Code de la Démocratie Locale et de la Décentralisation | `img_l_pdf_2004_04_22_2004A27184_F.pdf` | 477 | $4.06 |
| 4 | Code Wallon de l'Action sociale et de la Santé | `img_l_pdf_2011_09_29_2011A27223_F.pdf` | 324 | $2.75 |
| 5 | Code du Bien-être au Travail | `img_l_pdf_2017_04_28_2017A10461_F.pdf` | 308 | $2.61 |
| 6 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101053_F.pdf` | 302 | $2.56 |
| 7 | Code de la Navigation | `img_l_pdf_2019_05_08_2019A12565_F.pdf` | 277 | $2.34 |
| 8 | Code Wallon du Développement Territorial | `img_l_pdf_2016_07_20_2016A05561_F.pdf` | 244 | $2.06 |
| 9 | Code Wallon de l'Enseignement Fondamental et de l'Enseignement Secondaire | `img_l_pdf_2019_05_03_2019A30854_F.pdf` | 233 | $1.96 |
| 10 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101055_F.pdf` | 173 | $1.45 |
| 11 | Code Wallon de l'Habitation Durable | `img_l_pdf_1998_10_29_1998A27652_F.pdf` | 148 | $1.23 |
| 12 | Code Pénal | `img_l_pdf_1867_06_08_1867060850_F.pdf` | 138 | $1.15 |
| 13 | Code Civil | `img_l_pdf_1804_03_21_1804032150_F.pdf` | 129 | $1.07 |
| 14 | Code Bruxellois de l'Aménagement du Territoire | `img_l_pdf_2004_04_09_2004A31182_F.pdf` | 128 | $1.06 |
| 15 | Code Pénal Social | `img_l_pdf_2010_06_06_2010A09589_F.pdf` | 123 | $1.02 |
| 16 | Code Ferroviaire | `img_l_pdf_2013_08_30_2013014641_F.pdf` | 118 | $0.98 |
| 17 | Code de l'Eau intégré au Code Wallon de l'Environnement | `img_l_pdf_2004_05_27_2004A27101_F.pdf` | 116 | $0.96 |
| 18 | Code Wallon de l'Agriculture | `img_l_pdf_2014_03_27_2014027151_F.pdf` | 101 | $0.83 |
| 19 | Code Bruxellois du Logement | `img_l_pdf_2003_07_17_2013A31614_F.pdf` | 99 | $0.81 |
| 20 | Code Bruxellois de l'Air, du Climat et de la Maîtrise de l'Energie | `img_l_pdf_2013_05_02_2013031357_F.pdf` | 99 | $0.81 |
| 21 | Code de la Fonction Publique Wallonne | `img_l_pdf_2003_12_18_2003027783_F.pdf` | 85 | $0.69 |
| 22 | Code d'Instruction Criminelle | `img_l_pdf_1808_11_17_1808111701_F.pdf` | 82 | $0.67 |
| 23 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101056_F.pdf` | 79 | $0.64 |
| 24 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101054_F.pdf` | 78 | $0.63 |
| 25 | Codes des Droits et Taxes Divers | `img_l_pdf_1927_03_02_1927030201_F.pdf` | 67 | $0.54 |
| 26 | Code Electoral | `img_l_pdf_1894_04_12_1894041255_F.pdf` | 62 | $0.50 |
| 27 | Code Civil | `img_l_pdf_1804_03_21_1804032154_F.pdf` | 55 | $0.43 |
| 28 | Code Forestier | `img_l_pdf_1854_12_19_1854121950_F.pdf` | 39 | $0.30 |
| 29 | Code de Droit International Privé | `img_l_pdf_2004_07_16_2004009511_F.pdf` | 37 | $0.28 |
| 30 | Code d'Instruction Criminelle | `img_l_pdf_1808_11_19_1808111901_F.pdf` | 36 | $0.27 |
| 31 | Code Civil | `img_l_pdf_1804_03_21_1804032153_F.pdf` | 33 | $0.25 |
| 32 | Code d'Instruction Criminelle | `img_l_pdf_1808_12_09_1808120950_F.pdf` | 31 | $0.23 |
| 33 | Code d'Instruction Criminelle | `img_l_pdf_1808_12_12_1808121250_F.pdf` | 30 | $0.22 |
| 34 | La Constitution | `img_l_pdf_1994_02_17_1994021048_F.pdf` | 30 | $0.22 |
| 35 | Code Civil | `img_l_pdf_1804_03_21_1804032152_F.pdf` | 25 | $0.18 |
| 36 | Code Wallon du Bien-être des animaux | `img_l_pdf_2018_10_04_2018A15578_F.pdf` | 25 | $0.18 |
| 37 | Code Consulaire | `img_l_pdf_2013_12_21_2014A15009_F.pdf` | 18 | $0.12 |
| 38 | Code Rural | `img_l_pdf_1886_10_07_1886100750_F.pdf` | 17 | $0.11 |
| 39 | Code de la Nationalité Belge | `img_l_pdf_1984_06_28_1984900065_F.pdf` | 17 | $0.11 |
| 40 | Code Civil | `img_l_pdf_1804_03_21_1804032151_F.pdf` | 14 | $0.08 |
| 41 | Code d'Instruction Criminelle | `img_l_pdf_1808_12_16_1808121650_F.pdf` | 14 | $0.08 |
| 42 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101052_F.pdf` | 14 | $0.08 |
| 43 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101057_F.pdf` | 13 | $0.07 |
| 44 | Code Civil | `img_l_pdf_1804_03_21_1804032155_F.pdf` | 12 | $0.07 |
| 45 | Code d'Instruction Criminelle | `img_l_pdf_1808_12_10_1808121050_F.pdf` | 10 | $0.05 |
| 46 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101063_F.pdf` | 9 | $0.04 |
| 47 | Code Judiciaire | `img_l_pdf_1967_10_10_1967101064_F.pdf` | 3 | $0.00 |
| 48 | Code Pénal Militaire | `img_l_pdf_1899_06_15_1899061501_F.pdf` | 1 | *(placeholder)* |
| 49 | Code Electoral Communal Bruxellois | `img_l_pdf_1932_08_04_1932080451_F.pdf` | 1 | *(placeholder)* |

---

## Summary

| Metric | Value |
|--------|------:|
| Total PDFs | 49 |
| Processable PDFs (excl. 2 placeholders) | 47 |
| Total pages (47 PDFs) | 5,938 |
| **Estimated total cost** | **~$49.27** |
| Largest PDF (Code Réglementaire Wallon) | 736 pages / $6.29 |
| Smallest processable PDF (Code Judiciaire) | 3 pages / $0.00 |
