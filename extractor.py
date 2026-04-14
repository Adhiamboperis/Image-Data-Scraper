"""
extractor.py
------------
Handles:
  1. OCR  — Google Cloud Vision API (free tier: 1,000 images / month)
  2. Classification  — keyword matching to identify the company
  3. Field extraction — regex + heuristics per company schema
"""

import os
import re
import base64
import json
from datetime import datetime
from google.cloud import vision


# ── OCR ────────────────────────────────────────────────────────────────────────

def extract_text_from_image(image_bytes: bytes) -> str:
    """Send image bytes to Google Vision OCR and return the full text."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Google Vision error: {response.error.message}")

    return response.full_text_annotation.text


# ── Classification ─────────────────────────────────────────────────────────────

# Keywords that strongly identify each company.
# Add more as you discover them from your real documents.
COMPANY_KEYWORDS = {
    "freightways": [
        "freightways",
        "freight ways",
    ],
    "shuffle": [
        "rolling cargo",
        "rollingcargo",
        "rolling  cargo",   # handle double-space OCR artefacts
    ],
}


def classify_company(text: str) -> str:
    """
    Return 'freightways', 'shuffle', or 'unknown' based on keywords in text.
    Comparison is case-insensitive.
    """
    lower = text.lower()
    for company, keywords in COMPANY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return company
    return "unknown"


# ── Helpers ────────────────────────────────────────────────────────────────────

def clean(value: str) -> str:
    """Strip extra whitespace from an extracted value."""
    return " ".join(value.split()) if value else ""


def find_after_label(text: str, label_pattern: str, max_chars: int = 60) -> str:
    """
    Extract the value that appears on the same line after a label.
    label_pattern is a regex (case-insensitive).
    """
    match = re.search(
        label_pattern + r"[:\s\-]*(.{1," + str(max_chars) + r"})",
        text,
        re.IGNORECASE,
    )
    return clean(match.group(1).split("\n")[0]) if match else ""


def find_date(text: str) -> str:
    """
    Try to find a date in various common formats within text.
    Returns the first match as a string, or '' if none found.
    """
    patterns = [
        r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b",   # 12/03/2024
        r"\b(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",      # 2024-03-12
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",  # 12 Mar 2024
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


# ── Per-company extractors ─────────────────────────────────────────────────────

def extract_freightways(text: str, filename: str) -> dict:
    """
    Fields: Description, Quantity, Date, Total
    """
    description = find_after_label(text, r"description")
    quantity    = find_after_label(text, r"quantity|qty")
    date        = find_after_label(text, r"\bdate\b") or find_date(text)
    total       = find_after_label(text, r"total")

    # Fallback: if total not labelled, look for a currency amount
    if not total:
        m = re.search(r"(KES|KSH|Ksh|USD)?\s*[\d,]+\.\d{2}", text)
        total = m.group(0) if m else ""

    return {
        "filename":    filename,
        "company":     "Freightways",
        "date":        clean(date),
        "description": clean(description),
        "quantity":    clean(quantity),
        "total":       clean(total),
    }


def extract_shuffle(text: str, filename: str) -> dict:
    """
    Fields: WayBill No, Posting Date, Quantity (KGs), Quantity (Pieces)
    """
    waybill      = find_after_label(text, r"waybill\s*(no|number|#)?|way\s*bill")
    posting_date = find_after_label(text, r"posting\s*date|post\s*date") or find_date(text)
    qty_kg       = find_after_label(text, r"quantity.*kg|weight.*kg|kgs?")
    qty_pieces   = find_after_label(text, r"pieces?|pcs?|units?|qty.*pcs")

    # Tighten up numeric fields — keep only the numeric part
    def numeric_only(val: str) -> str:
        m = re.search(r"[\d,]+\.?\d*", val)
        return m.group(0) if m else val

    return {
        "filename":        filename,
        "company":         "Shuffle (Rolling Cargo)",
        "waybill_no":      clean(waybill),
        "posting_date":    clean(posting_date),
        "quantity_kg":     numeric_only(clean(qty_kg)),
        "quantity_pieces": numeric_only(clean(qty_pieces)),
    }


def extract_unknown(text: str, filename: str) -> dict:
    return {
        "filename": filename,
        "company":  "Unknown",
        "raw_text": text[:500],   # first 500 chars for manual review
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def classify_and_extract(text: str, filename: str) -> tuple[str, dict]:
    """
    Returns (company_key, record_dict).
    company_key is one of: 'freightways', 'shuffle', 'unknown'
    """
    company = classify_company(text)

    if company == "freightways":
        return "freightways", extract_freightways(text, filename)
    elif company == "shuffle":
        return "shuffle", extract_shuffle(text, filename)
    else:
        return "unknown", extract_unknown(text, filename)
