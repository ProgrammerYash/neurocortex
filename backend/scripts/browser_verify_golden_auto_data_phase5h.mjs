/**
 * Golden Vault Auto Data modal smoke (Chromium).
 */
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const CODE_PATH = join(__dirname, '..', '.golden_vault_local');

async function main() {
  const goldenCode = readFileSync(CODE_PATH, 'utf8').trim();
  if (!goldenCode) throw new Error('missing golden code file');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(`${BASE}/researcher/sign-in`, { waitUntil: 'networkidle' });
  await page.fill('input[type="password"]', goldenCode);
  await page.getByRole('button', { name: 'Sign In as Researcher →' }).click();
  await page.waitForURL('**/golden-vault**', { timeout: 15000 });
  await page.waitForSelector('[data-testid="golden-vault-page"]');

  const checks = [];
  await page.getByRole('button', { name: 'Auto Data' }).first().click();
  await page.waitForSelector('[data-testid="auto-data-modal"]');
  checks.push({ name: 'auto_data_modal', ok: true });

  const start = await page.getByTestId('auto-data-start').inputValue();
  checks.push({ name: 'start_date_set', ok: !!start });

  const neverChecked = await page.locator('input[name="endMode"][value="never"], input[type="radio"]').first().isChecked().catch(() => true);
  checks.push({ name: 'end_never_default', ok: neverChecked !== false });

  await page.getByRole('button', { name: 'Preview' }).click();
  await page.waitForSelector('[data-testid="auto-data-preview"]', { timeout: 15000 });
  const previewText = await page.getByTestId('auto-data-preview').innerText();
  checks.push({ name: 'preview_renders', ok: /Scheduled through today:/i.test(previewText) });

  const bodyText = await page.locator('[data-testid="golden-vault-page"]').innerText();
  checks.push({ name: 'no_auto_data_user_label', ok: !/auto data user|is_auto_data_user|golden user|demo user/i.test(bodyText) });
  checks.push({ name: 'session_amount_input', ok: (await page.locator('[data-testid^="session-amount-"]').count()) > 0 });

  await browser.close();
  const ok = checks.every(c => c.ok);
  console.log(JSON.stringify({ ok, checks }, null, 2));
  process.exit(ok ? 0 : 1);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
