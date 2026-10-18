import csv
import sys
import time
import ijson

JSON_PATH = "index files/healthnet_ca_in_network.json"
PROV_CSV_PATH = "healthnet_csv/provider_references.csv"
IN_NET_CSV_PATH = "healthnet_csv/in_network.csv"

def extract_provider_references():
    print("Starting extraction of provider_references...")
    t0 = time.time()
    count_refs = 0
    count_rows = 0

    with open(JSON_PATH, "rb") as f_in, open(PROV_CSV_PATH, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "provider_group_id",
            "network_name",
            "tin_type",
            "tin_value",
            "business_name",
            "npi"
        ])

        items = ijson.items(f_in, "provider_references.item")
        for ref in items:
            count_refs += 1
            pg_id = ref.get("provider_group_id")
            net_name_raw = ref.get("network_name", [])
            if isinstance(net_name_raw, list):
                net_name = "|".join(str(x) for x in net_name_raw)
            else:
                net_name = str(net_name_raw) if net_name_raw is not None else ""

            p_groups = ref.get("provider_groups", [])
            if not p_groups:
                writer.writerow([pg_id, net_name, "", "", "", ""])
                count_rows += 1
                continue

            for pg in p_groups:
                tin = pg.get("tin", {})
                tin_type = tin.get("type", "")
                tin_val = tin.get("value", "")
                biz_name = tin.get("business_name", "")
                npis = pg.get("npi", [])

                if not npis:
                    writer.writerow([pg_id, net_name, tin_type, tin_val, biz_name, ""])
                    count_rows += 1
                else:
                    for npi in npis:
                        writer.writerow([pg_id, net_name, tin_type, tin_val, biz_name, npi])
                        count_rows += 1

    t1 = time.time()
    print(f"Extracted {count_refs} provider reference items into {count_rows} CSV rows in {t1 - t0:.2f}s.")

def extract_in_network():
    print("Starting extraction of in_network...")
    t0 = time.time()
    count_items = 0
    count_rows = 0

    with open(JSON_PATH, "rb") as f_in, open(IN_NET_CSV_PATH, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "billing_code",
            "billing_code_type",
            "billing_code_type_version",
            "name",
            "description",
            "negotiation_arrangement",
            "negotiated_type",
            "negotiated_rate",
            "expiration_date",
            "service_code",
            "billing_class",
            "setting",
            "billing_code_modifier",
            "additional_information",
            "provider_group_id"
        ])

        items = ijson.items(f_in, "in_network.item")
        for item in items:
            count_items += 1
            b_code = item.get("billing_code", "")
            b_type = item.get("billing_code_type", "")
            b_ver = item.get("billing_code_type_version", "")
            b_name = item.get("name", "")
            b_desc = item.get("description", "")
            b_arr = item.get("negotiation_arrangement", "")

            for rate in item.get("negotiated_rates", []):
                prov_refs = rate.get("provider_references", [])
                if not prov_refs:
                    prov_refs = [None]

                for price in rate.get("negotiated_prices", []):
                    n_type = price.get("negotiated_type", "")
                    n_rate = price.get("negotiated_rate", "")
                    exp_date = price.get("expiration_date", "")
                    
                    sc = price.get("service_code")
                    if isinstance(sc, list):
                        sc_str = "|".join(str(x) for x in sc)
                    else:
                        sc_str = str(sc) if sc is not None else ""

                    b_class = price.get("billing_class", "")
                    setting = price.get("setting", "")

                    mod = price.get("billing_code_modifier")
                    if isinstance(mod, list):
                        mod_str = "|".join(str(x) for x in mod)
                    else:
                        mod_str = str(mod) if mod is not None else ""

                    add_info = price.get("additional_information", "")

                    for p_ref in prov_refs:
                        writer.writerow([
                            b_code,
                            b_type,
                            b_ver,
                            b_name,
                            b_desc,
                            b_arr,
                            n_type,
                            n_rate,
                            exp_date,
                            sc_str,
                            b_class,
                            setting,
                            mod_str,
                            add_info,
                            p_ref if p_ref is not None else ""
                        ])
                        count_rows += 1

            if count_items % 250 == 0:
                print(f"Processed {count_items} billing code items ({count_rows} rate rows so far)...")

    t1 = time.time()
    print(f"Extracted {count_items} in_network items into {count_rows} CSV rows in {t1 - t0:.2f}s.")

if __name__ == "__main__":
    extract_provider_references()
    extract_in_network()
