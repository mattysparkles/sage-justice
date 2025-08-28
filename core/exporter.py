from __future__ import annotations

"""Tools for exporting post logs into various formats."""

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from .logger import logger
from .report_generator import _load_rows

try:  # Optional dependency
    from fpdf import FPDF  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    FPDF = None

OUTPUT_DIR = Path("reports")


def export_reviews(start: Optional[datetime], end: Optional[datetime], formats: Iterable[str]) -> List[Path]:
    """Export post log entries for the given range into selected *formats*."""
    rows = _load_rows(start, end)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    generated: List[Path] = []

    if "csv" in formats:
        csv_path = OUTPUT_DIR / f"report_{timestamp}.csv"
        if rows:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        else:
            csv_path.touch()
        generated.append(csv_path)
        logger.info("CSV report written to %s", csv_path)

    if "json" in formats:
        json_path = OUTPUT_DIR / f"report_{timestamp}.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, default=str)
        generated.append(json_path)
        logger.info("JSON report written to %s", json_path)

    if "pdf" in formats:
        if FPDF is None:
            logger.error("FPDF library not available; skipping PDF export")
        else:
            pdf_path = OUTPUT_DIR / f"report_{timestamp}.pdf"
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            grouped = defaultdict(list)
            for r in rows:
                grouped[r.get("site", "unknown")].append(r)
            for site, site_rows in grouped.items():
                pdf.set_font("Helvetica", style="B", size=14)
                pdf.cell(0, 10, site, ln=True)
                pdf.set_font("Helvetica", size=10)
                for r in site_rows:
                    ts = r["timestamp"].isoformat() if isinstance(r["timestamp"], datetime) else str(r["timestamp"])
                    text = r.get("review", "")
                    pdf.multi_cell(0, 5, f"{ts}: {text}")
                    pdf.ln(1)
                pdf.ln(2)
            pdf.output(str(pdf_path))
            generated.append(pdf_path)
            logger.info("PDF report written to %s", pdf_path)

    return generated

__all__ = ["export_reviews"]
