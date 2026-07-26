/**
 * Headless browser Golden Vault checks (reads secrets locally; never logs them).
 */
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BACKEND = join(__dirname, '..');
const BASE_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const CODE_PATH = join(BACKEND, '.golden_vault_local');
const PYTHON =
  process.env.BROWSER_VERIFY_PYTHON ||
  join(BACKEND, '.venv', 'Scripts', 'python.exe');

function record(checks, name, ok, detail = '') {
  checks.push({ name, ok, detail });
}

function createResearcherInvite() {
  const result = spawnSync(
    PYTHON,
    [join(BACKEND, 'scripts', 'create_browser_researcher_invite.py')],
    { encoding: 'utf8', cwd: BACKEND },
  );
  if (result.status !== 0) {
    throw new Error(result.stderr || 'failed to create researcher invite');
  }
  return JSON.parse(result.stdout.trim()).researcherCode;
}

async function main() {
  const checks = [];
  if (!readFileSync(CODE_PATH, 'utf8').trim()) {
    console.log(JSON.stringify({ ok: false, error: 'missing golden code file', checks }, null, 2));
    process.exit(1);
  }
  const goldenCode = readFileSync(CODE_PATH, 'utf8').trim();
  const wrongCode = 'browser-wrong-golden-code-xyz';
  const researcherCode = createResearcherInvite();

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });

  await page.goto(`${BASE_URL}/researcher/sign-in`, { waitUntil: 'networkidle' });
  await page.fill('input[type="password"]', wrongCode);
  await page.getByRole('button', { name: 'Sign In as Researcher →' }).click();
  try {
    await page.waitForURL('**/golden-vault**', { timeout: 3000 });
    record(checks, 'incorrect_golden_code_rejected', false, page.url());
  } catch {
    const alertVisible = await page.getByRole('alert').isVisible();
    record(
      checks,
      'incorrect_golden_code_rejected',
      alertVisible && !page.url().includes('/golden-vault'),
      page.url(),
    );
  }

  await page.goto(`${BASE_URL}/researcher/sign-in`, { waitUntil: 'networkidle' });
  await page.fill('input[type="password"]', goldenCode);
  await page.getByRole('button', { name: 'Sign In as Researcher →' }).click();
  await page.waitForURL('**/golden-vault**', { timeout: 15000 });
  await page.waitForSelector('[data-testid="golden-vault-page"]', { timeout: 15000 });
  record(checks, 'golden_code_redirects_to_vault', page.url().includes('/golden-vault'), page.url());
  record(checks, 'golden_vault_heading', await page.getByText('Golden Vault').isVisible(), '');
  record(checks, 'simulated_data_banner', await page.getByText('SIMULATED DATA').isVisible(), '');

  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return doc.scrollWidth <= doc.clientWidth + 2;
  });
  record(
    checks,
    'mobile_no_horizontal_overflow',
    overflow,
    `scrollWidth=${await page.evaluate(() => document.documentElement.scrollWidth)}`,
  );

  await page.evaluate(() => localStorage.removeItem('nc3_golden_vault_token'));
  await page.goto(`${BASE_URL}/researcher/sign-in`, { waitUntil: 'networkidle' });
  await page.fill('input[type="password"]', researcherCode);
  await page.getByRole('button', { name: 'Sign In as Researcher →' }).click();
  await page.waitForURL('**/researcher/dashboard**', { timeout: 15000 });
  record(
    checks,
    'ordinary_researcher_login',
    page.url().includes('/researcher/dashboard'),
    page.url(),
  );

  await browser.close();
  const ok = checks.every(c => c.ok);
  console.log(JSON.stringify({ ok, checks }, null, 2));
  process.exit(ok ? 0 : 1);
}

main().catch(err => {
  console.log(JSON.stringify({ ok: false, error: String(err.message || err), checks: [] }, null, 2));
  process.exit(2);
});
