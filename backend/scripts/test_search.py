"""Integration tests for search API (run with uvicorn on :8000)."""

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> None:
    with httpx.Client(timeout=120.0) as client:
        h = client.get(f"{BASE}/health").json()
        assert h["status"] == "ok", h
        print("health:", h)

        r = client.post(
            f"{BASE}/api/v1/search",
            json={
                "query": "нейросеть",
                "top_k": 3,
                "mode": "semantic",
                "live": False,
            },
        )
        r.raise_for_status()
        sem = r.json()["results"]
        assert sem[0]["patent"]["patent_number"] == "RU2020112345A", sem
        print("semantic:", [x["patent"]["patent_number"] for x in sem])

        r = client.post(
            f"{BASE}/api/v1/search",
            json={
                "query": "нейрон",
                "top_k": 3,
                "mode": "keyword",
                "live": False,
            },
        )
        r.raise_for_status()
        kw = r.json()["results"]
        assert any(
            x["patent"]["patent_number"] == "RU2020112345A" for x in kw
        ), kw
        print("keyword:", [x["patent"]["patent_number"] for x in kw])

        detail = client.get(f"{BASE}/api/v1/patents/RU2020112345A")
        detail.raise_for_status()
        assert "нейрон" in detail.json()["title"].lower()
        print("detail ok:", detail.json()["patent_number"])


if __name__ == "__main__":
    main()
