from playwright.sync_api import sync_playwright
import os

def html_to_pdf(html_file, output_pdf):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file://" + os.path.abspath(html_file))
        page.pdf(path=output_pdf, print_background=True, format="A4")
        browser.close()

html_to_pdf("sample_report.html", "output.pdf")
