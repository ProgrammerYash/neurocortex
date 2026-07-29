/**
 * Phase 5I participant route light/dark audit at multiple widths.
 *
 * Isolated typing check:
 *   node browser_verify_phase5i_participant_routes.mjs --only typing_mobile_light
 */
import { chromium } from 'playwright';
import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BACKEND = join(__dirname, '..');
const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const PYTHON = join(BACKEND, '.venv', 'Scripts', 'python.exe');
const ARTIFACTS_DIR = join(BACKEND, 'test-artifacts');
const TYPING_ROUTE = '/participant/session/typing';

const ROUTES = [
  '/participant/dashboard',
  '/participant/settings',
  '/participant/schedule',
  '/participant/inbox',
  '/participant/session/reaction-time',
  TYPING_ROUTE,
  '/participant/session/memory',
  '/participant/session/attention',
  '/participant/session/daily-survey',
  '/participant/session/nasa-tlx',
  '/participant/pet',
  '/participant/neuroverse',
  '/participant/achievements',
];

const WIDTHS = [1440, 1280, 1024, 768, 390];

function parseOnlyMode(argv) {
  const idx = argv.indexOf('--only');
  if (idx === -1) return null;
  return argv[idx + 1] || null;
}

function bootstrapParticipant() {
  const script = `
from fastapi.testclient import TestClient
from app.main import app
from tests.test_electronic_consent import register
import json
c = TestClient(app)
resp = register(c)
assert resp.status_code in (200, 201), resp.text
data = resp.json()
pid = data['public_id']
token = data['access_token']
c.patch('/v1/participants/me/preferences', json={'study_frequency': 'daily'}, headers={'Authorization': f'Bearer {token}'})
sessions = c.get('/v1/participants/me/sessions', headers={'Authorization': f'Bearer {token}'})
assert sessions.status_code == 200
print(json.dumps({'publicId': pid, 'accessToken': token}))
`;
  const r = spawnSync(PYTHON, ['-c', script], { cwd: BACKEND, encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr || 'bootstrap failed');
  return JSON.parse(r.stdout.trim());
}

async function seedParticipantAuth(page, { publicId, accessToken }) {
  await gotoSafe(page, `${BASE}/`);
  await clearParticipantStorage(page);
  await page.evaluate(({ publicId, accessToken }) => {
    localStorage.setItem('nc3_token', accessToken);
    localStorage.setItem('nc3_participant_theme_last_id', publicId);
    const map = {};
    map[publicId] = 'light';
    localStorage.setItem('nc3_participant_themes', JSON.stringify(map));
  }, { publicId, accessToken });
  const dashResponse = await gotoSafe(page, `${BASE}/participant/dashboard`);
  await page.waitForFunction(
    () =>
      !document.body.innerText.includes('Loading your session')
      && !document.querySelector('[data-testid="app-page-loader"]'),
    null,
    { timeout: 90000 },
  );
  await page.waitForSelector('.participant-app', { timeout: 45000 });
  return dashResponse?.status?.() ?? null;
}

function attachDiagnostics(page, bucket) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') bucket.consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => {
    bucket.pageErrors.push(String(err));
  });
  page.on('requestfailed', (req) => {
    bucket.failedRequests.push({
      url: req.url(),
      method: req.method(),
      failure: req.failure()?.errorText || 'unknown',
    });
  });
}

async function gotoSafe(page, url) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      return response;
    } catch (error) {
      if (attempt === 2) throw error;
      await page.waitForTimeout(1500);
    }
  }
  return null;
}

async function waitForParticipantAppReady(page) {
  await page.waitForFunction(
    () => {
      const loader = document.querySelector('[data-testid="app-page-loader"]');
      if (loader) return false;
      if (window.location.pathname.includes('/participant/sign-in')) return false;
      return !!document.querySelector('.participant-app');
    },
    null,
    { timeout: 45000 },
  );
}

async function readPageDiagnostics(page) {
  return page.evaluate(() => {
    const token = localStorage.getItem('nc3_token');
    const themeLast = localStorage.getItem('nc3_participant_theme_last_id');
    const themes = localStorage.getItem('nc3_participant_themes');
    const keys = Object.keys(localStorage).filter(k =>
      k.startsWith('nc3_') || k.includes('participant'),
    );
    const mainText = (document.body?.innerText || '').slice(0, 2500);
    return {
      url: window.location.href,
      title: document.title,
      mainTextPreview: mainText,
      auth: {
        hasToken: !!token,
        tokenLength: token ? token.length : 0,
      },
      theme: {
        themeLast,
        themesRaw: themes,
        lightShell: !!document.querySelector('.participant-app--light'),
        darkShell: !!document.querySelector('.participant-app--dark'),
        participantThemeDataset: document.documentElement.dataset.participantTheme || null,
      },
      localStorageKeys: keys,
      sessionStorageKeys: Object.keys(sessionStorage),
      hasBegin: !!document.querySelector('[data-testid="typing-begin-test"]'),
      hasPassage: !!document.querySelector('[data-testid="typing-passage"]'),
      hasLoader: !!document.querySelector('[data-testid="app-page-loader"]'),
      lockedModule: (document.body?.innerText || '').includes('Already Completed Today'),
    };
  });
}

function saveFailureArtifacts(page, prefix = 'typing_mobile_light') {
  mkdirSync(ARTIFACTS_DIR, { recursive: true });
  const pngPath = join(ARTIFACTS_DIR, `${prefix}.png`);
  const htmlPath = join(ARTIFACTS_DIR, `${prefix}.html`);
  return page.screenshot({ path: pngPath, fullPage: true }).then(async () => {
    const html = await page.content();
    writeFileSync(htmlPath, html, 'utf8');
    return { pngPath, htmlPath };
  });
}

async function logTypingFailure(page, diagnostics, navigationStatus, error) {
  const pageState = await readPageDiagnostics(page).catch(() => ({}));
  const payload = {
    error: String(error),
    navigationStatus,
    page: pageState,
    diagnostics,
  };
  console.error(JSON.stringify(payload, null, 2));
  const paths = await saveFailureArtifacts(page).catch(() => ({}));
  if (paths.pngPath) console.error(`Screenshot: ${paths.pngPath}`);
  if (paths.htmlPath) console.error(`HTML: ${paths.htmlPath}`);
}

async function clearParticipantStorage(page) {
  await page.evaluate(() => {
    const keep = [];
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith('nc3_')) localStorage.removeItem(key);
    }
    sessionStorage.clear();
  });
}

async function loginParticipant(page, publicId) {
  await gotoSafe(page, `${BASE}/participant/sign-in`);
  await page.getByPlaceholder('NC-XXXXXXXXXXXXXXXX').waitFor({ state: 'visible', timeout: 60000 });
  await page.getByPlaceholder('NC-XXXXXXXXXXXXXXXX').fill(publicId);
  await page.getByPlaceholder('4–6 digit PIN').fill('2468');
  const loginResponsePromise = page.waitForResponse(
    (resp) =>
      resp.url().includes('/v1/auth/participant/login')
      && resp.request().method() === 'POST',
    { timeout: 60000 },
  );
  await page.getByRole('button', { name: /Sign In/i }).click();
  const loginResponse = await loginResponsePromise;
  if (!loginResponse.ok()) {
    const body = await loginResponse.text().catch(() => '');
    throw new Error(`participant login HTTP ${loginResponse.status()}: ${body.slice(0, 400)}`);
  }
  await page.waitForFunction(
    () =>
      !window.location.pathname.includes('/participant/sign-in')
      && !!localStorage.getItem('nc3_token'),
    null,
    { timeout: 60000 },
  );
  await waitForParticipantAppReady(page);
}

async function applyLightTheme(page, publicId) {
  await page.evaluate((pid) => {
    localStorage.setItem('nc3_participant_theme_last_id', pid);
    const map = JSON.parse(localStorage.getItem('nc3_participant_themes') || '{}');
    map[pid] = 'light';
    localStorage.setItem('nc3_participant_themes', JSON.stringify(map));
    const vars = {
      '--pt-bg': '#e8eef5',
      '--pt-text': '#0f172a',
      '--pt-muted': '#475569',
    };
    Object.entries(vars).forEach(([k, v]) => document.documentElement.style.setProperty(k, v));
    document.body.style.backgroundColor = vars['--pt-bg'];
    document.body.style.color = vars['--pt-text'];
  }, publicId);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await waitForParticipantAppReady(page);
  await page.waitForSelector('.participant-app--light', { timeout: 20000 });
}

async function ensureTypingIntroOrActive(page) {
  const begin = page.getByTestId('typing-begin-test');
  if (await begin.isVisible().catch(() => false)) {
    await begin.click();
    await page.waitForSelector('[data-testid="typing-passage"]', { timeout: 20000 });
    return 'intro_clicked';
  }
  const passage = page.locator('[data-testid="typing-passage"]');
  if (await passage.isVisible().catch(() => false)) {
    return 'already_active';
  }
  if (await page.getByText('Already Completed Today').isVisible().catch(() => false)) {
    throw new Error('typing_module_locked_already_completed_today');
  }
  if (page.url().includes('/participant/sign-in')) {
    throw new Error('redirected_to_sign_in');
  }
  if (page.url().includes('/participant/schedule')) {
    throw new Error('redirected_to_schedule');
  }
  if (page.url().includes('/participant/consent')) {
    throw new Error('redirected_to_consent');
  }
  if (page.url().includes('/participant/change-pin')) {
    throw new Error('redirected_to_change_pin');
  }
  throw new Error('typing_intro_and_passage_not_found');
}

async function runTypingMobileLightCheck(browser) {
  const { publicId, accessToken } = bootstrapParticipant();
  const diagnostics = { consoleErrors: [], pageErrors: [], failedRequests: [] };
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const page = await context.newPage();
  attachDiagnostics(page, diagnostics);

  let navigationStatus = null;
  try {
    await seedParticipantAuth(page, { publicId, accessToken });
    await applyLightTheme(page, publicId);

    const navResponse = await gotoSafe(page, `${BASE}${TYPING_ROUTE}`);
    navigationStatus = navResponse?.status?.() ?? null;
    await waitForParticipantAppReady(page);

    await page.waitForSelector(
      '[data-testid="typing-begin-test"], [data-testid="typing-passage"]',
      { timeout: 20000 },
    );
    await ensureTypingIntroOrActive(page);

    const passage = page.locator('[data-testid="typing-passage"]');
    await passage.waitFor({ state: 'visible', timeout: 20000 });

    const input = page.locator('input[aria-label="Typing input"]');
    await input.focus();

    const beforeMetrics = await page.evaluate(() => {
      const passageEl = document.querySelector('[data-testid="typing-passage"]');
      return {
        overflowX: passageEl ? getComputedStyle(passageEl).overflowX : null,
        overflowY: passageEl ? getComputedStyle(passageEl).overflowY : null,
        whiteSpace: passageEl ? getComputedStyle(passageEl).whiteSpace : null,
        scrollWidth: passageEl?.scrollWidth ?? 0,
        clientWidth: passageEl?.clientWidth ?? 0,
        scrollTop: passageEl?.scrollTop ?? 0,
      };
    });

    await page.keyboard.type('abcdefghijklmnopqrstuvwxyz', { delay: 15 });
    await page.keyboard.press('Backspace');

    const afterMetrics = await page.evaluate(() => {
      const passageEl = document.querySelector('[data-testid="typing-passage"]');
      const inputEl = document.querySelector('input[aria-label="Typing input"]');
      const doc = document.documentElement;
      return {
        scrollTop: passageEl?.scrollTop ?? 0,
        scrollWidth: passageEl?.scrollWidth ?? 0,
        clientWidth: passageEl?.clientWidth ?? 0,
        horizontalOverflow: doc.scrollWidth <= doc.clientWidth + 2,
        focused: document.activeElement === inputEl,
        lightShell: !!document.querySelector('.participant-app--light'),
      };
    });

    const ok =
      beforeMetrics.overflowX === 'hidden'
      && (beforeMetrics.overflowY === 'auto' || beforeMetrics.overflowY === 'scroll')
      && beforeMetrics.whiteSpace === 'pre-wrap'
      && beforeMetrics.scrollWidth <= beforeMetrics.clientWidth + 2
      && afterMetrics.focused
      && afterMetrics.lightShell
      && afterMetrics.horizontalOverflow;

    return {
      name: 'typing_mobile_light',
      ok,
      detail: {
        publicId,
        navigationStatus,
        beforeMetrics,
        afterMetrics,
        autoScrollMoved: afterMetrics.scrollTop >= beforeMetrics.scrollTop,
      },
    };
  } catch (error) {
    await logTypingFailure(page, diagnostics, navigationStatus, error);
    return {
      name: 'typing_mobile_light',
      ok: false,
      detail: {
        error: String(error),
        navigationStatus,
        diagnostics,
        ...(await readPageDiagnostics(page).catch(() => ({}))),
      },
    };
  } finally {
    await context.close();
  }
}

async function auditRoute(page, route, theme, width) {
  await page.setViewportSize({ width, height: 900 });
  await gotoSafe(page, `${BASE}${route}`);
  if (page.url().includes('/participant/sign-in')) {
    return { route, theme, width, overflow: false, darkPanel: true, lightShell: false, bg: 'redirected_sign_in' };
  }
  await page.evaluate((t) => {
    const id = localStorage.getItem('nc3_participant_theme_last_id');
    const map = JSON.parse(localStorage.getItem('nc3_participant_themes') || '{}');
    if (id) map[id] = t;
    localStorage.setItem('nc3_participant_themes', JSON.stringify(map));
    const vars =
      t === 'light'
        ? { '--pt-bg': '#e8eef5', '--pt-text': '#0f172a', '--pt-muted': '#475569' }
        : { '--pt-bg': '#060910', '--pt-text': '#e2e8f0', '--pt-muted': '#a0aec0' };
    Object.entries(vars).forEach(([k, v]) => document.documentElement.style.setProperty(k, v));
    if (document.body) {
      document.body.style.backgroundColor = vars['--pt-bg'];
      document.body.style.color = vars['--pt-text'];
    }
  }, theme);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('.participant-app', { timeout: 20000 }).catch(() => null);
  await page.waitForTimeout(500);
  return page.evaluate(({ theme, width, routePath }) => {
    const doc = document.documentElement;
    const overflow = doc.scrollWidth <= doc.clientWidth + 2;
    const shell = document.querySelector('.participant-app');
    const bgEl = shell || document.body;
    const bg = getComputedStyle(bgEl).backgroundColor;
    const rgb = bg.match(/\d+/g)?.map(Number) || [0, 0, 0];
    const lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
    const lightShell = !!document.querySelector('.participant-app--light');
    const darkShell = !!document.querySelector('.participant-app--dark');
    const darkPanel =
      theme === 'light' && (lum < 0.35 || (!lightShell && darkShell));
    return { route: routePath, theme, width, overflow, darkPanel, lightShell, bg };
  }, { theme, width, routePath: route });
}

async function runFullMatrix(browser) {
  const { publicId, accessToken } = bootstrapParticipant();
  const context = await browser.newContext();
  const page = await context.newPage();
  await seedParticipantAuth(page, { publicId, accessToken });
  await page.evaluate((pid) => {
    localStorage.setItem('nc3_participant_theme_last_id', pid);
  }, publicId);

  const checks = [];
  for (const theme of ['light', 'dark']) {
    for (const width of WIDTHS) {
      for (const route of ROUTES) {
        const result = await auditRoute(page, route, theme, width);
        checks.push({
          name: `${theme}_${width}_${route}`,
          ok: result.overflow && !result.darkPanel,
          detail: result,
        });
      }
    }
  }

  const typingCheck = await runTypingMobileLightCheck(browser);
  checks.push(typingCheck);
  await context.close();
  return checks;
}

async function main() {
  const only = parseOnlyMode(process.argv.slice(2));
  const browser = await chromium.launch({ headless: true });

  let checks;
  if (only === 'typing_mobile_light') {
    checks = [await runTypingMobileLightCheck(browser)];
  } else if (only) {
    console.error(JSON.stringify({ ok: false, error: `unknown --only mode: ${only}` }));
    await browser.close();
    process.exit(1);
  } else {
    checks = await runFullMatrix(browser);
  }

  await browser.close();
  const ok = checks.every((c) => c.ok);
  const failed = checks.filter((c) => !c.ok);
  console.log(JSON.stringify({ ok, failed, total: checks.length }, null, 2));
  process.exit(ok ? 0 : 2);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
