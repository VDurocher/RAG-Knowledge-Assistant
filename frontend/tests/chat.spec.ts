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

// Construit une réponse SSE complète sous forme de string
function buildSseStream(tokens: string[], sources: unknown[]): string {
  const tokenEvents = tokens
    .map((token) => `event: token\ndata: ${JSON.stringify({ token })}\n\n`)
    .join("");

  const sourcesEvent = `event: sources\ndata: ${JSON.stringify(sources)}\n\n`;
  const doneEvent = `event: done\ndata: ${JSON.stringify({ is_fallback: false })}\n\n`;

  return tokenEvents + sourcesEvent + doneEvent;
}

const SSE_SOURCES = [
  {
    source: "contracts.pdf",
    page: 1,
    excerpt: "Les conditions générales de vente sont applicables à partir du 01/01/2024.",
    confidence: 0.85,
    confidence_label: "high",
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function mockBaseRoutes(page: Page): Promise<void> {
  await page.route("**/api/status", (route: Route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_STATUS) })
  );
  await page.route("**/api/documents", (route: Route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_DOCUMENTS) })
  );
}

// Monte un mock SSE pour /api/chat avec les tokens et sources fournis
async function mockChatRoute(
  page: Page,
  tokens: string[],
  sources: unknown[] = SSE_SOURCES
): Promise<void> {
  await page.route("**/api/chat", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: {
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
      body: buildSseStream(tokens, sources),
    })
  );
}

// Tape un message dans l'input et l'envoie via Enter
async function sendChatMessage(page: Page, text: string): Promise<void> {
  const textarea = page.getByPlaceholder("Ask a question about your documents…");
  await textarea.fill(text);
  await textarea.press("Enter");
}

// ─── Suite ────────────────────────────────────────────────────────────────────

test.describe("Chat — flux de conversation", () => {
  test.beforeEach(async ({ page }) => {
    await mockBaseRoutes(page);
    await page.goto("/");
  });

  // 1. Le message utilisateur apparaît dans la liste après envoi
  test("affiche le message utilisateur dans la liste après envoi via Enter", async ({ page }) => {
    // Arrange
    await mockChatRoute(page, ["Hello", " world"]);

    // Act
    await sendChatMessage(page, "Quelles sont les clauses du contrat ?");

    // Assert — la bulle utilisateur doit être visible
    await expect(
      page.getByText("Quelles sont les clauses du contrat ?")
    ).toBeVisible();
  });

  // 2. La réponse streamée apparaît après envoi
  test("affiche la réponse 'Hello world' reconstituée depuis les tokens SSE", async ({ page }) => {
    // Arrange
    await mockChatRoute(page, ["Hello", " world"]);

    // Act
    await sendChatMessage(page, "Test streaming");

    // Assert — le contenu assemblé doit être visible une fois le stream terminé
    await expect(page.getByText("Hello world")).toBeVisible({ timeout: 8_000 });
  });

  // 3. Les source chips apparaissent après la réponse
  test("affiche le chip source 'contracts.pdf' après la réponse de l'assistant", async ({ page }) => {
    // Arrange
    await mockChatRoute(page, ["Voici la réponse."], SSE_SOURCES);

    // Act
    await sendChatMessage(page, "Quel est le contenu du contrat ?");

    // Assert — le chip de source doit être visible après la fin du stream
    await expect(page.getByText("contracts.pdf")).toBeVisible({ timeout: 8_000 });
  });

  // 4. Cliquer "View excerpts" déplie l'accordéon
  test("déplie l'accordéon des extraits au clic sur 'View excerpts'", async ({ page }) => {
    // Arrange
    await mockChatRoute(page, ["Réponse avec source."], SSE_SOURCES);
    await sendChatMessage(page, "Montre-moi les extraits");

    // Attendre que les chips soient visibles avant de chercher le bouton
    await expect(page.getByText("contracts.pdf")).toBeVisible({ timeout: 8_000 });

    // Assert — l'excerpt n'est pas encore visible
    const excerptText = "Les conditions générales de vente";
    await expect(page.getByText(excerptText)).not.toBeVisible();

    // Act
    await page.getByRole("button", { name: /view excerpts/i }).click();

    // Assert — le contenu de l'extrait doit être visible
    await expect(page.getByText(excerptText)).toBeVisible();
  });

  // 5. Clear réinitialise la conversation et ré-affiche l'EmptyState
  test("réaffiche l'EmptyState après avoir cliqué Clear", async ({ page }) => {
    // Arrange — envoyer un message d'abord
    await mockChatRoute(page, ["Une réponse."]);
    await sendChatMessage(page, "Question initiale");
    await expect(page.getByText("Une réponse.")).toBeVisible({ timeout: 8_000 });

    // Act
    await page.getByRole("button", { name: /clear/i }).click();

    // Assert — l'EmptyState doit réapparaître
    await expect(
      page.getByText("Ask anything about your documents")
    ).toBeVisible();

    // Et le message précédent ne doit plus exister
    await expect(page.getByText("Question initiale")).not.toBeVisible();
  });

  // 6. Shift+Enter insère un saut de ligne sans envoyer le message
  test("insère un saut de ligne avec Shift+Enter sans envoyer le message", async ({ page }) => {
    // Arrange
    await mockChatRoute(page, []);
    const textarea = page.getByPlaceholder("Ask a question about your documents…");

    // Act — taper du texte puis Shift+Enter
    await textarea.fill("Ligne 1");
    await textarea.press("Shift+Enter");
    await textarea.type("Ligne 2");

    // Assert — l'input contient les deux lignes (pas d'envoi)
    const value = await textarea.inputValue();
    expect(value).toContain("Ligne 1");
    expect(value).toContain("Ligne 2");

    // Et aucun message utilisateur ne doit avoir été ajouté à la liste
    await expect(page.getByText("Ask anything about your documents")).toBeVisible();
  });
});
