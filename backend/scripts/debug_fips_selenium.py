"""Debug FIPS Selenium flow — saves HTML snapshots."""

import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from app.services.fips_live_service import (  # noqa: E402
    _create_chrome_driver,
    _fetch_with_selenium,
    _parse_results_html,
    _prepare_fips_session,
    _submit_fips_query,
)

OUT = _BACKEND / "_debug_fips"
QUERY = "электрическая зубная щетка"


def main() -> None:
    from selenium.webdriver.support.ui import WebDriverWait

    OUT.mkdir(exist_ok=True)
    driver = _create_chrome_driver()
    wait = WebDriverWait(driver, 35)

    try:
        _prepare_fips_session(driver, wait)
        (OUT / "03_search_form.html").write_text(driver.page_source, encoding="utf-8")
        print("form url", driver.current_url)

        _submit_fips_query(driver, wait, QUERY)
        (OUT / "04_results.html").write_text(driver.page_source, encoding="utf-8")
        print("results url", driver.current_url)

        recs = _parse_results_html(driver.page_source, 25)
        print("parsed", len(recs))
        for r in recs[:5]:
            print(" ", r["patent_number"], r["title"][:60])
    finally:
        driver.quit()

    print("\nFull fetch:")
    all_recs = _fetch_with_selenium(QUERY, 10)
    print("total", len(all_recs))


if __name__ == "__main__":
    main()
