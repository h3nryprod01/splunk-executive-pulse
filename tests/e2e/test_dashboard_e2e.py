"""E2E smoke test for the Executive Pulse dashboard (run via with_server.py)."""
from __future__ import annotations
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:3000"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


def first_story_text(page) -> str:
    return page.locator("text=/Story 1/").first.inner_text().lower()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 2200})

    page.goto(URL)
    page.wait_for_load_state("networkidle")
    # Warm the API route, then reload so the page fetch lands on live data.
    page.wait_for_timeout(1500)
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)

    # 1. Page renders the briefing
    check("page title", "Executive Pulse" in page.content())

    # 2. CEO is the default persona and leads with the revenue incident
    page.wait_for_selector("text=/Story 1/")
    ceo_story1 = first_story_text(page)
    check("CEO headline = revenue", "revenue" in ceo_story1, ceo_story1[:60])

    # 3. Audio player wired to a real mp3
    audio_src = page.locator("audio").first.get_attribute("src") or ""
    check("audio src is /audio/*.mp3", "/audio/" in audio_src and audio_src.endswith(".mp3"), audio_src)

    # 4. Persona switch: CISO leads with the security threat (same data, different lens)
    page.locator("button.flex-1", has_text="CISO").click()
    page.wait_for_timeout(1500)
    ciso_story1 = first_story_text(page)
    check("CISO headline = security", "security" in ciso_story1, ciso_story1[:60])
    check("differentiation (CEO != CISO headline)", ceo_story1 != ciso_story1)

    # 5. Drill-down: NL question -> SPL via the AI Assistant
    page.get_by_role("button", name="Was there a credential stuffing attack?").click()
    page.wait_for_selector("pre", timeout=8000)
    spl = page.locator("pre").first.inner_text()
    check("drill-down returns SPL", "index=security" in spl, spl[:70])

    page.screenshot(path="/tmp/dashboard_e2e.png", full_page=True)
    print("  screenshot -> /tmp/dashboard_e2e.png")
    browser.close()

print(f"\n{'ALL PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
