/**
 * Phase 5H homepage viewport checks (real Chromium).
 */
import { chromium } from 'playwright';

const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const WIDTHS = [1440, 1280, 1024, 768, 390];

async function checkWidth(page, width) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
  await page.evaluate(() => window.scrollTo(0, 0));
  return page.evaluate(() => {
    const btn = document.querySelector('.home-btn--explore');
    const cs = btn ? getComputedStyle(btn) : null;
    const heroBtn = document.querySelector('.home-hero__actions button.home-btn--explore');
    const heroRA = document.querySelectorAll('.home-hero__actions button').length;
    const ctaRA = Array.from(document.querySelectorAll('.home-cta button')).some(
      b => b.textContent.trim() === 'Researcher Access',
    );
    const back = document.querySelector('.home-cta a.home-btn--top');
    return {
      width: innerWidth,
      exploreText: btn?.textContent?.trim() || null,
      exploreExact: btn?.textContent?.trim() === 'Explore the Research',
      clipped: btn ? btn.scrollWidth > btn.clientWidth + 1 : true,
      overflowHidden: cs?.overflow === 'hidden',
      textOverflow: cs?.textOverflow,
      ellipsis: cs?.textOverflow === 'ellipsis',
      pageOverflowX: Math.max(document.documentElement.scrollWidth - innerWidth, 0),
      heroResearcherButtons: heroRA,
      bottomResearcher: ctaRA,
      backTopUnderline: back ? getComputedStyle(back).textDecorationLine : null,
    };
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = [];
  for (const w of WIDTHS) {
    results.push({ viewport: w, ...(await checkWidth(page, w)) });
  }
  await browser.close();
  const ok = results.every(
    r =>
      r.exploreExact &&
      !r.clipped &&
      !r.ellipsis &&
      r.pageOverflowX === 0 &&
      r.heroResearcherButtons >= 4 &&
      r.bottomResearcher &&
      r.backTopUnderline === 'none',
  );
  console.log(JSON.stringify({ ok, results }, null, 2));
  process.exit(ok ? 0 : 1);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
