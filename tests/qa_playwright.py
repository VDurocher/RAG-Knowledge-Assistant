"""Script QA Playwright pour RAG-Knowledge-Assistant — teste l'UI Streamlit."""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
APP_URL = "http://localhost:8502"

# Rapport des bugs trouvés
bugs: list[dict] = []


def log_bug(category: str, description: str, severity: str = "medium") -> None:
    """Enregistre un bug dans la liste."""
    bugs.append({"category": category, "description": description, "severity": severity})
    print(f"  [BUG {severity.upper()}] {category}: {description}")


def run_qa_tests() -> list[dict]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # Collecte des erreurs console
        console_errors: list[str] = []
        page.on(
            "console",
            lambda msg: console_errors.append(f"[{msg.type}] {msg.text}")
            if msg.type == "error"
            else None,
        )

        print("\n=== TEST 1 : Chargement de la page ===")
        try:
            response = page.goto(APP_URL, wait_until="networkidle", timeout=30_000)
            if response and response.status >= 400:
                log_bug("Chargement", f"HTTP {response.status} lors du chargement", "critical")
            else:
                print(f"  OK — page chargée (HTTP {response.status if response else 'inconnu'})")
        except PlaywrightTimeout:
            log_bug("Chargement", "Timeout : la page ne se charge pas en 30s", "critical")
            browser.close()
            return bugs

        # Attente du rendu Streamlit complet (chargement modèle HuggingFace peut prendre 30-120s)
        print("  Attente du chargement Streamlit (modèle embeddings HuggingFace + FAISS)...")

        # Attente que le spinner de cache disparaisse ET que le chat input apparaisse
        try:
            page.wait_for_selector(
                "[data-testid='stChatInput']",
                timeout=120_000,
            )
            print("  OK — pipeline RAG chargé, chat input visible")
        except PlaywrightTimeout:
            # Peut-être une erreur de config — on vérifie les alertes
            print("  WARN — timeout 120s, pipeline non chargé. Vérification des erreurs...")
            try:
                page.wait_for_selector(
                    "[data-testid='stAlert'], [data-testid='stSidebar']",
                    timeout=10_000,
                )
            except PlaywrightTimeout:
                pass
        time.sleep(2)

        # Screenshot initial
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_initial_load.png"), full_page=True)
        print("  Screenshot sauvegardé : 01_initial_load.png")

        print("\n=== TEST 2 : Titre / Header principal ===")
        title_selectors = [
            "h1",
            "[data-testid='stTitle']",
            "text=Knowledge Assistant",
            "text=RAG",
        ]
        title_found = False
        for selector in title_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=3_000):
                    text = element.inner_text()
                    print(f"  OK — titre trouvé : '{text.strip()[:60]}'")
                    title_found = True
                    break
            except Exception:
                continue

        if not title_found:
            log_bug("Header", "Titre principal (h1) non visible sur la page", "high")

        print("\n=== TEST 3 : Sidebar et widgets ===")

        # Sidebar
        try:
            sidebar = page.locator("[data-testid='stSidebar']")
            if sidebar.is_visible(timeout=5_000):
                print("  OK — sidebar visible")
                sidebar.screenshot(path=str(SCREENSHOTS_DIR / "02_sidebar.png"))
                print("  Screenshot sauvegardé : 02_sidebar.png")
            else:
                log_bug("Sidebar", "Sidebar non visible", "high")
        except Exception as error:
            log_bug("Sidebar", f"Erreur sidebar : {error}", "high")

        # File uploader
        try:
            uploader = page.locator("[data-testid='stFileUploader']")
            if uploader.first.is_visible(timeout=5_000):
                print("  OK — file uploader présent")
            else:
                log_bug("File Uploader", "Widget file uploader absent ou non visible", "medium")
        except Exception as error:
            log_bug("File Uploader", f"Erreur : {error}", "medium")

        # Sliders
        try:
            sliders = page.locator("[data-testid='stSlider']")
            count = sliders.count()
            if count >= 2:
                print(f"  OK — {count} sliders présents (attendu : 2+)")
            else:
                log_bug("Sliders", f"Seulement {count} slider(s) trouvé(s) (attendu : 2+)", "medium")
        except Exception as error:
            log_bug("Sliders", f"Erreur : {error}", "medium")

        # Toggles — plusieurs sélecteurs possibles selon la version Streamlit
        try:
            # Streamlit >= 1.35 utilise data-testid="stCheckbox" ou "stToggle"
            toggles = page.locator("[data-testid='stToggle'], [role='switch']")
            count = toggles.count()
            if count >= 2:
                print(f"  OK — {count} toggles/switches présents")
            else:
                # Fallback : vérifier par rôle
                switches = page.locator("input[type='checkbox']")
                switch_count = switches.count()
                if switch_count >= 2:
                    print(f"  OK — {switch_count} switches (checkboxes) présents")
                else:
                    log_bug(
                        "Toggles",
                        f"Seulement {count} toggle(s) détecté(s) (attendu : 2+). "
                        f"Vérifier le sélecteur data-testid.",
                        "low",
                    )
        except Exception as error:
            log_bug("Toggles", f"Erreur : {error}", "low")

        print("\n=== TEST 4 : Boutons sidebar ===")
        try:
            buttons = page.locator("[data-testid='stSidebar'] button")
            count = buttons.count()
            print(f"  OK — {count} bouton(s) dans la sidebar")
            if count == 0:
                log_bug("Boutons", "Aucun bouton dans la sidebar", "medium")
        except Exception as error:
            log_bug("Boutons", f"Erreur : {error}", "medium")

        print("\n=== TEST 5 : Zone principale — chat input ===")
        try:
            chat_input = page.locator("[data-testid='stChatInput']")
            if chat_input.is_visible(timeout=5_000):
                print("  OK — chat input visible")
            else:
                log_bug(
                    "Chat Input",
                    "Chat input non visible — app bloquée par erreur config ou absence docs",
                    "high",
                )
        except Exception as error:
            log_bug("Chat Input", f"Erreur : {error}", "high")

        print("\n=== TEST 6 : Détection d'erreurs Python dans l'UI ===")
        try:
            error_elements = page.locator("[data-testid='stAlert']")
            alert_count = error_elements.count()

            error_alerts: list[str] = []
            for index in range(alert_count):
                element = error_elements.nth(index)
                try:
                    text = element.inner_text()
                    if any(
                        kw in text.lower()
                        for kw in [
                            "error",
                            "exception",
                            "traceback",
                            "attributeerror",
                            "typeerror",
                            "valueerror",
                        ]
                    ):
                        error_alerts.append(text[:200])
                except Exception:
                    pass

            if error_alerts:
                for alert_text in error_alerts:
                    log_bug("Erreur Python", f"Exception visible dans l'UI : {alert_text}", "critical")
            else:
                print(
                    f"  OK — aucune exception Python visible ({alert_count} alerte(s) non-erreur)"
                )

        except Exception as error:
            log_bug("Erreurs UI", f"Impossible de vérifier les alertes : {error}", "medium")

        print("\n=== TEST 7 : Badge knowledge base ===")
        try:
            page_content = page.content()
            if "badge-ok" in page_content or "documents indexed" in page_content:
                print("  OK — badge vert (documents indexés trouvés)")
            elif "badge-err" in page_content or "No documents found" in page_content:
                log_bug(
                    "Knowledge Base",
                    "Badge rouge — aucun document trouvé dans knowledge_base/",
                    "high",
                )
            else:
                print("  INFO — badge non détecté dans le HTML")
        except Exception as error:
            log_bug("Knowledge Base", f"Erreur : {error}", "low")

        print("\n=== TEST 8 : Erreurs console navigateur ===")
        if console_errors:
            print(f"  {len(console_errors)} erreur(s) console :")
            for err in console_errors[:5]:
                print(f"    - {err[:120]}")
                log_bug("Console JS", err[:120], "low")
        else:
            print("  OK — aucune erreur console JavaScript")

        print("\n=== TEST 9 : Screenshots finaux ===")
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_full_page.png"), full_page=True)
        print("  Screenshot sauvegardé : 03_full_page.png")

        try:
            main_area = page.locator("[data-testid='stAppViewContainer']")
            if main_area.is_visible(timeout=3_000):
                main_area.screenshot(path=str(SCREENSHOTS_DIR / "04_main_area.png"))
                print("  Screenshot sauvegardé : 04_main_area.png")
        except Exception:
            pass

        print("\n=== TEST 10 : Vue mobile (375px) ===")
        context_mobile = browser.new_context(viewport={"width": 375, "height": 812})
        page_mobile = context_mobile.new_page()
        try:
            page_mobile.goto(APP_URL, wait_until="networkidle", timeout=20_000)
            time.sleep(2)
            page_mobile.screenshot(
                path=str(SCREENSHOTS_DIR / "05_mobile_view.png"), full_page=True
            )
            print("  OK — 05_mobile_view.png sauvegardé")
        except Exception as error:
            log_bug("Mobile", f"Problème vue mobile : {error}", "low")
        finally:
            context_mobile.close()

        browser.close()

    # ─── Rapport final ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RAPPORT QA — RÉSUMÉ")
    print("=" * 60)

    if not bugs:
        print("Aucun bug détecté — application conforme.")
    else:
        by_severity: dict[str, list[dict]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }
        for bug in bugs:
            by_severity[bug["severity"]].append(bug)

        for severity in ["critical", "high", "medium", "low"]:
            items = by_severity[severity]
            if items:
                print(f"\n[{severity.upper()}] — {len(items)} bug(s)")
                for item in items:
                    print(f"  - [{item['category']}] {item['description']}")

    print(f"\nTotal : {len(bugs)} bug(s) trouvé(s)")
    print(f"Screenshots dans : {SCREENSHOTS_DIR}")

    return bugs


if __name__ == "__main__":
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    result_bugs = run_qa_tests()
    sys.exit(1 if any(b["severity"] in ("critical", "high") for b in result_bugs) else 0)
