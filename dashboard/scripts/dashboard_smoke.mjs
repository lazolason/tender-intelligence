import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdir, readFile, stat } from 'node:fs/promises';

import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dashboardDir = path.resolve(__dirname, '..');
const repoRoot = path.resolve(dashboardDir, '..');
const screenshotPath = path.join(repoRoot, 'output', 'playwright', 'dashboard-smoke.png');

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.manifest': 'application/manifest+json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function getContentType(filePath) {
  return MIME_TYPES[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
}

function parseClosingDate(value) {
  if (!value) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isTenderActive(tender) {
  const closing = parseClosingDate(tender?.closing_date);
  if (!closing) return true;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  closing.setHours(0, 0, 0, 0);
  return closing >= today;
}

async function createStaticServer(rootDir) {
  const server = http.createServer(async (req, res) => {
    try {
      const requestUrl = new URL(req.url || '/', 'http://127.0.0.1');
      let relativePath = decodeURIComponent(requestUrl.pathname);
      if (relativePath === '/') relativePath = '/index.html';

      const resolvedPath = path.resolve(rootDir, `.${relativePath}`);
      if (!resolvedPath.startsWith(rootDir)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
      }

      const fileInfo = await stat(resolvedPath).catch(() => null);
      if (!fileInfo || !fileInfo.isFile()) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }

      const body = await readFile(resolvedPath);
      res.writeHead(200, {
        'Content-Type': getContentType(resolvedPath),
        'Cache-Control': 'no-store',
      });
      res.end(body);
    } catch (error) {
      res.writeHead(500);
      res.end(String(error));
    }
  });

  await new Promise((resolve, reject) => {
    server.listen(0, '127.0.0.1', (error) => {
      if (error) reject(error);
      else resolve();
    });
  });

  const address = server.address();
  if (!address || typeof address === 'string') {
    throw new Error('Could not determine static server port');
  }

  return {
    server,
    origin: `http://127.0.0.1:${address.port}`,
  };
}

function expect(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function run() {
  const payloadPath = path.join(dashboardDir, 'tenders.json');
  const payload = JSON.parse(await readFile(payloadPath, 'utf8'));
  const tenders = Array.isArray(payload?.tenders) ? payload.tenders : [];
  const expectedSnapshotCount = tenders.length;
  const expectedActiveCount = tenders.filter(isTenderActive).length;
  const expectedRecentCount = Math.min(expectedSnapshotCount, 6);

  await mkdir(path.dirname(screenshotPath), { recursive: true });

  const { server, origin } = await createStaticServer(dashboardDir);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });
  const consoleMessages = [];

  page.on('console', (msg) => {
    consoleMessages.push({ type: msg.type(), text: msg.text() });
  });
  page.on('pageerror', (error) => {
    consoleMessages.push({ type: 'pageerror', text: error.message });
  });

  try {
    await page.goto(origin, { waitUntil: 'networkidle' });
    await page.locator('h1').waitFor();
    await page.locator('#sourceStats').waitFor();

    const pageTitle = (await page.locator('h1').textContent())?.trim() || '';
    expect(pageTitle.includes('Tender Intelligence'), 'Dashboard heading did not render');

    const sourceStats = await page.locator('#sourceStats').textContent();
    expect(
      String(sourceStats).includes(`Snapshot Matches: ${expectedSnapshotCount}`),
      `Unexpected source stats: ${sourceStats}`,
    );

    const displayedCount = Number((await page.locator('#displayedCount').textContent()) || '0');
    const totalCount = Number((await page.locator('#totalCount').textContent()) || '0');
    expect(totalCount === expectedSnapshotCount, `Expected totalCount=${expectedSnapshotCount}, got ${totalCount}`);
    expect(displayedCount === expectedActiveCount, `Expected displayedCount=${expectedActiveCount}, got ${displayedCount}`);

    if (expectedActiveCount === 0) {
      await page.locator('#activeEmptyState').waitFor();
      expect(await page.locator('#activeEmptyState').isVisible(), 'Empty-state panel should be visible');
      expect(await page.locator('#recentMatchesSection').isVisible(), 'Recent matches section should be visible');
      const recentItems = await page.locator('#recentTenderList .tender-item').count();
      expect(recentItems === expectedRecentCount, `Expected ${expectedRecentCount} recent matches, got ${recentItems}`);
    } else {
      const activeItems = await page.locator('#tenderList .tender-item').count();
      expect(activeItems > 0, 'Expected at least one active tender item');
    }

    const firstSummaryButton = page.locator('.tender-summary-btn').first();
    await firstSummaryButton.click();
    await page.locator('#summaryModal.active').waitFor();
    const modalTitle = (await page.locator('#modalTitle').textContent())?.trim() || '';
    expect(modalTitle.length > 0, 'Summary modal title should not be empty');
    await page.locator('#summaryModalClose').click();

    await page.locator('[data-tab="calendar"]').click();
    await page.locator('#calendar.active').waitFor();
    const calendarMonth = (await page.locator('#calendarMonth').textContent())?.trim() || '';
    expect(calendarMonth.length > 0, 'Calendar month label should not be empty');

    await page.screenshot({ path: screenshotPath, fullPage: true });

    const unexpectedConsole = consoleMessages.filter((entry) => ['error', 'pageerror'].includes(entry.type));
    expect(
      unexpectedConsole.length === 0,
      `Unexpected browser console errors:\n${unexpectedConsole.map((entry) => `${entry.type}: ${entry.text}`).join('\n')}`,
    );

    console.log(`dashboard smoke passed: ${origin}`);
    console.log(`screenshot: ${screenshotPath}`);
  } finally {
    await page.close().catch(() => {});
    await browser.close().catch(() => {});
    await new Promise((resolve, reject) => {
      server.close((error) => {
        if (error) reject(error);
        else resolve();
      });
    });
  }
}

run().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
