import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './specs',
  globalSetup: './global-setup.js',
  globalTeardown: './global-teardown.js',
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'echo "Using existing dev server — start with: docker compose -f docker-compose.dev.yml up -d"',
    url: 'http://localhost:8080',
    reuseExistingServer: true,
    timeout: 10000,
  },
  projects: [
    { name: 'chromium',      use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',       use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',        use: { ...devices['Desktop Safari'] } },
    { name: 'edge',          use: { ...devices['Desktop Edge'], channel: 'msedge' } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 14'] } },
  ],
})
