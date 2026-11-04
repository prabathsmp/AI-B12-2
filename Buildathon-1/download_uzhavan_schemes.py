"""
Download at least N scheme records from the official Tamil Nadu Uzhavan portal
and create one searchable PDF per scheme.

Install:
    pip install -r requirements_playwright.txt
    playwright install chromium

Run:
    python download_uzhavan_schemes.py --target 30 --headed

Output:
    uzhavan_scheme_pdfs/*.pdf
    uzhavan_scheme_pdfs/download_report.csv

The portal's scheme names use onclick="getSchemeDet(ID)". This script captures
the listing-row fields and the JSON returned by the portal's official AJAX
endpoint, then writes both into a readable PDF. The PDFs are generated from
extracted page text/data; they are not represented as official Government Orders.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import html
import re
import unicodedata
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

START_URL = "https://www.tnagrisnet.tn.gov.in/people_app/GoScheme"
OUTPUT_DIR = Path("uzhavan_scheme_pdfs")
REPORT_FILE = OUTPUT_DIR / "download_report.csv"
PAGE_SIZE = 50


def slugify(text: str, max_len: int = 85) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text[:max_len].rstrip("_") or "scheme"


async def choose_50_entries(page) -> bool:
    selects = page.locator("select")
    for i in range(await selects.count()):
        select = selects.nth(i)
        try:
            options = await select.locator("option").evaluate_all(
                "(opts) => opts.map(o => ({text: (o.textContent || '').trim(), value: o.value}))"
            )
            match = next(
                (opt for opt in options if opt["text"] == "50" or opt["value"] == "50"),
                None,
            )
            if match:
                await select.select_option(value=match["value"])
                await page.wait_for_timeout(1000)
                return True
        except Exception:
            pass
    return False


async def extract_scheme_ids(page) -> list[dict[str, Any]]:
    """Read visible scheme rows and their onclick IDs from the current page."""
    return await page.locator("table tbody tr").evaluate_all(r"""
        rows => rows.map(row => {
            const cells = Array.from(row.querySelectorAll('td'))
                .map(td => (td.innerText || td.textContent || '').trim());
            const link = row.querySelector('a[onclick*="getSchemeDet"]');
            const onclick = link ? (link.getAttribute('onclick') || '') : '';
            const match = onclick.match(/getSchemeDet\s*\(\s*(\d+)\s*\)/);
            return {
                row_number: cells[0] || '',
                department: cells[1] || '',
                name: link ? (link.innerText || link.textContent || '').trim() : '',
                description: cells[3] || '',
                beneficiaries: cells[4] || '',
                required_documents: cells[5] || '',
                go_guidelines: cells[6] || '',
                scheme_id: match ? Number(match[1]) : null
            };
        }).filter(item => item.name && item.scheme_id !== null)
    """)


async def fetch_scheme_details(page, scheme_id: int) -> list[dict[str, Any]]:
    """Invoke getSchemeDet and capture its POST response JSON."""
    fragment = f"/people_app/goScheme/getSchemeDet/{scheme_id}"
    async with page.expect_response(
        lambda response: (
            fragment in response.url and response.request.method.upper() == "POST"
        ),
        timeout=20000,
    ) as response_info:
        await page.evaluate("(id) => window.getSchemeDet(id)", scheme_id)

    response = await response_info.value
    if not response.ok:
        raise RuntimeError(f"Scheme endpoint returned HTTP {response.status}: {response.url}")

    data = await response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Preserve unexpected but valid JSON instead of silently discarding it.
        return [data]
    return [{"response": str(data)}]


def text_or_blank(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_scheme_html(scheme: dict[str, Any], details: list[dict[str, Any]]) -> str:
    def esc(value: Any) -> str:
        return html.escape(text_or_blank(value)).replace("\n", "<br>")

    detail_rows = []
    for item in details:
        detail_rows.append(
            "<tr>"
            f"<td>{esc(item.get('input_type_name'))}<br><span class='ta'>{esc(item.get('input_type_name_tamil'))}</span></td>"
            f"<td>{esc(item.get('class_Name') or item.get('class_name'))}<br><span class='ta'>{esc(item.get('class_name_Tamil'))}</span></td>"
            f"<td>{esc(item.get('pattern_of_subsidy'))}<br><span class='ta'>{esc(item.get('pattern_of_subsidy_tamil'))}</span></td>"
            "</tr>"
        )

    if not detail_rows:
        detail_rows.append(
            '<tr><td colspan="3">No component/subsidy details were returned by the portal.</td></tr>'
        )

    source_url = f"{START_URL} (scheme ID: {scheme['scheme_id']})"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4; margin: 16mm 13mm; }}
body {{ font-family: Arial, "Noto Sans Tamil", sans-serif; color: #222; font-size: 10.5pt; line-height: 1.45; }}
h1 {{ font-size: 19pt; margin: 0 0 4px; }}
h2 {{ font-size: 13pt; margin: 20px 0 8px; border-bottom: 1px solid #999; padding-bottom: 4px; }}
.sub {{ color: #555; font-size: 9pt; margin-bottom: 16px; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
th, td {{ border: 1px solid #999; padding: 7px; vertical-align: top; overflow-wrap: anywhere; }}
th {{ background: #f0f0f0; text-align: left; }}
.meta th {{ width: 29%; }}
.ta {{ color: #444; }}
.note {{ margin-top: 18px; font-size: 8.5pt; color: #555; }}
tr {{ page-break-inside: avoid; }}
</style>
</head>
<body>
<h1>{esc(scheme.get('name'))}</h1>
<div class="sub">Tamil Nadu Uzhavan portal · Scheme ID: {esc(scheme.get('scheme_id'))}</div>

<h2>Scheme listing information</h2>
<table class="meta">
<tr><th>Department</th><td>{esc(scheme.get('department'))}</td></tr>
<tr><th>Description</th><td>{esc(scheme.get('description'))}</td></tr>
<tr><th>Eligible beneficiaries</th><td>{esc(scheme.get('beneficiaries'))}</td></tr>
<tr><th>Required documents</th><td>{esc(scheme.get('required_documents'))}</td></tr>
<tr><th>GO / Guidelines status</th><td>{esc(scheme.get('go_guidelines'))}</td></tr>
</table>

<h2>Components and subsidy information returned by the portal</h2>
<table>
<thead><tr><th>Input type</th><th>Component</th><th>Pattern of subsidy</th></tr></thead>
<tbody>{''.join(detail_rows)}</tbody>
</table>

<div class="note">
Source: {esc(source_url)}<br>
Generated from information displayed/returned by the Uzhavan portal. This PDF is a
reference extract, not an official Government Order. Verify scheme availability,
current eligibility, subsidy rates and application procedures with the relevant
department before relying on them. Empty fields indicate that the portal did not
provide a value in the captured response.
</div>
</body>
</html>"""


async def write_pdf(browser, scheme: dict[str, Any], details: list[dict[str, Any]], number: int) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{number:03d}_{slugify(scheme['name'])}.pdf"
    pdf_page = await browser.new_page()
    try:
        document_html = build_scheme_html(scheme, details)
        await pdf_page.set_content(document_html, wait_until="load")
        await pdf_page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
    finally:
        await pdf_page.close()
    return output_path


async def main(target: int, headless: bool) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_rows: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    successful = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            accept_downloads=True,
            locale="en-IN",
            viewport={"width": 1440, "height": 1000},
        )
        page = await context.new_page()

        print(f"Opening {START_URL}")
        await page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)

        selected_50 = await choose_50_entries(page)
        print("Selected 50 entries." if selected_50 else
              "WARNING: Could not select 50 entries; will process rows available.")

        # The portal uses DataTables; extract up to 50 records from each page.
        while successful < target:
            current_schemes = await extract_scheme_ids(page)
            new_schemes = [
                item for item in current_schemes
                if item["scheme_id"] not in seen_ids
            ]
            print(
                f"Page yielded {len(current_schemes)} schemes; "
                f"{len(new_schemes)} not yet processed."
            )

            for scheme in new_schemes:
                if successful >= target:
                    break
                scheme_id = scheme["scheme_id"]
                seen_ids.add(scheme_id)
                print(
                    f"[{successful + 1}/{target}] "
                    f"{scheme['name']} (ID {scheme_id})"
                )

                try:
                    details = await fetch_scheme_details(page, scheme_id)
                    pdf_path = await write_pdf(
                        browser, scheme, details, successful + 1
                    )
                    successful += 1
                    status = "success"
                    output_or_error = str(pdf_path.resolve())
                    print(f"    Saved: {pdf_path}")
                except Exception as exc:
                    status = "failed"
                    output_or_error = str(exc)
                    print(f"    FAILED: {exc}")

                report_rows.append({
                    "scheme_id": scheme_id,
                    "scheme": scheme["name"],
                    "department": scheme["department"],
                    "source_url": f"{START_URL} (scheme ID: {scheme_id})",
                    "status": status,
                    "output_or_error": output_or_error,
                })

                await page.wait_for_timeout(350)

            if successful >= target:
                break

            # Move to the next DataTables page. Try common selectors.
            next_button = page.locator(
                "#DataTables_Table_0_next, "
                "li.paginate_button.next:not(.disabled) a, "
                "a[aria-label='Next'], button[aria-label='Next']"
            ).first
            try:
                if not await next_button.is_visible(timeout=1500):
                    print("No visible Next button; reached the end of the listing.")
                    break

                parent_class = (
                    await next_button.locator("xpath=..").get_attribute("class") or ""
                ).lower()
                own_class = (await next_button.get_attribute("class") or "").lower()
                if "disabled" in parent_class or "disabled" in own_class:
                    print("Next button is disabled; reached the end of the listing.")
                    break

                await next_button.click(timeout=5000)
                await page.wait_for_timeout(900)
            except PlaywrightTimeoutError:
                print("Could not navigate to the next table page.")
                break

        report_path = REPORT_FILE
        with report_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "scheme_id", "scheme", "department", "source_url",
                    "status", "output_or_error",
                ],
            )
            writer.writeheader()
            writer.writerows(report_rows)

        print(f"\nFinished: {successful} successful PDFs (target: {target}).")
        print(f"PDF directory: {OUTPUT_DIR.resolve()}")
        print(f"CSV report: {report_path.resolve()}")
        if successful < target:
            print(
                "The portal yielded fewer successful records than requested. "
                "Review download_report.csv for endpoint or navigation errors."
            )
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create PDFs from Uzhavan scheme listing and AJAX detail data."
    )
    parser.add_argument("--target", type=int, default=30)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    if args.target < 1:
        parser.error("--target must be at least 1")
    asyncio.run(main(args.target, headless=not args.headed))
