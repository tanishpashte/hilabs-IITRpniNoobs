#!/usr/bin/env python3
"""
Step 5: Produce the Final Rate File (Challenge C6 / Deliverable 1)
Joins the curated rate dataset (Step 3) with the curated physical practice addresses (Step 4)
to produce the final official deliverable specified in ps.md:
- Granularity: Exactly one row per NPI, TIN, Address, and Billing Code
- Deliverable 1 Columns: NPI, TIN, Address, Billing Code, Specialty, Rate

Outputs:
1. healthnet_csv/final_provider_rate_file.csv
2. healthnet_csv/final_provider_rate_file.xlsx (Official Deliverable 1 Excel)
3. healthnet_csv/final_provider_rate_file_detailed.csv (Enriched version with audit metrics)
"""

import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
import sys
import time

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "submission" else BASE_DIR

STEP3_RATES_CSV = PROJECT_ROOT / "healthnet_csv" / "step3_rates_with_specialty.csv"
STEP4_ADDR_CSV = PROJECT_ROOT / "healthnet_csv" / "curated_provider_addresses.csv"

OUTPUT_FINAL_CSV = PROJECT_ROOT / "healthnet_csv" / "final_provider_rate_file.csv"
OUTPUT_FINAL_XLSX = PROJECT_ROOT / "healthnet_csv" / "final_provider_rate_file.xlsx"
OUTPUT_DETAILED_CSV = PROJECT_ROOT / "healthnet_csv" / "final_provider_rate_file_detailed.csv"

def run_step_5_assembly():
    print("=" * 70)
    print("Step 5: Final Provider Rate File Assembly (Challenge C6 / Deliverable 1)")
    print("=" * 70)
    t0 = time.time()

    # 1. Load curated addresses: (npi, tin) -> address info
    print(f"Loading curated addresses from {STEP4_ADDR_CSV}...")
    address_lookup = {}
    with open(STEP4_ADDR_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            npi = row.get("npi", "").strip()
            tin = row.get("tin", "").strip()
            key = (npi, tin)
            address_lookup[key] = {
                "full_address": row.get("full_address", "").strip(),
                "confidence": row.get("address_confidence", "").strip(),
                "curation_method": row.get("curation_method", "").strip(),
                "city": row.get("city", "").strip(),
                "state": row.get("state", "").strip(),
                "zip_code": row.get("zip_code", "").strip()
            }
    print(f"Loaded curated address profiles for {len(address_lookup):,} (NPI, TIN) provider entities.")

    # 2. Join rates with addresses to produce Deliverable 1 records
    print(f"Joining rates from {STEP3_RATES_CSV} with addresses...")
    final_rows = []
    detailed_rows = []

    matched_addr_count = 0
    missing_addr_count = 0

    with open(STEP3_RATES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            npi = row.get("npi", "").strip()
            tin = row.get("tin", "").strip()
            b_code = row.get("billing_code", "").strip()
            specialty = row.get("specialty", "").strip()
            rate_val = row.get("curated_rate", "").strip()

            key = (npi, tin)
            addr_info = address_lookup.get(key, {})
            address = addr_info.get("full_address", "")
            addr_conf = addr_info.get("confidence", "Low")
            addr_method = addr_info.get("curation_method", "")

            if address:
                matched_addr_count += 1
                # Exact 6 required columns for Deliverable 1
                final_rows.append({
                    "NPI": npi,
                    "TIN": tin,
                    "Address": address,
                    "Billing Code": b_code,
                    "Specialty": specialty,
                    "Rate": float(rate_val) if rate_val else 0.0
                })
            else:
                missing_addr_count += 1

            # Enriched audit row
            detailed_rows.append({
                "NPI": npi,
                "TIN": tin,
                "Business Name": row.get("business_name", ""),
                "Address": address,
                "Address Confidence": addr_conf,
                "Address Curation Method": addr_method,
                "Billing Code": b_code,
                "Billing Code Type": row.get("billing_code_type", ""),
                "Procedure Name": row.get("name", ""),
                "Billing Class": row.get("billing_class", ""),
                "Specialty": specialty,
                "Specialty Code": row.get("specialty_code", ""),
                "Specialty Mapping Method": row.get("specialty_mapping_method", ""),
                "Rate": float(rate_val) if rate_val else 0.0,
                "Min Rate": row.get("min_rate", ""),
                "Max Rate": row.get("max_rate", ""),
                "Rate Observations": row.get("rate_observations", "")
            })

    total_count = len(final_rows)
    print(f"Assembled {total_count:,} final rate records:")
    print(f"  • Rates with verified physical practice address: {matched_addr_count:,} ({matched_addr_count/total_count*100:.1f}%)")
    print(f"  • Rates without physical address on file:        {missing_addr_count:,} ({missing_addr_count/total_count*100:.1f}%)")

    # 3. Write Deliverable 1 CSV
    print(f"Writing Deliverable 1 CSV to {OUTPUT_FINAL_CSV}...")
    with open(OUTPUT_FINAL_CSV, "w", newline="", encoding="utf-8") as f_out:
        fieldnames = ["NPI", "TIN", "Address", "Billing Code", "Specialty", "Rate"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for r in final_rows:
            writer.writerow({
                "NPI": r["NPI"],
                "TIN": r["TIN"],
                "Address": r["Address"],
                "Billing Code": r["Billing Code"],
                "Specialty": r["Specialty"],
                "Rate": f"{r['Rate']:.2f}"
            })
    print(f"Saved: {OUTPUT_FINAL_CSV}")

    # 4. Write Detailed Auditing CSV
    print(f"Writing Detailed Auditing CSV to {OUTPUT_DETAILED_CSV}...")
    with open(OUTPUT_DETAILED_CSV, "w", newline="", encoding="utf-8") as f_out:
        fieldnames = list(detailed_rows[0].keys())
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(detailed_rows)
    print(f"Saved: {OUTPUT_DETAILED_CSV}")

    # 5. Write Deliverable 1 Excel Workbook (.xlsx)
    print(f"Generating Deliverable 1 Excel Workbook at {OUTPUT_FINAL_XLSX}...")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Provider Rates"

    # Styling
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    num_alignment = Alignment(horizontal="right")
    text_alignment = Alignment(horizontal="left")

    headers = ["NPI", "TIN", "Address", "Billing Code", "Specialty", "Rate"]
    ws.append(headers)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[1].height = 24

    for r in final_rows:
        ws.append([
            r["NPI"],
            r["TIN"],
            r["Address"],
            r["Billing Code"],
            r["Specialty"],
            r["Rate"]
        ])

    # Format Rate column as currency / decimal
    for row_idx in range(2, len(final_rows) + 2):
        ws.cell(row=row_idx, column=6).number_format = '$#,##0.00'

    # Auto-adjust column widths
    column_widths = {1: 15, 2: 15, 3: 45, 4: 15, 5: 30, 6: 15}
    for col_idx, width in column_widths.items():
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    # Freeze header row
    ws.freeze_panes = "A2"

    wb.save(OUTPUT_FINAL_XLSX)
    print(f"Saved: {OUTPUT_FINAL_XLSX}")

    t_end = time.time()
    print("=" * 70)
    print(f"Step 5 execution completed successfully in {t_end - t0:.2f} seconds.")
    print("=" * 70)

if __name__ == "__main__":
    run_step_5_assembly()
