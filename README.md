# Transport Log Extractor — Setup Guide

## What this app does
Upload photos of transport documents → the app reads them using Google Vision OCR,
identifies whether they belong to **Freightways** or **Shuffle (Rolling Cargo)**,
extracts the relevant fields, and lets you export clean CSV or Excel files.

---

## Step 1 — Set up Google Cloud Vision API (free)

Google Vision gives you **1,000 free image reads per month**.

1. Go to https://console.cloud.google.com
2. Create a new project (e.g. "transport-logs")
3. Search for "Cloud Vision API" and click **Enable**
4. Go to **IAM & Admin → Service Accounts**
5. Click **Create Service Account** → give it any name → click Done
6. Click the service account → go to **Keys** tab → Add Key → JSON
7. A `.json` file will download — save it somewhere safe on your PC
8. Set an environment variable pointing to that file:

   **Windows (PowerShell):**
   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your-key.json"
   ```

   **Mac / Linux:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-key.json"
   ```

   Tip: add this line to your `.bashrc` or `.zshrc` so you don't have to
   run it every time.

---

## Step 2 — Install Python dependencies

Make sure you have Python 3.10+ installed. Then run:

```bash
pip install -r requirements.txt
```

---

## Step 3 — Run the app

```bash
streamlit run app.py
```

Your browser will open automatically at http://localhost:8501

---

## How to use it

1. Click **Browse files** and select one or more document photos
2. Click **Process images**
3. Results appear in two tabs — Freightways and Shuffle
4. Download as CSV (one per company) or a combined Excel file with two sheets

---

## Improving extraction accuracy

The app uses keyword matching + regex to extract fields. If some fields come
back empty or wrong, open `extractor.py` and adjust:

- `COMPANY_KEYWORDS` — add more keywords that appear on your documents
- `extract_freightways()` — tweak the label patterns to match your exact documents
- `extract_shuffle()` — same

The labels in `find_after_label()` are regex patterns, so you can add
alternatives with `|`. For example:
```python
find_after_label(text, r"total|grand total|amount due")
```

---

## File structure

```
transport_logs/
├── app.py            # Streamlit UI
├── extractor.py      # OCR + classification + field extraction
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## Adding the third company (Nippon) later

In `extractor.py`:
1. Add Nippon keywords to `COMPANY_KEYWORDS`
2. Write an `extract_nippon()` function with its fields
3. Add an `elif company == "nippon"` branch in `classify_and_extract()`
4. Add a new tab in `app.py`
