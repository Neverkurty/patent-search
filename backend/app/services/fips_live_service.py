"""
Live patent fetch from FIPS IISS (https://www1.fips.ru/iiss/).

Uses Selenium when available; results are cached in memory to limit load on FIPS.
"""

from __future__ import annotations

import logging
import random
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from app.core.config import get_settings

logger = logging.getLogger(__name__)

FIPS_DB_URL = "https://www1.fips.ru/iiss/db.xhtml"
INVENTION_DB_CHECKBOX = "db-selection-form:dbsGrid1:0:dbsGrid1checkbox"
SIDEBAR_SEARCH = "sidebarForm:searchLink"

_PATENT_NUM_RE = re.compile(
    r"\b(RU\s?[\d\s]{6,15}[A-Z]?\d?(?:/\d+)?)\b",
    re.IGNORECASE,
)
# Compact numbers in links: RU2020123456, 2020123456/A1
_PATENT_COMPACT_RE = re.compile(
    r"\b(RU\d{6,12}[A-Z]?\d?)\b",
    re.IGNORECASE,
)


@dataclass
class _CacheEntry:
    records: list[dict]
    expires_at: float


_cache: dict[str, _CacheEntry] = {}
_cache_lock = Lock()


def _cache_get(key: str) -> list[dict] | None:
    now = time.time()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry.expires_at > now:
            return entry.records
        if entry:
            del _cache[key]
    return None


def _cache_set(key: str, records: list[dict], ttl: int) -> None:
    with _cache_lock:
        _cache[key] = _CacheEntry(records=records, expires_at=time.time() + ttl)
        if len(_cache) > 100:
            oldest = min(_cache, key=lambda k: _cache[k].expires_at)
            del _cache[oldest]


def _delay() -> None:
    time.sleep(random.uniform(0.8, 1.8))


def _normalize_patent_number(raw: str) -> str:
    return re.sub(r"\s+", "", raw.upper())


def _add_record(
    records: list[dict],
    seen: set[str],
    num: str,
    title: str,
    max_results: int,
) -> bool:
    num = _normalize_patent_number(num)
    if len(num) < 8 or num in seen:
        return len(records) >= max_results
    seen.add(num)
    records.append(
        {
            "patent_number": num,
            "title": (title or f"Патент {num}")[:500],
            "abstract": "",
            "claims": "",
            "ipc_codes": [],
            "application_date": None,
            "publication_date": None,
            "status": "",
            "applicants": [],
            "inventors": [],
        }
    )
    return len(records) >= max_results


def _parse_publication_date(raw: str) -> str | None:
    """Parse '(27.05.2025)' → ISO date."""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", raw)
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{mo}-{d}"


def _fips_num_to_patent_id(num: str) -> str:
    digits = re.sub(r"\D", "", num)
    if not digits:
        return num
    return f"RU{digits}"


def _parse_results_html(html: str, max_results: int) -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    records: list[dict] = []
    seen: set[str] = set()

    # IISS search_res.xhtml: <a class="tr" href="document.xhtml?...">
    for link in soup.select("a.tr[href*='document.xhtml']"):
        tds = link.select("div.td")
        if len(tds) < 3:
            continue
        num_raw = tds[1].get_text(strip=True)
        if not re.fullmatch(r"\d{5,12}", num_raw):
            continue
        patent_number = _fips_num_to_patent_id(num_raw)
        title = tds[4].get_text(" ", strip=True) if len(tds) > 4 else ""
        pub_date = _parse_publication_date(tds[2].get_text(strip=True))
        status = tds[-1].get_text(strip=True) if tds else ""
        if patent_number in seen:
            continue
        seen.add(patent_number)
        records.append(
            {
                "patent_number": patent_number,
                "title": title[:500] or f"Патент {patent_number}",
                "abstract": title[:800],
                "claims": "",
                "ipc_codes": [],
                "application_date": None,
                "publication_date": pub_date,
                "status": status,
                "applicants": [],
                "inventors": [],
            }
        )
        if len(records) >= max_results:
            return records

    # Fallback: RU-prefixed numbers in links
    for link in soup.find_all("a", href=True):
        combined = f"{link.get_text()} {link['href']}"
        for match in _PATENT_COMPACT_RE.finditer(combined):
            if _add_record(
                records, seen, match.group(1), link.get_text(strip=True), max_results
            ):
                return records

    return records


def _detect_chrome_major_version() -> int | None:
    """Detect installed Google Chrome major version (Windows-focused)."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Google\Chrome\BLBeacon",
            ) as key:
                version, _ = winreg.QueryValueEx(key, "version")
                return int(str(version).split(".")[0])
        except OSError:
            pass

    chrome_paths = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    for chrome_exe in chrome_paths:
        if not chrome_exe.exists():
            continue
        try:
            proc = subprocess.run(
                [str(chrome_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            output = (proc.stdout or proc.stderr or "").strip()
            match = re.search(r"(\d+)\.", output)
            if match:
                return int(match.group(1))
        except OSError:
            continue
    return None


def _chrome_version_candidates() -> list[int | None]:
    """Build list of Chrome major versions to try (newest strategies first)."""
    settings = get_settings()
    detected = _detect_chrome_major_version()
    ordered: list[int | None] = []

    if settings.chrome_version_main is not None:
        ordered.append(settings.chrome_version_main)
    if detected is not None:
        for offset in (0, -1, 1, -2):
            v = detected + offset
            if v > 0:
                ordered.append(v)

    # Last resort: let undetected-chromedriver pick (may mismatch)
    ordered.append(None)

    seen: set[int | None] = set()
    unique: list[int | None] = []
    for v in ordered:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def _create_chrome_driver():
    import undetected_chromedriver as uc
    from selenium.common.exceptions import SessionNotCreatedException

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ru-RU")

    errors: list[str] = []
    for version_main in _chrome_version_candidates():
        label = str(version_main) if version_main is not None else "auto"
        try:
            kwargs: dict = {"options": options, "use_subprocess": True}
            if version_main is not None:
                kwargs["version_main"] = version_main
            driver = uc.Chrome(**kwargs)
            logger.info("Chrome started with version_main=%s", label)
            return driver
        except SessionNotCreatedException as exc:
            errors.append(f"{label}: {exc}")
            logger.warning("Chrome version_main=%s failed: %s", label, exc)

    hint = _detect_chrome_major_version()
    extra = (
        f" Установите CHROME_VERSION_MAIN={hint} в .env."
        if hint
        else ""
    )
    raise RuntimeError(
        "Не удалось подобрать ChromeDriver под ваш Chrome. "
        + "; ".join(errors[:2])
        + extra
    )


def _prepare_fips_session(driver, wait) -> None:
    """Expand patent DB group, select inventions abstracts, open search form."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    driver.get(FIPS_DB_URL)
    _delay()

    # Section «Патентные документы РФ» is collapsed (hiddenBlock)
    section_title = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//div[contains(@class,'title') and "
                "contains(@onclick,'dbsGrid1')]",
            )
        )
    )
    driver.execute_script("arguments[0].click();", section_title)
    time.sleep(1)

    checkbox = wait.until(
        EC.presence_of_element_located((By.ID, INVENTION_DB_CHECKBOX))
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'}); arguments[0].click();",
        checkbox,
    )
    if not checkbox.is_selected():
        driver.execute_script("arguments[0].checked = true;", checkbox)
    _delay()

    wait.until(EC.element_to_be_clickable((By.ID, SIDEBAR_SEARCH))).click()
    time.sleep(2)

    def _search_form_ready(drv) -> bool:
        if "search" in drv.current_url.lower():
            return True
        return len(drv.find_elements(By.CSS_SELECTOR, "textarea")) > 0

    wait.until(_search_form_ready)
    time.sleep(1)


def _submit_fips_query(driver, wait, query: str) -> None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    query_el = None
    for selector in (
        "textarea[id*='Input']",
        "textarea[id*='query']",
        "textarea[id*='Query']",
        "textarea",
        "input[type='text'][id*='query']",
    ):
        for el in driver.find_elements(By.CSS_SELECTOR, selector):
            if el.is_displayed():
                query_el = el
                break
        if query_el:
            break

    if query_el is None:
        raise RuntimeError("Не найдено поле запроса на странице поиска ФИПС")

    query_el.clear()
    query_el.send_keys(query)
    _delay()

    submitted = False
    for btn in driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='submit'], button, a.ui-commandlink, span.ui-button-text",
    ):
        label = (btn.get_attribute("value") or btn.text or "").strip().lower()
        if "поиск" in label and btn.is_displayed():
            try:
                btn.click()
                submitted = True
                break
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
                submitted = True
                break

    if not submitted:
        driver.execute_script("arguments[0].form && arguments[0].form.submit();", query_el)

    time.sleep(3)
    try:
        wait.until(
            lambda d: "найден" in d.page_source.lower()
            or "документ" in d.page_source.lower()
            or _PATENT_COMPACT_RE.search(d.page_source) is not None
        )
    except Exception:
        time.sleep(4)


def _fetch_with_selenium(query: str, max_results: int) -> list[dict]:
    from selenium.webdriver.support.ui import WebDriverWait

    driver = _create_chrome_driver()
    wait = WebDriverWait(driver, 35)

    try:
        _prepare_fips_session(driver, wait)
        _submit_fips_query(driver, wait, query)

        html = driver.page_source
        records = _parse_results_html(html, max_results)

        # Enrich top hits from document snippets on results page
        for row in records:
            num = row["patent_number"]
            if num.lower() in html.lower():
                idx = html.lower().find(num.lower())
                snippet = html[max(0, idx - 200) : idx + 400]
                clean = re.sub(r"<[^>]+>", " ", snippet)
                clean = re.sub(r"\s+", " ", clean).strip()
                if len(clean) > 30:
                    row["abstract"] = clean[:800]

        return records
    finally:
        driver.quit()


def fetch_patents_from_fips(
    query: str,
    *,
    max_results: int = 25,
    cache_ttl: int = 300,
) -> tuple[list[dict], str]:
    """
    Fetch patents from FIPS for a query.

    Returns (records, status_message).
    """
    key = query.strip().lower()
    if len(key) < 2:
        return [], "Запрос слишком короткий"

    cached = _cache_get(key)
    if cached is not None:
        return cached, f"Из кэша ФИПС ({len(cached)} записей)"

    try:
        records = _fetch_with_selenium(key, max_results)
        if records:
            _cache_set(key, records, cache_ttl)
            return records, f"Загружено с ФИПС: {len(records)}"
        return [], "ФИПС не вернул документов по запросу"
    except ImportError:
        logger.warning("Selenium/undetected-chromedriver not installed")
        return [], "Live-режим ФИПС недоступен (нет Selenium)"
    except Exception as exc:
        logger.exception("FIPS live fetch failed: %s", exc)
        return [], f"Ошибка запроса к ФИПС: {exc}"
