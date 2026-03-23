import { test, expect, type Page, type Route } from "@playwright/test";

// ─── Données de mock réutilisables ────────────────────────────────────────────

const MOCK_STATUS = {
  doc_count: 3,
  llm_label: "gpt-4o-mini",
  embedder_label: "text-embedding-3-small",
};

const MOCK_DOCUMENTS = [
  { name: "contracts.pdf", extension: "pdf" },
  { name: "employees.csv", extension: "csv" },
  { name: "procedures.docx", extension: "docx" },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

// Monte les deux routes de démarrage nécessaires à chaque test
async function mockBaseRoutes(page: Page): Promise<void> {
  await page.route("**/api/status", (route: Route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_STATUS) })
  );
  await page.route("**/api/documents", (route: Route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_DOCUMENTS) })
  );
}

// ─── Suite ────────────────────────────────────────────────────────────────────

test.describe("UI — rendu et interactions de base", () => {
  test.beforeEach(async ({ page }) => {
    await mockBaseRoutes(page);
    await page.goto("/");
  });

  // 1. EmptyState visible au chargement
  test("affiche l'EmptyState avec le texte 'Ask anything' au démarrage", async ({ page }) => {
    // Arrange — routes mockées dans beforeEach
    // Act — page déjà chargée
    // Assert
    await expect(
      page.getByText("Ask anything about your documents")
    ).toBeVisible();
  });

  // 2. Liste des documents dans la sidebar
  test("affiche les 3 documents mockés dans la sidebar", async ({ page }) => {
    // exact: true — évite le match partiel sur "Delete contracts.pdf"
    await expect(page.getByTitle("contracts.pdf", { exact: true })).toBeVisible();
    await expect(page.getByTitle("employees.csv", { exact: true })).toBeVisible();
    await expect(page.getByTitle("procedures.docx", { exact: true })).toBeVisible();
  });

  // 3. Badge count dans la section Documents
  test("affiche le badge '3' dans la section Documents de la sidebar", async ({ page }) => {
    // Le badge est un <span> adjacent au label "DOCUMENTS"
    const documentsSection = page.locator("section").filter({
      has: page.getByText("Documents", { exact: false }),
    });
    await expect(documentsSection.getByText("3")).toBeVisible();
  });

  // 4. Badge LLM dans le header du chat
  test("affiche le badge 'gpt-4o-mini' dans l'en-tête du chat", async ({ page }) => {
    await expect(page.getByText("gpt-4o-mini")).toBeVisible();
  });

  // 5. Accordéon Settings — les sliders apparaissent après le clic
  test("ouvre le panneau Settings et affiche les sliders au clic", async ({ page }) => {
    // Arrange — le panneau est fermé par défaut
    const confidenceLabel = page.getByText("Confidence threshold");
    await expect(confidenceLabel).not.toBeVisible();

    // Act
    await page.getByRole("button", { name: /settings/i }).click();

    // Assert
    await expect(confidenceLabel).toBeVisible();
    await expect(page.getByText("Results per query")).toBeVisible();
    await expect(page.getByText("General knowledge fallback")).toBeVisible();
  });

  // 6. Toggle fallback — change d'état visuellement
  test("bascule l'état du toggle fallback au clic", async ({ page }) => {
    // Arrange — ouvrir les settings
    await page.getByRole("button", { name: /settings/i }).click();

    const toggle = page.getByRole("button", { name: /disable fallback/i });
    // Le toggle est activé par défaut (aria-label "Disable fallback")
    await expect(toggle).toBeVisible();

    // Act
    await toggle.click();

    // Assert — après clic, le label bascule sur "Enable fallback"
    await expect(page.getByRole("button", { name: /enable fallback/i })).toBeVisible();
  });
});
