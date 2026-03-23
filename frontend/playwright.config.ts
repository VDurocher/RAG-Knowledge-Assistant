import { defineConfig, devices } from "@playwright/test";

// Configuration Playwright pour les tests E2E du RAG Knowledge Assistant
export default defineConfig({
  testDir: "./tests",

  // Timeout par test
  timeout: 10_000,

  // Timeout pour chaque assertion
  expect: {
    timeout: 5_000,
  },

  // Pas de parallélisme — les tests partagent le même serveur dev
  fullyParallel: false,
  workers: 1,

  // Pas de retry en CI pour éviter les faux positifs sur les SSE
  retries: 0,

  reporter: "list",

  use: {
    baseURL: "http://localhost:3001",
    headless: true,
    // Capture automatique en cas d'échec pour débogage
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Serveur de développement Next.js lancé automatiquement avant les tests
  webServer: {
    command: "npm run dev -- --port 3001",
    url: "http://localhost:3001",
    // Ne jamais réutiliser un serveur existant — évite de se connecter au mauvais projet
    reuseExistingServer: false,
    timeout: 60_000,
    // Variables d'environnement injectées pour pointer vers les mocks réseau
    env: {
      NEXT_PUBLIC_API_URL: "http://localhost:8000",
    },
  },
});
