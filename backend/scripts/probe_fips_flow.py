"""Probe FIPS IISS session flow (dev only)."""

import re

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BASE = "https://www1.fips.ru/iiss"


def viewstate(html: str) -> str:
    m = re.search(
        r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"',
        html,
    )
    if m:
        return m.group(1)
    soup = BeautifulSoup(html, "lxml")
    el = soup.find("input", {"name": "javax.faces.ViewState"})
    return el["value"] if el and el.get("value") else ""


def main() -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    with httpx.Client(timeout=40, follow_redirects=True, headers=headers) as c:
        r = c.get(f"{BASE}/db.xhtml")
        print("1 db", r.status_code, str(r.url)[-40:])
        vs = viewstate(r.text)
        print("   viewstate", len(vs))

        # PrimeFaces partial: toggle invention abstracts DB
        ajax_headers = {
            **headers,
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        r2 = c.post(
            str(r.url),
            headers=ajax_headers,
            data={
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "db-selection-form:dbsGrid1:0:dbsGrid1checkbox",
                "javax.faces.partial.execute": "@all",
                "javax.faces.partial.render": "db-selection-form:button-set1",
                "db-selection-form:dbsGrid1:0:dbsGrid1checkbox": "on",
                "db-selection-form": "db-selection-form",
                "javax.faces.ViewState": vs,
            },
        )
        print("2 checkbox ajax", r2.status_code, len(r2.text))

        # Navigate to search page via sidebar
        r3 = c.post(
            str(r.url),
            headers=ajax_headers,
            data={
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "sidebarForm:searchLink",
                "javax.faces.partial.execute": "sidebarForm",
                "javax.faces.partial.render": "sidebarForm",
                "sidebarForm": "sidebarForm",
                "sidebarForm:searchLink": "sidebarForm:searchLink",
                "db-selection-form:dbsGrid1:0:dbsGrid1checkbox": "on",
                "javax.faces.ViewState": vs,
            },
        )
        print("3 search link ajax", r3.status_code, len(r3.text))
        if "search.xhtml" in r3.text:
            print("   contains search.xhtml in response")

        r4 = c.get(f"{BASE}/search.xhtml")
        print("4 GET search", r4.status_code, str(r4.url))
        vs2 = viewstate(r4.text)
        print("   viewstate2", len(vs2))
        # find query field ids
        soup = BeautifulSoup(r4.text, "lxml")
        for ta in soup.find_all("textarea")[:3]:
            print("   textarea", ta.get("id"), ta.get("name"))
        for inp in soup.find_all("input"):
            if inp.get("type") in (None, "text", "search"):
                print("   input", inp.get("id"), inp.get("name"))


if __name__ == "__main__":
    main()
