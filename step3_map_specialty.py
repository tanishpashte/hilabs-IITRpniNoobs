#!/usr/bin/env python3
"""
Step 3: Specialty Resolution via Multi-Tier Mapping Strategy
- Source: NPPES/Rate Benchmarking Individual Weights_Hackathon.xlsx
- Option A (Primary - Provider Taxonomy):
    Look up provider's taxonomy in NPPES (nppes.csv / npiregistry.cms.hhs.gov.json)
    Join on Sheet 1 (Taxonomy-Spec Xwalk: Taxonomy Code -> SPEC_DESCR, SPEC_CD)
- Option B (Secondary - Procedure Default):
    If NPI's taxonomy is unlisted or missing in Sheet 1, join on Sheet 3
    (Spec-Proc Weights: PROC_CD -> SPEC_DESCRIPTION using top-ranked specialty)
- Fallback:
    If unmapped in Sheet 1 & 3 (e.g., Facility/Organization taxonomies like Ambulatory Surgery Centers),
    use NPPES primary_taxonomy_desc.
Outputs: healthnet_csv/step3_rates_with_specialty.csv
"""

import csv
import openpyxl
import os
import sys
import time

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "submission" else BASE_DIR

CURATED_RATES_CSV = PROJECT_ROOT / "healthnet_csv" / "step2_curated_rates.csv"
NPPES_CSV = PROJECT_ROOT / "healthnet_csv" / "nppes.csv"
EXCEL_PATH = PROJECT_ROOT / "NPPES" / "Rate Benchmarking Individual Weights_Hackathon.xlsx"
OUTPUT_CSV = PROJECT_ROOT / "healthnet_csv" / "step3_rates_with_specialty.csv"

def run_step_3_specialty_mapping():
    print("=" * 70)
    print("Step 3: Specialty Resolution via Taxonomy & Procedure Mapping")
    print("=" * 70)
    t0 = time.time()

    # 1. Load Sheet 1: Taxonomy-Spec Xwalk
    print(f"Loading Sheet 1 (Taxonomy-Spec Xwalk) from {EXCEL_PATH}...")
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws1 = wb["Taxonomy-Spec Xwalk"]
    tax_map = {} # taxonomy_code -> (spec_descr, spec_cd, spec_type)
    for row in ws1.iter_rows(min_row=2, values_only=True):
        spec_type, spec_cd, spec_descr, tax_code = row[0], row[1], row[2], row[3]
        if tax_code:
            tax_code_clean = str(tax_code).strip()
            tax_map[tax_code_clean] = {
                "spec_descr": str(spec_descr).strip() if spec_descr else "",
                "spec_cd": str(spec_cd).strip() if spec_cd else "",
                "spec_type": str(spec_type).strip() if spec_type else ""
            }
    print(f"Loaded {len(tax_map)} taxonomy mappings from Sheet 1.")

    # 2. Load Sheet 3: Spec-Proc Weights (Procedure Default)
    print("Loading Sheet 3 (Spec-Proc Weights) for Option B procedure default...")
    ws3 = wb["Spec-Proc Weights"]
    proc_candidates = {}
    for row in ws3.iter_rows(min_row=2, values_only=True):
        spec_cd, spec_descr, proc_cd, rank, weight = row[0], row[1], row[2], row[3], row[4]
        if proc_cd:
            p_cd = str(proc_cd).strip()
            r_val = int(rank) if rank is not None else 9999
            w_val = float(weight) if weight is not None else 0.0
            if p_cd not in proc_candidates:
                proc_candidates[p_cd] = []
            # Sort key: lowest rank first, then highest weight
            proc_candidates[p_cd].append((r_val, -w_val, str(spec_descr).strip(), str(spec_cd).strip()))

    proc_map = {}
    for p_cd, cands in proc_candidates.items():
        cands.sort()
        best = cands[0]
        proc_map[p_cd] = {
            "spec_descr": best[2],
            "spec_cd": best[3],
            "rank": best[0]
        }
    print(f"Loaded {len(proc_map)} unique procedure code defaults from Sheet 3.")

    # 3. Load NPPES provider details (npi -> primary taxonomy, all taxonomies, entity type, desc)
    print(f"Loading NPPES provider data from {NPPES_CSV}...")
    nppes_lookup = {}
    if os.path.exists(NPPES_CSV):
        with open(NPPES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                npi = row.get("npi", "").strip()
                if npi:
                    prim_code = row.get("primary_taxonomy_code", "").strip()
                    prim_desc = row.get("primary_taxonomy_desc", "").strip()
                    all_tax = [t.strip() for t in row.get("all_taxonomy_codes", "").split("|") if t.strip()]
                    ent_type = row.get("entity_type", "").strip()
                    full_name = row.get("provider_full_name", "").strip()
                    addr = row.get("practice_full_address", "").strip()
                    nppes_lookup[npi] = {
                        "primary_taxonomy_code": prim_code,
                        "primary_taxonomy_desc": prim_desc,
                        "all_taxonomy_codes": all_tax,
                        "entity_type": ent_type,
                        "provider_full_name": full_name,
                        "practice_full_address": addr
                    }
    print(f"Loaded details for {len(nppes_lookup):,} NPIs from NPPES.")

    # 4. Process curated rates and apply Option A -> Option B -> Fallback
    print(f"Joining and mapping specialty onto {CURATED_RATES_CSV}...")
    total_records = 0
    count_opt_a_prim = 0
    count_opt_a_sec = 0
    count_opt_b = 0
    count_nppes_fallback = 0
    count_unassigned = 0

    with open(CURATED_RATES_CSV, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = [
            "npi",
            "tin",
            "business_name",
            "billing_code",
            "billing_code_type",
            "name",
            "description",
            "billing_class",
            "curated_rate",
            "specialty",
            "specialty_code",
            "specialty_mapping_method",
            "primary_taxonomy_code",
            "primary_taxonomy_desc",
            "entity_type",
            "min_rate",
            "max_rate",
            "rate_observations"
        ]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            total_records += 1
            npi = row.get("npi", "").strip()
            b_code = row.get("billing_code", "").strip()

            prov_info = nppes_lookup.get(npi, {})
            prim_tax = prov_info.get("primary_taxonomy_code", "")
            prim_desc = prov_info.get("primary_taxonomy_desc", "")
            all_tax = prov_info.get("all_taxonomy_codes", [])
            ent_type = prov_info.get("entity_type", "")

            specialty = ""
            specialty_cd = ""
            mapping_method = ""

            # Option A (Primary): Match provider's primary taxonomy against Sheet 1
            if prim_tax and prim_tax in tax_map:
                specialty = tax_map[prim_tax]["spec_descr"]
                specialty_cd = tax_map[prim_tax]["spec_cd"]
                mapping_method = "Option A (Primary Taxonomy Match)"
                count_opt_a_prim += 1

            # Option A (Secondary Taxonomy): If primary unlisted, check secondary taxonomies in Sheet 1
            elif any(t in tax_map for t in all_tax):
                for t in all_tax:
                    if t in tax_map:
                        specialty = tax_map[t]["spec_descr"]
                        specialty_cd = tax_map[t]["spec_cd"]
                        mapping_method = "Option A (Secondary Taxonomy Match)"
                        count_opt_a_sec += 1
                        break

            # Option B (Secondary): Procedure code default from Sheet 3 (top-ranked specialty)
            elif b_code in proc_map:
                specialty = proc_map[b_code]["spec_descr"]
                specialty_cd = proc_map[b_code]["spec_cd"]
                mapping_method = "Option B (Procedure Default - Top Rank)"
                count_opt_b += 1

            # Fallback: Facility/Organization taxonomy description from NPPES
            elif prim_desc:
                specialty = prim_desc
                specialty_cd = "FACILITY/ORG"
                mapping_method = "NPPES Taxonomy Description (Facility/Organization)"
                count_nppes_fallback += 1

            else:
                specialty = "Unassigned"
                specialty_cd = "UNKNOWN"
                mapping_method = "Unassigned"
                count_unassigned += 1

            out_row = {
                "npi": npi,
                "tin": row.get("tin", ""),
                "business_name": row.get("business_name", ""),
                "billing_code": b_code,
                "billing_code_type": row.get("billing_code_type", ""),
                "name": row.get("name", ""),
                "description": row.get("description", ""),
                "billing_class": row.get("billing_class", ""),
                "curated_rate": row.get("curated_rate", ""),
                "specialty": specialty,
                "specialty_code": specialty_cd,
                "specialty_mapping_method": mapping_method,
                "primary_taxonomy_code": prim_tax,
                "primary_taxonomy_desc": prim_desc,
                "entity_type": ent_type,
                "min_rate": row.get("min_rate", ""),
                "max_rate": row.get("max_rate", ""),
                "rate_observations": row.get("rate_observations", "")
            }
            writer.writerow(out_row)

    t_end = time.time()
    print("=" * 70)
    print(f"Step 3 completed successfully in {t_end - t0:.2f} seconds.")
    print(f"Total curated rates processed: {total_records:,}")
    print(f"  • Option A (Primary Taxonomy Match):            {count_opt_a_prim:,} ({count_opt_a_prim/total_records*100:.1f}%)")
    print(f"  • Option A (Secondary Taxonomy Match):          {count_opt_a_sec:,} ({count_opt_a_sec/total_records*100:.1f}%)")
    print(f"  • Option B (Procedure Default - Top Rank):      {count_opt_b:,} ({count_opt_b/total_records*100:.1f}%)")
    print(f"  • NPPES Facility/Organization Description:      {count_nppes_fallback:,} ({count_nppes_fallback/total_records*100:.1f}%)")
    print(f"  • Unassigned (e.g. placeholder NPI 0):          {count_unassigned:,} ({count_unassigned/total_records*100:.1f}%)")
    print(f"Output saved to: {OUTPUT_CSV}")
    print("=" * 70)

if __name__ == "__main__":
    run_step_3_specialty_mapping()
