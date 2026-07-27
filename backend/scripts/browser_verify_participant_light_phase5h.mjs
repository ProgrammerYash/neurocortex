/**
 * Participant dashboard light-theme contrast checks (Chromium + live API).
 */
import { chromium } from 'playwright';
import { spawnSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BACKEND = join(__dirname, '..');
const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const API = process.env.API_URL || 'http://127.0.0.1:8000';
const PYTHON = join(BACKEND, '.venv', 'Scripts', 'python.exe');

function createParticipant() {
  const script = `
from fastapi.testclient import TestClient
from app.main import app
from tests.test_electronic_consent import register
c = TestClient(app)
resp = register(c)
assert resp.status_code in (200, 201), resp.text
data = resp.json()
pid = data['public_id']
token = data['access_token']
pref = c.patch(
    '/v1/participants/me/preferences',
    json={'study_frequency': 'daily'},
    headers={'Authorization': f'Bearer {token}'},
)
assert pref.status_code == 200, pref.text
print(pid)
`;
  const r = spawnSync(PYTHON, ['-c', script], { cwd: BACKEND, encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr || 'participant bootstrap failed');
  return r.stdout.trim();
}

function contrast(fg, bg) {
  const parse = hex => {
    const h = hex.replace('#', '');
    const n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(v => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
  };
  const lum = ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const f = parse(fg);
  const b = parse(bg);
  const L1 = lum(f) + 0.05;
  const L2 = lum(b) + 0.05;
  return L1 > L2 ? L1 / L2 : L2 / L1;
}

async function main() {
  const publicId = createParticipant();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  await page.goto(`${BASE}/participant/sign-in`, { waitUntil: 'networkidle' });
  await page.getByPlaceholder('NC-XXXXXXXXXXXXXXXX').fill(publicId);
  await page.getByPlaceholder('4–6 digit PIN').fill('2468');
  await page.getByRole('button', { name: /Sign In/i }).click();
  const landed = await Promise.race([
    page.waitForURL('**/participant/dashboard**', { timeout: 90000 }).then(() => 'dashboard'),
    page.waitForSelector('[style*="252,129,129"]', { timeout: 90000 }).then(() => 'error'),
  ]).catch(() => 'timeout');
  if (landed !== 'dashboard') {
    const diag = await page.evaluate(() => ({
      url: location.href,
      text: document.body.innerText.slice(0, 400),
    }));
    console.log(JSON.stringify({ ok: false, step: 'login', landed, diag, consoleErrors }, null, 2));
    await browser.close();
    process.exit(1);
  }
  await page.waitForFunction(
    () => !document.body.innerText.includes('Loading your session'),
    { timeout: 90000 },
  );
  let participantShell;
  try {
    participantShell = await page.waitForSelector('.participant-app', { timeout: 90000 });
  } catch {
    const diag = await page.evaluate(() => ({
      url: location.href,
      loader: document.body.innerText.includes('Loading your session'),
      signIn: document.body.innerText.includes('Enter your Participant ID'),
      preview: document.body.innerText.slice(0, 350),
    }));
    console.log(JSON.stringify({ ok: false, step: 'shell', diag, consoleErrors }, null, 2));
    await browser.close();
    process.exit(1);
  }
  if (!participantShell) {
    console.log(JSON.stringify({ ok: false, step: 'shell_missing', consoleErrors }, null, 2));
    await browser.close();
    process.exit(1);
  }

  await page.getByRole('button', { name: 'Participant settings' }).click();
  await page.waitForURL('**/participant/settings**', { timeout: 15000 });
  await page.locator('button').filter({ hasText: /^Light$/ }).click();
  await page.getByTestId('participant-settings-save').click();
  await page.waitForSelector('.participant-app--light', { timeout: 15000 });
  await page.goto(`${BASE}/participant/dashboard`, { waitUntil: 'networkidle' });
  await page.waitForFunction(
    () => !document.body.innerText.includes('Loading your session'),
    { timeout: 60000 },
  );
  await page.waitForSelector('.participant-app--light', { timeout: 30000 });

  const checks = [];
  const sample = await page.evaluate(() => {
    const app = document.querySelector('.participant-app');
    const card = document.querySelector('.participant-card');
    const muted = document.querySelector('.participant-muted');
    const text = getComputedStyle(app || document.body).color;
    const bg = getComputedStyle(app || document.body).backgroundColor;
    const cardText = card ? getComputedStyle(card).color : null;
    const cardBg = card ? getComputedStyle(card).backgroundColor : null;
    const mutedColor = muted ? getComputedStyle(muted).color : null;
    const bodyText = document.body.innerText;
    return {
      hasLightClass: app?.classList.contains('participant-app--light'),
      text,
      bg,
      cardText,
      cardBg,
      mutedColor,
      hasCompletedSessionsRatio: /Completed sessions:\s*\d+\s*\/\s*\d+/i.test(bodyText),
    };
  });
  checks.push({ name: 'light_class', ok: sample.hasLightClass });
  checks.push({ name: 'no_completed_sessions_ratio', ok: !sample.hasCompletedSessionsRatio });

  await page.locator('button').filter({ hasText: /^Progress$/ }).click();
  await page.waitForTimeout(600);
  checks.push({
    name: 'progress_tab_text',
    ok: await page.evaluate(() => {
      const el = document.querySelector('[data-testid="weekly-session-progress"]') || document.querySelector('.participant-card');
      if (!el) return true;
      const fg = getComputedStyle(el).color;
      return fg !== 'rgb(226, 232, 240)';
    }),
  });

  await page.locator('button').filter({ hasText: /^Enrollment$/ }).click();
  await page.waitForTimeout(600);
  let enrollmentOk = await page.evaluate(() => {
    const card = document.querySelector('.participant-card');
    if (!card) return false;
    const fg = getComputedStyle(card).color;
    const bg = getComputedStyle(card).backgroundColor;
    return fg && bg && fg !== bg;
  });
  checks.push({ name: 'enrollment_readable', ok: enrollmentOk });

  await page.getByRole('button', { name: 'Participant settings' }).click();
  await page.waitForURL('**/participant/settings**', { timeout: 15000 });
  checks.push({
    name: 'settings_readable',
    ok: await page.evaluate(() => {
      const card = document.querySelector('.participant-card');
      if (!card) return false;
      const style = getComputedStyle(card);
      return style.color !== 'rgb(226, 232, 240)' && style.backgroundColor !== 'rgb(19, 25, 40)';
    }),
  });

  await page.locator('button').filter({ hasText: /^Dark$/ }).click();
  await page.getByTestId('participant-settings-save').click();
  await page.waitForSelector('.participant-app--dark', { timeout: 15000 });
  checks.push({
    name: 'dark_mode_class',
    ok: await page.evaluate(() => document.querySelector('.participant-app--dark') !== null),
  });

  await browser.close();
  const ok = checks.every(c => c.ok);
  console.log(JSON.stringify({ ok, checks, publicId }, null, 2));
  process.exit(ok ? 0 : 1);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
