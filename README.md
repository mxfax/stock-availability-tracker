# Stock Availability Tracker

This Python script automates product stock tracking for an e-commerce website.  
It scrapes product pages by SKU, checks stock status, and compares the current results with previous runs to detect changes such as **restocked**, **newly out of stock**, or **still out of stock** items.

## Features
- Reads product SKUs from a text file  
- Checks stock availability using **requests** and **BeautifulSoup**  
- Generates a detailed stock change report  
- Keeps historical data between runs  

## Requirements
```bash
pip install requests beautifulsoup4
```

## Usage
1. Place your SKUs in a text file named `SKUs.txt`.
2. Update the `BASE_URL` variable in the script to match your target website.
3. Run the script:
   ```bash
   python StockCheck_Soup.py
   ```
4. Review results in:
   - `out_stock.txt` — current out-of-stock items  
   - `stock_change_report.txt` — summary of changes  

## Notes
- This script assumes the target website supports searching by SKU (e.g., via 'search.php?search_query={sku}'). Ensure your chosen site allows this before use.
- Designed for educational and portfolio purposes.  
- Be respectful when scraping websites — follow robots.txt and rate limits.
