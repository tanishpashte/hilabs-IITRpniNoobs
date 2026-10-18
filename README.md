# Centene California Commercial Group PPO Rate Curation Pipeline

**Payer:** Centene Management Company LLC / Health Net  
**Target Market:** Commercial Group, California (`plan_market_type: "group"`)  
**Network:** PPO Network (`healthnet-ca_in-network.json`)  
**Deliverable Standard:** CMS Transparency in Coverage (TiC) Rule — Deliverables 1 through 6  

---

## 1. Quick Start: Re-Run End-to-End

This repository is designed with **zero hardcoded paths** and can be re-run cleanly from any machine or directory.

### Step 1: Set Up Python Environment
Ensure Python 3.9+ is installed:
```bash
# Optional: Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required lightweight dependencies
pip install -r requirements.txt
```

### Step 2: Execute Master Pipeline
Run the master pipeline script with a single command:
```bash
python run_pipeline.py
```
*(Total runtime: approximately **10 to 15 seconds** using low-memory streaming parsers).*

---

## 2. Pipeline Execution Steps

The pipeline can also be run sequentially step-by-step:

```bash
# Step 1: Parse Centene Index Files & Rule out HMO/POS/EPO (Challenges C1 & C2)
python "2b logic parse_index.py"

# Step 2: Extract & Deduplicate In-Network Rates using Median Contract Policy (Challenge C4)
python step2_deduplicate_rates.py

# Step 3: Multi-Tier Specialty Mapping (Sheet 1 Taxonomy & Sheet 3 Procedure Defaults)
python step3_map_specialty.py

# Step 4: Physical Practice Location Curation & PO Box Elimination (Challenge C5)
python step4_curate_addresses.py

# Step 5: Final Deliverable Assembly (Challenge C6 / Deliverable 1)
python step5_build_final_rate_file.py

# Step 6: Automated 8-File Quality & Compliance Evaluation (Challenge C3)
python "3 evaluate_ptd_quality.py"
```

---

## 3. Deliverables Manifest

All required challenge deliverables are self-contained in this directory:

| Deliverable # | Artifact | File Name | Description & Verification |
|:---:|---|---|---|
| **1** | **Rate File (CSV)** | [`1 rate-file.csv`](./1%20rate-file.csv) | **21,392 rows**: Exact 6 columns (`NPI`, `TIN`, `Address`, `Billing Code`, `Specialty`, `Rate`) with **100.0% verified physical California addresses**. |
| **1** | **Rate File (Excel)** | [`1 rate-file.xlsx`](./1%20rate-file.xlsx) | Official styled Excel workbook (.xlsx) with formatted currency (`$#,##0.00`), freeze panes, and auto-width columns. |
| **2a** | **Logic File: Rate Engine** | [`2a logic extract_ppo_rates.py`](./2a%20logic%20extract_ppo_rates.py) | Python implementation of the multi-rate median resolution policy and provider group linking. |
| **2b** | **Logic File: Network Engine** | [`2b logic parse_index.py`](./2b%20logic%20parse_index.py) | Multi-signal priority logic to identify California commercial group PPO plans and rule out HMO/POS/EPO. |
| **3** | **Quality Scoring Engine** | [`3 evaluate_ptd_quality.py`](./3%20evaluate_ptd_quality.py) | Automated low-memory quality evaluator grading all 8 project files across 6 core quality dimensions. |
| **4** | **Summary File** | [`4 summary.md`](./4%20summary.md) | High-level metrics report: index files parsed, PPO plans identified, quality scores, rates extracted, and address linkage rates. |
| **—** | **Complete Technical Guide** | [`document.md`](./document.md) | Comprehensive 8-file quality evaluation guide, deduction rules matrix, and empirical multi-rate breakdown. |

---

## 4. Key Methodologies & Architectural Highlights

### Core Problem 1: Network Mapping (Challenges C1 & C2)
* Evaluated **3,215 national plans** across 4 Centene brand index files (`Health Net`, `Ambetter`, `Fidelis`, `QualChoice`).
* Isolated **1,312 California Commercial Group plans** (`plan_market_type: "group"`).
* Ruled out **723 HMO plans** (`CommunityCare`, `SmartCare`, `Salud`) and **133 POS/EOA hybrid plans**.
* Identified **456 commercial group PPO plans** (**250 unique `plan_id` EINs**), linking to the single monolithic in-network rate file `healthnet-ca_in-network.json` (701.6 MB).

### Core Problem 2: File Quality Assessment (Challenge C3)
* Graded all 8 project files with scores from **90/100 to 100/100 (Grades A to A+)**.
* The in-network rate MRF scored **100/100 (A+)** with 0 negative rates, 0 zero-dollar rates, and 100% explicit dollar figures.

### Supporting Step: Rate Deduplication & Multi-Rate Policy (Challenge C4)
* Streamed **1,500,288 price records** across 1,717 billing codes in 100,000-row chunks using C-based `ijson` (< 100 MB RAM).
* Resolved multiple contract tiers per `(NPI, TIN, Code)` by computing the **median negotiated rate**, preventing distortion from customized outlier carve-outs while preserving min/max audit trails.
* Curated **21,858 unique base rate tuples**.

### Multi-Tier Specialty Resolution (Step 3)
* **Option A (Primary Taxonomy Match)**: 28.3% mapped to clinical specialties via Sheet 1 (`Taxonomy-Spec Xwalk`).
* **Option B (Procedure Default)**: 10.3% mapped via Sheet 3 (`Spec-Proc Weights`) using the Rank 1 highest-weighted specialty.
* **Facility/Organization Descriptions**: 60.5% institutional providers classified directly via NPPES registry taxonomy.

### Core Problem 3: Address Mapping & Curation (Challenge C5)
* Solved the industry-wide challenge where ~80% of NPPES mailing addresses are stale corporate PO boxes.
* Strictly discarded `address_purpose == "MAILING"` and extracted verified physical practice locations (`address_purpose == "LOCATION"`).
* Evaluated secondary clinical practice sites (`pl_pfile`) and aligned multi-location clinicians to their TIN facility city (e.g. *Mountain View Urgent Care* ➔ *Mountain View, CA*).
* Pruned 466 address-less records to produce a final deliverable with **100.0% verified physical California practice addresses across all 21,392 rows**.

---

## 5. Zero Hardcoded Paths Guarantee

All scripts dynamically resolve paths relative to the project structure:
```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "submission" else BASE_DIR
```
Whether invoked from repository root or inside the `submission/` directory, files resolve automatically across Linux, macOS, and Windows.
