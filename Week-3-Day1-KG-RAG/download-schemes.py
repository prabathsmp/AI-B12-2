"""
Download the first N Agriculture - Farmers Welfare scheme pages from
the Government of Tamil Nadu scheme listing and save each as a PDF.

Install:
    pip install playwright
    playwright install chromium

Run:
    python download_tn_gov_schemes.py --target 10 --headed

Output:
    tn_gov_scheme_pdfs/*.pdf
    tn_gov_scheme_pdfs/download_report.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

START_URL = "https://www.tn.gov.in/scheme_list.php?dep_id=Mg=="
OUTPUT_DIR = Path("tn_gov_scheme_pdfs")
REPORT_FILE = OUTPUT_DIR / "download_report.csv"


def slugify(value: str, max_len: int = 90) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value[:max_len].rstrip("_") or "scheme"


async def collect_scheme_links(page) -> list[dict[str, str]]:
    """Collect scheme detail links from the Agriculture department listing."""
    return await page.locator("a[href*='scheme_details.php']").evaluate_all(r"""
        anchors => {
            const seen = new Set();
            return anchors.map(a => ({
                name: (a.innerText || a.textContent || '').trim(),
                href: a.href
            })).filter(x => {
                if (!x.name || !x.href || seen.has(x.href)) return false;
                seen.add(x.href);
                return true;
            });
        }
    """)


async def render_scheme_pdf(browser, url: str, output_path: Path) -> str:
    """Open a scheme detail page and print the rendered page to PDF."""
    page = await browser.new_page(
        locale="en-IN",
        viewport={"width": 1440, "height": 1000},
    )
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        await page.wait_for_timeout(1000)

        # The Tamil Nadu site can display an accessibility toolbar/panel over
        # the page. Close it when possible, then suppress accessibility/floating
        # overlays in the printed output so they do not cover scheme content.
        for selector in (
            "button[aria-label*='close' i]",
            "button[title*='close' i]",
            "[role='button'][aria-label*='close' i]",
            "[aria-label*='close accessibility' i]",
            "[title*='close accessibility' i]",
        ):
            try:
                candidate = page.locator(selector).first
                if await candidate.is_visible(timeout=300):
                    await candidate.click(timeout=700)
                    await page.wait_for_timeout(250)
            except Exception:
                pass

        # Ensure a desktop layout before printing, even if the site remembers
        # a narrow/mobile viewport or has an accessibility panel open.
        await page.set_viewport_size({"width": 1440, "height": 1100})
        await page.add_style_tag(content=r"""
            @media print {
              html, body { width: 100% !important; max-width: 100% !important; }
              body { overflow: visible !important; }
            }
            [id*="accessibility" i], [class*="accessibility" i],
            [id*="accessibe" i], [class*="accessibe" i],
            iframe[title*="accessibility" i], iframe[src*="accessibility" i],
            iframe[src*="accessibe" i],
            .userway, #userway, [data-userway],
            [id*="a11y" i], [class*="a11y" i] {
              display: none !important; visibility: hidden !important;
            }
            /* Hide floating/fixed overlays (toolbar bubbles, panels, chat widgets)
               without changing the normal document flow. */
            @media print {
              body * { }
            }
        """)

        # Some versions render the accessibility panel in an iframe or a
        # generic container whose class/id does not mention accessibility.
        # Locate the visible panel by its heading and hide its fixed-position
        # ancestor for printing.
        await page.evaluate(r"""() => {
          const candidates = Array.from(document.querySelectorAll('body *'));
          for (const el of candidates) {
            const label = `${el.innerText || ''} ${el.getAttribute('aria-label') || ''}`
              .replace(/\s+/g, ' ').trim().toLowerCase();
            if (!label || label.length > 160) continue;
            if (label.includes('accessibility menu')) {
              let node = el;
              for (let i = 0; node && i < 6; i++, node = node.parentElement) {
                const style = getComputedStyle(node);
                const rect = node.getBoundingClientRect();
                if (style.position === 'fixed' ||
                    (rect.width > 180 && rect.height > 250 && style.zIndex !== 'auto')) {
                  node.dataset.hideForPdf = 'true';
                  node.style.setProperty('display', 'none', 'important');
                  break;
                }
              }
            }
          }
        }""")
        await page.add_style_tag(content=r"""
            @media print {
              [data-hide-for-pdf="true"] { display: none !important; }
              html, body { width: 100% !important; max-width: 100% !important; }
              body { overflow: visible !important; }
            }
        """)

        if response and response.status >= 400:
            raise RuntimeError(f"HTTP {response.status} while opening {url}")

        # If the detail page redirects to a PDF, the browser may not expose
        # printable HTML. In that case, report the issue rather than creating
        # a misleading PDF from the listing page.
        content_type = ""
        if response:
            content_type = response.headers.get("content-type", "").lower()
        if "application/pdf" in content_type:
            raise RuntimeError(
                "The detail link returned a PDF directly. Use the original PDF URL "
                "instead of printing this page."
            )

        title = (await page.title()).strip()
        body_text = (await page.locator("body").inner_text()).strip()
        if not body_text:
            raise RuntimeError("The scheme detail page had no readable body text.")

        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            scale=0.9,
            display_header_footer=True,
            header_template=(
                '<div style="font-size:8px;width:100%;padding:0 12mm;color:#666;">'
                'Government of Tamil Nadu — Schemes</div>'
            ),
            footer_template=(
                '<div style="font-size:8px;width:100%;padding:0 12mm;'
                'display:flex;justify-content:space-between;color:#666;">'
                f'<span>{url}</span><span>Page <span class="pageNumber"></span>'
                ' of <span class="totalPages"></span></span></div>'
            ),
            margin={"top": "18mm", "bottom": "20mm", "left": "13mm", "right": "13mm"},
        )
        return title or "Scheme detail page"
    finally:
        await page.close()


async def main(target: int, headless: bool) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_rows: list[dict[str, str]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            accept_downloads=True,
            locale="en-IN",
            viewport={"width": 1440, "height": 1000},
        )
        page = await context.new_page()

        print(f"Opening scheme listing: {START_URL}")
        await page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except PlaywrightTimeoutError:
            pass
        await page.wait_for_timeout(1000)

        links = await collect_scheme_links(page)
        if not links:
            # Fallback for pages whose scheme links use a relative or alternate
            # detail URL pattern. Keep only anchors in the main content area.
            links = await page.locator("main a, #content a, .content a, body a").evaluate_all(r"""
                anchors => {
                    const seen = new Set();
                    return anchors.map(a => ({
                        name: (a.innerText || a.textContent || '').trim(),
                        href: a.href
                    })).filter(x => {
                        if (!x.name || !x.href ||
                            !/scheme_details\.php/i.test(x.href) ||
                            seen.has(x.href)) return false;
                        seen.add(x.href);
                        return true;
                    });
                }
            """)

        print(f"Found {len(links)} scheme detail links.")
        if not links:
            print("Could not find links matching scheme_details.php.")
            print("Inspect the current page HTML and update collect_scheme_links().")
            await browser.close()
            return

        for index, item in enumerate(links[:target], start=1):
            name = item["name"]
            detail_url = urljoin(START_URL, item["href"])
            output_path = OUTPUT_DIR / f"{index:02d}_{slugify(name)}.pdf"
            print(f"[{index}/{min(target, len(links))}] {name}")
            try:
                page_title = await render_scheme_pdf(browser, detail_url, output_path)
                status = "success"
                output = str(output_path.resolve())
                print(f"    Saved: {output_path}")
            except Exception as exc:
                status = "failed"
                output = str(exc)
                page_title = ""
                print(f"    FAILED: {exc}")

            report_rows.append({
                "scheme_name": name,
                "detail_url": detail_url,
                "page_title": page_title,
                "status": status,
                "output_or_error": output,
            })
            await asyncio.sleep(0.5)

        with REPORT_FILE.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "scheme_name", "detail_url", "page_title",
                    "status", "output_or_error",
                ],
            )
            writer.writeheader()
            writer.writerows(report_rows)

        successes = sum(row["status"] == "success" for row in report_rows)
        print(f"\nFinished: {successes}/{len(report_rows)} PDFs created.")
        print(f"PDF directory: {OUTPUT_DIR.resolve()}")
        print(f"CSV report: {REPORT_FILE.resolve()}")
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Save Government of Tamil Nadu scheme detail pages as PDFs."
    )
    parser.add_argument("--target", type=int, default=10, help="Number of scheme pages to save")
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    args = parser.parse_args()
    if args.target < 1:
        parser.error("--target must be at least 1")
    asyncio.run(main(args.target, headless=not args.headed))
