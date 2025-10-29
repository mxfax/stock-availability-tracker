"""
Stock Availability Tracker
--------------------------
This script checks the stock status of products listed by SKU from a text file using web scraping.
It compares current stock availability with a previous record and generates a change report.
Note: This script assumes the target website supports searching by SKU (e.g., via 'search.php?search_query={sku}'). Ensure your chosen site allows this before use.
Dependencies: requests, BeautifulSoup (bs4)
"""

import os
import datetime # To add timestamp to output
import requests
from bs4 import BeautifulSoup

# --- Configuration ---
BASE_DIR = "your_project_directory_here"
BASE_URL = "https://example-store.com"
SKU_FILE_PATH = os.path.join(BASE_DIR, "SKUs.txt")
CURRENT_OOS_FILE_PATH = os.path.join(BASE_DIR, "out_stock.txt")
PREVIOUS_OOS_FILE_PATH = os.path.join(BASE_DIR, "previous_out_stock.txt")
CHANGE_REPORT_FILE_PATH = os.path.join(BASE_DIR, "stock_change_report.txt") # New file for the report
WRITE_CHANGE_REPORT_FILE = True # Set to False to disable writing the report file
WAIT_TIMEOUT = 15
# --- End Configuration ---

# --- Data Structures ---
previous_oos_data = {} # Store previous OOS as {sku: url}
current_oos_products = [] # Stores current OOS as list of {'sku': sku, 'url': url}
current_instock_skus = set() # Stores current in-stock SKUs
analysis_report_lines = [] # Lines for the unified report

# --- Get Current Time ---
run_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"--- Stock Check Run Started: {run_timestamp} ---")


# 1. Read Previous Out-of-Stock File (including URLs)
try:
    # Ensure previous file is read before potential overwrite/rename
    with open(PREVIOUS_OOS_FILE_PATH, mode="r") as prev_file:
        print(f"Reading previous out-of-stock file: {PREVIOUS_OOS_FILE_PATH}")
        for line in prev_file:
            line = line.strip()
            if line:
                parts = line.split(maxsplit=1)
                sku = parts[0]
                url = parts[1] if len(parts) > 1 else "N/A"
                # Basic validation: Skip if SKU looks like an error message remnant
                if not sku.endswith(")") or "(Error:" not in sku:
                    previous_oos_data[sku] = url
    print(f"Loaded {len(previous_oos_data)} SKUs from previous run.")
except FileNotFoundError:
    print(f"Previous out-of-stock file not found at {PREVIOUS_OOS_FILE_PATH}. Assuming first run.")
except Exception as e:
    print(f"Error reading previous out-of-stock file: {e}")

# 2. Read Current SKUs to Check
try:
    with open(SKU_FILE_PATH, mode="r") as product_skus_file:
        products_to_check = product_skus_file.readlines()
except FileNotFoundError:
    print(f"Error: SKU file not found at {SKU_FILE_PATH}")
    exit()


# 3. Main Checking Loop (Using BeautifulSoup)
headers = {'User-Agent': 'Mozilla/5.0'}

print(f"\nStarting stock check for {len(products_to_check)} SKUs...")

for product_line in products_to_check:
    sku = product_line.strip()
    if not sku:
        continue

    search_url = f"{BASE_URL}/search.php?search_query={sku}"
    product_url = search_url
    print(f"Checking SKU: {sku}")

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try to locate product link if redirected from search
        product_links = soup.select('a.product-title')
        if product_links:
            product_url = product_links[0].get('href')
            if not product_url.startswith('http'):
                product_url = BASE_URL + product_url
            # Follow the product page
            prod_response = requests.get(product_url, headers=headers, timeout=10)
            prod_response.raise_for_status()
            prod_soup = BeautifulSoup(prod_response.text, 'html.parser')
        else:
            prod_soup = soup  # Fallback to current soup if direct page

        qty_select = prod_soup.select_one('.ProductQty select')
        if qty_select:
            options_elements = qty_select.find_all('option')
            values = [opt.get('value') for opt in options_elements]
            has_stock = any(val and val.isdigit() and int(val) > 0 for val in values)
        else:
            has_stock = False

        if has_stock:
            current_instock_skus.add(sku)
        else:
            current_oos_products.append({'sku': sku, 'url': product_url})

    except Exception as e:
        print(f"  -> [{sku}] -> ERROR during processing: {e}")
        current_oos_products.append({'sku': f"{sku} (Error: {type(e).__name__})", 'url': product_url})

# 5. No browser to close with BeautifulSoup/requests

# 6. Analyze Results - Generate Unified Report
print("\n--- Stock Status Analysis ---")

# Create helper structures for analysis
current_oos_dict = {item['sku']: item['url'] for item in current_oos_products if not item['sku'].endswith(")")} # Exclude error SKUs
current_oos_skus_set = set(current_oos_dict.keys())
previous_oos_skus_set = set(previous_oos_data.keys())

# Identify all unique SKUs involved in OOS status (past or present)
all_relevant_skus = previous_oos_skus_set | current_oos_skus_set # Union of both sets

analysis_report_lines.append(f"Analysis Report - {run_timestamp}")
analysis_report_lines.append("="*30)

summary = {"RESTOCKED": 0, "STILL_OOS": 0, "NEWLY_OOS": 0, "ERROR_PREV_OOS": 0}

if not all_relevant_skus:
    analysis_report_lines.append("No out-of-stock items found previously or currently.")
else:
    # Sort SKUs for consistent report order
    for sku in sorted(list(all_relevant_skus)):
        in_previous = sku in previous_oos_skus_set
        in_current_oos = sku in current_oos_skus_set
        in_current_instock = sku in current_instock_skus

        status_line = None
        if in_previous and in_current_instock:
            status = "[+] RESTOCKED"
            prev_url = previous_oos_data.get(sku, 'N/A')
            status_line = f"{status:<15}: {sku} (Was OOS: {prev_url})"
            summary["RESTOCKED"] += 1
        elif in_previous and in_current_oos:
            status = "[-] STILL OOS"
            curr_url = current_oos_dict.get(sku, 'N/A')
            status_line = f"{status:<15}: {sku} (Link: {curr_url})"
            summary["STILL_OOS"] += 1
        elif not in_previous and in_current_oos:
            status = "[!] NEWLY OOS"
            curr_url = current_oos_dict.get(sku, 'N/A')
            status_line = f"{status:<15}: {sku} (Link: {curr_url})"
            summary["NEWLY_OOS"] += 1
        elif in_previous and not in_current_oos and not in_current_instock:
            # Was OOS, but not found OOS or In Stock now (implies check error?)
            status = "[E] ERROR"
            prev_url = previous_oos_data.get(sku, 'N/A')
            status_line = f"{status:<15}: {sku} (Was OOS: {prev_url}) - Current status unknown (check error?)"
            summary["ERROR_PREV_OOS"] += 1
        # Ignore cases: Not previously OOS and now In Stock, or error items not previously OOS

        if status_line:
            analysis_report_lines.append(status_line)

    analysis_report_lines.append("="*30)
    analysis_report_lines.append("Summary:")
    analysis_report_lines.append(f"  Restocked:        {summary['RESTOCKED']}")
    analysis_report_lines.append(f"  Still OutOfStock: {summary['STILL_OOS']}")
    analysis_report_lines.append(f"  Newly OutOfStock: {summary['NEWLY_OOS']}")
    if summary['ERROR_PREV_OOS'] > 0:
        analysis_report_lines.append(f"  Errors (Prev OOS):{summary['ERROR_PREV_OOS']}")
    analysis_report_lines.append(f"  Total Currently OOS (incl errors): {len(current_oos_products)}")

# --- Print Unified Report to Console ---
for line in analysis_report_lines:
    print(line)

# 7. Update Output Files
print("\nUpdating output files...")

# --- Rotate Files ---
try:
    os.replace(CURRENT_OOS_FILE_PATH, PREVIOUS_OOS_FILE_PATH)
    print(f"Moved previous results '{os.path.basename(CURRENT_OOS_FILE_PATH)}' -> '{os.path.basename(PREVIOUS_OOS_FILE_PATH)}'")
except FileNotFoundError:
    print(f"No existing '{os.path.basename(CURRENT_OOS_FILE_PATH)}' file found to move.")
except Exception as e:
    print(f"Error moving file: {e}")

# --- Write Current OOS File (Sorted) ---
try:
    with open(CURRENT_OOS_FILE_PATH, mode="w") as out_stock_file:
        print(f"Writing {len(current_oos_products)} currently out-of-stock items to {CURRENT_OOS_FILE_PATH}")
        # Sort by SKU before writing for consistent output
        current_oos_products.sort(key=lambda x: x['sku'])
        for item in current_oos_products:
            out_stock_file.write(f"{item['sku']}\t{item['url']}\n")
    print(f"'{os.path.basename(CURRENT_OOS_FILE_PATH)}' updated successfully (sorted by SKU).")
except IOError as e:
    print(f"Error: Could not write to output file {CURRENT_OOS_FILE_PATH}: {e}")

# --- (Optional) Write Change Report File ---
if WRITE_CHANGE_REPORT_FILE:
    try:
        with open(CHANGE_REPORT_FILE_PATH, mode="w") as report_file:
            print(f"Writing analysis report to {CHANGE_REPORT_FILE_PATH}")
            for line in analysis_report_lines:
                report_file.write(line + "\n")
        print("Change report file written successfully.")
    except IOError as e:
        print(f"Error: Could not write change report file {CHANGE_REPORT_FILE_PATH}: {e}")


print(f"\n--- Stock Check Run Finished: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
