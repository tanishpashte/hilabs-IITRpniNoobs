#!/usr/bin/env python3
"""
Master Pipeline Runner: Price Transparency Data (PTD) Provider Rate Curation
Re-runs the entire pipeline end-to-end with ZERO hardcoded paths:
  1. Parse Centene Index Files & Identify PPO Network (Challenges C1 & C2)
  2. Grade PTD File Quality & Schema Compliance (Challenge C3)
  3. Extract & Deduplicate In-Network Rates using Median Contract Policy (Challenge C4)
  4. Multi-Tier Specialty Resolution via NUCC Taxonomy & Procedure Crosswalk
  5. Curate Physical Practice Locations & Filter Stale Addresses (Challenge C5)
  6. Assemble Final Rate Deliverables (Deliverable 1 CSV & Excel) (Challenge C6)

Usage:
  python run_pipeline.py
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Resolve base directories dynamically without hardcoding
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "submission" else SCRIPT_DIR

def run_step(step_name, script_path, cwd=PROJECT_ROOT):
    print("=" * 75)
    print(f"▶ EXECUTING: {step_name}")
    print(f"  Script: {script_path}")
    print("=" * 75)
    t0 = time.time()
    result = subprocess.run([sys.executable, str(script_path)], cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Error during {step_name} (Exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"✔ Completed {step_name} in {time.time() - t0:.2f} seconds.\n")

def main():
    print("#" * 75)
    print("  CENTENE CALIFORNIA COMMERCIAL GROUP PPO RATE CURATION PIPELINE")
    print(f"  Project Root: {PROJECT_ROOT}")
    print("#" * 75)
    print()
    start_total = time.time()

    # Step 1: Parse Index & Identify PPO Plans
    run_step(
        "Step 1: Network Mapping (C1 & C2 - Parse Index & Find PPO)",
        SCRIPT_DIR / "2b logic parse_index.py" if (SCRIPT_DIR / "2b logic parse_index.py").exists() else SCRIPT_DIR / "parse_index.py"
    )

    # Step 2: Extract & Deduplicate Rates (C4)
    run_step(
        "Step 2: Rate Deduplication & Provider Linking (C4 - Median Policy)",
        SCRIPT_DIR / "step2_deduplicate_rates.py"
    )

    # Step 3: Specialty Resolution
    run_step(
        "Step 3: Multi-Tier Specialty Mapping (Sheet 1 Taxonomy & Sheet 3 Procedure)",
        SCRIPT_DIR / "step3_map_specialty.py"
    )

    # Step 4: Address Curation & Multi-Location Alignment (C5)
    run_step(
        "Step 4: Practice Location Curation (C5 - Filter Stale Data & PO Boxes)",
        SCRIPT_DIR / "step4_curate_addresses.py"
    )

    # Step 5: Final Deliverable Assembly (C6 / Deliverable 1)
    run_step(
        "Step 5: Final Deliverable Assembly (C6 - Output CSV & Excel)",
        SCRIPT_DIR / "step5_build_final_rate_file.py"
    )

    # Step 6: File Quality Audit (C3)
    if (SCRIPT_DIR / "3 evaluate_ptd_quality.py").exists():
        run_step(
            "Step 6: File Quality Evaluation (C3 - 8-File Scorecard)",
            SCRIPT_DIR / "3 evaluate_ptd_quality.py"
        )

    # Sync final output to submission folder
    final_csv = PROJECT_ROOT / "healthnet_csv" / "final_provider_rate_file.csv"
    final_xlsx = PROJECT_ROOT / "healthnet_csv" / "final_provider_rate_file.xlsx"
    target_csv = SCRIPT_DIR / "1 rate-file.csv"
    target_xlsx = SCRIPT_DIR / "1 rate-file.xlsx"

    if final_csv.exists() and final_csv != target_csv:
        import shutil
        shutil.copy2(final_csv, target_csv)
    if final_xlsx.exists() and final_xlsx != target_xlsx:
        import shutil
        shutil.copy2(final_xlsx, target_xlsx)

    elapsed_total = time.time() - start_total
    print("#" * 75)
    print(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {elapsed_total:.2f} SECONDS!")
    print(f"  • Deliverable 1 CSV:   {target_csv}")
    print(f"  • Deliverable 1 Excel: {target_xlsx}")
    print(f"  • Deliverable 4 KPI:   {SCRIPT_DIR / '4 summary.md'}")
    print("#" * 75)

if __name__ == "__main__":
    main()
