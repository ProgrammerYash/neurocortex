/**
 * Phase 5I fake-user API E2E + timings (reads golden code locally; never logs PINs).
 */
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BACKEND = join(__dirname, '..');
const API = process.env.API_URL || 'http://127.0.0.1:8000/v1';
const PYTHON = process.env.BROWSER_VERIFY_PYTHON || join(BACKEND, '.venv', 'Scripts', 'python.exe');
const CODE_PATH = join(BACKEND, '.golden_vault_local');

async function api(path, { method = 'GET', token, body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { status: res.status, data };
}

async function main() {
  const report = { ok: false, timings: {}, checks: [] };
  const code = readFileSync(CODE_PATH, 'utf8').trim();
  if (!code) {
    console.log(JSON.stringify({ ok: false, error: 'missing .golden_vault_local' }, null, 2));
    process.exit(1);
  }

  const login = await api('/golden-vault/login', { method: 'POST', body: { code } });
  if (login.status !== 200) {
    console.log(JSON.stringify({ ok: false, error: 'golden login failed', login }, null, 2));
    process.exit(1);
  }
  const token = login.data.access_token;

  const warmStart = performance.now();
  await api('/golden-vault/participants?limit=50&offset=0', { token });
  report.timings.warmGoldenVaultListMs = Math.round(performance.now() - warmStart);

  const previewStart = performance.now();
  const previewBody = {
    total: 10,
    start_date: '2026-01-10',
    daily: 3,
    weekly: 2,
    two_days: 3,
    four_days: 2,
  };
  const preview = await api('/golden-vault/fake-users/preview', {
    method: 'POST',
    token,
    body: previewBody,
  });
  report.timings.fakeUserPreviewMs = Math.round(performance.now() - previewStart);
  report.checks.push({ name: 'preview_ok', ok: preview.status === 200 });

  const genStart = performance.now();
  const created = await api('/golden-vault/fake-users/generate', {
    method: 'POST',
    token,
    body: { ...previewBody, idempotency_key: crypto.randomUUID() },
  });
  if (created.status !== 200) {
    console.log(JSON.stringify({ ok: false, error: 'generate failed', created }, null, 2));
    process.exit(1);
  }
  const batchId = created.data.batchId;
  let status = created.data.status;
  while (!['completed', 'completed_with_errors', 'failed'].includes(status)) {
    const step = await api(`/golden-vault/fake-users/batches/${batchId}/process`, {
      method: 'POST',
      token,
    });
    status = step.data.status;
  }
  report.timings.tenUserGenerationMs = Math.round(performance.now() - genStart);

  const batch = await api(`/golden-vault/fake-users/batches/${batchId}`, { token });
  report.checks.push({
    name: 'ten_users_created',
    ok: batch.data.successfulCount === 10 && batch.data.processedCount === 10,
    detail: batch.data,
  });

  const cred1 = await api(`/golden-vault/fake-users/batches/${batchId}/credentials`, { token });
  const cred2 = await api(`/golden-vault/fake-users/batches/${batchId}/credentials`, { token });
  const credentials = cred1.data?.credentials || [];
  report.checks.push({ name: 'credentials_once', ok: cred1.status === 200 && credentials.length === 10 });
  report.checks.push({ name: 'credentials_410_second', ok: cred2.status === 410 });
  const publicIds = credentials.map((c) => c.publicId).filter(Boolean);
  report.checks.push({
    name: 'unique_public_ids',
    ok: new Set(publicIds).size === 10,
  });

  const listed = await api(`/golden-vault/participants?synthetic_batch_id=${batchId}&limit=50`, { token });
  report.checks.push({ name: 'vault_batch_filter', ok: listed.data?.total === 10 });

  const verify = spawnSync(
    PYTHON,
    [
      join(BACKEND, 'scripts', 'verify_fake_user_batch.py'),
      batchId,
      publicIds.join(','),
    ],
    { encoding: 'utf8', cwd: BACKEND },
  );
  let dbVerify = {};
  try {
    dbVerify = JSON.parse(verify.stdout.trim() || '{}');
  } catch {
    dbVerify = { ok: false, stderr: verify.stderr };
  }
  report.checks.push({ name: 'db_verify', ok: dbVerify.ok === true, detail: dbVerify });

  report.ok = report.checks.every((c) => c.ok);
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.ok ? 0 : 2);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
