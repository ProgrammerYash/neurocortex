import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const cssPath = join(dirname(fileURLToPath(import.meta.url)), 'golden-vault.css');

describe('golden-vault.css mobile layout', () => {
  it('prevents horizontal page overflow on the vault root', () => {
    const css = readFileSync(cssPath, 'utf8');
    expect(css).toMatch(/\.golden-vault-root[\s\S]*overflow-x:\s*hidden/);
    expect(css).toMatch(/\.golden-vault-table-wrap[\s\S]*overflow-x:\s*auto/);
  });

  it('defines compact table row classes', () => {
    const css = readFileSync(cssPath, 'utf8');
    expect(css).toContain('.golden-vault-table-row-compact');
    expect(css).toContain('.golden-vault-table-compact');
    expect(css).toContain('.golden-vault-manage-drawer');
  });
});
