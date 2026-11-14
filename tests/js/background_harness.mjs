// Runs integrations/browser-extension/background.js in a Node vm with a fake `chrome` and a fake
// `fetch` (no network). Called by tests/test_integrations.py. Exit code 0 = all checks passed.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync(process.argv[2], 'utf8');
const EXT = 'chrome-extension://shieldtestid';
const CONTENT = { id: 'shieldtestid', url: 'https://chatgpt.com/c/123', tab: { id: 7 } };
const PAGE = { id: 'shieldtestid', url: `${EXT}/sidepanel.html` };
const OPTIONS_TAB = { id: 'shieldtestid', url: `${EXT}/options.html`, tab: { id: 9 } };

function env(storage, fetchImpl) {
  const calls = [];
  let onMessage = null;
  const chrome = {
    runtime: {
      id: 'shieldtestid',
      getURL: (p = '') => `${EXT}/${p}`,
      onInstalled: { addListener() {} },
      onMessage: { addListener(fn) { onMessage = fn; } },
      openOptionsPage: async () => { calls.push({ openOptions: true }); },
    },
    storage: { local: { get: async (defaults) => ({ ...defaults, ...storage }) } },
    sidePanel: { setPanelBehavior: async () => {} },
  };
  const fetch = async (url, opts) => {
    calls.push({ url, opts });
    return fetchImpl(url, opts);
  };
  const ctx = vm.createContext({ chrome, fetch, URL, AbortController, setTimeout, clearTimeout, console });
  vm.runInContext(code, ctx, { filename: 'background.js' });
  const send = (msg, sender) =>
    new Promise((resolve) => {
      let answered = false;
      const keepOpen = onMessage(msg, sender, (reply) => {
        answered = true;
        resolve(reply);
      });
      if (keepOpen !== true && !answered) resolve(undefined);
    });
  return { send, calls };
}

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } });

let checks = 0;
const ok = () => { checks += 1; };

// 1. Mask from a provider page: goes to 127.0.0.1 with the token and the chosen dossier.
{
  const e = env({ token: 'tok-123', dossier: 'DOSSIER_2' }, () =>
    json({ masked: 'Voir PERSONNE_A.', found: [{ code: 'PERSONNE_A', kind: 'PERSON' }], counts: { PERSON: 1 } }));
  const r = await e.send({ type: 'shield:mask', text: 'Voir Synthétique Testperson.' }, CONTENT);
  assert.deepEqual({ ...r }, { ok: true, masked: 'Voir PERSONNE_A.', count: 1 });
  assert.equal(e.calls.length, 1);
  assert.equal(e.calls[0].url, 'http://127.0.0.1:7878/api/mask');
  assert.equal(e.calls[0].opts.method, 'POST');
  assert.equal(e.calls[0].opts.headers['X-Shield-Token'], 'tok-123');
  assert.equal(e.calls[0].opts.credentials, 'omit');
  assert.deepEqual(JSON.parse(e.calls[0].opts.body), { text: 'Voir Synthétique Testperson.', dossier: 'DOSSIER_2' });
  ok();
}

// 2. Restore and dossier list are refused to provider pages (real values never reach their DOM).
for (const type of ['shield:restore', 'shield:dossiers', 'shield:status']) {
  const e = env({ token: 'tok' }, () => json({ text: 'secret' }));
  const r = await e.send({ type, text: 'PERSONNE_A', dossier: 'DOSSIER_1' }, CONTENT);
  assert.equal(r.ok, false);
  assert.equal(r.error, 'FORBIDDEN');
  assert.equal(e.calls.length, 0, `${type} must not call the Desk for a content script`);
  ok();
}

// 3. A sender that claims our id but has another origin is refused too.
{
  const e = env({ token: 'tok' }, () => json({ text: 'x' }));
  const r = await e.send({ type: 'shield:restore', text: 'A', dossier: 'DOSSIER_1' },
    { id: 'shieldtestid', url: 'chrome-extension://otherid/sidepanel.html' });
  assert.equal(r.error, 'FORBIDDEN');
  assert.equal(e.calls.length, 0);
  ok();
}

// 4. Restore from the side panel and from the options tab works; fields are mapped.
for (const sender of [PAGE, OPTIONS_TAB]) {
  const e = env({ token: 'tok' }, () => json({ text: 'Bonjour Synthétique.', unknown_codes: ['PERSONNE_Z'], restored: 2 }));
  const r = await e.send({ type: 'shield:restore', text: 'Bonjour PERSONNE_A.', dossier: 'DOSSIER_1' }, sender);
  assert.deepEqual({ ...r, unknownCodes: [...r.unknownCodes] },
    { ok: true, text: 'Bonjour Synthétique.', unknownCodes: ['PERSONNE_Z'], restored: 2 });
  assert.equal(e.calls[0].url, 'http://127.0.0.1:7878/api/restore');
  ok();
}

// 5. Restore without a dossier is refused before any call.
{
  const e = env({ token: 'tok' }, () => json({}));
  const r = await e.send({ type: 'shield:restore', text: 'x', dossier: '' }, PAGE);
  assert.equal(r.error, 'NO_DOSSIER');
  assert.equal(e.calls.length, 0);
  ok();
}

// 6. Desk not running -> DESK_DOWN (content.js then blocks the raw paste).
{
  const e = env({ token: 'tok' }, () => { throw new TypeError('Failed to fetch'); });
  const r = await e.send({ type: 'shield:mask', text: 'abc' }, CONTENT);
  assert.deepEqual({ ...r }, { ok: false, error: 'DESK_DOWN', status: undefined });
  ok();
}

// 7. No token -> NO_TOKEN without any call; wrong token -> BAD_TOKEN; server error -> DESK_ERROR.
{
  const e = env({}, () => json({}));
  const r = await e.send({ type: 'shield:mask', text: 'abc' }, CONTENT);
  assert.equal(r.error, 'NO_TOKEN');
  assert.equal(e.calls.length, 0);
  ok();
}
{
  const e = env({ token: 'bad' }, () => json({ error: 'forbidden' }, 403));
  const r = await e.send({ type: 'shield:mask', text: 'abc' }, CONTENT);
  assert.equal(r.error, 'BAD_TOKEN');
  ok();
}
{
  const e = env({ token: 'tok' }, () => json({ error: 'engine' }, 500));
  const r = await e.send({ type: 'shield:mask', text: 'abc' }, CONTENT);
  assert.equal(r.error, 'DESK_ERROR');
  ok();
}
{
  // A reply without "masked" is an error, never a pass-through of the raw text.
  const e = env({ token: 'tok' }, () => json({ text: 'abc' }));
  const r = await e.send({ type: 'shield:mask', text: 'abc' }, CONTENT);
  assert.equal(r.ok, false);
  assert.equal(r.error, 'DESK_ERROR');
  ok();
}

// 8. Port from the options; an invalid port falls back to 7878. No dossier -> no dossier field.
{
  const e = env({ token: 'tok', port: 9123 }, () => json({ masked: '', counts: { EMAIL: 2, PHONE: 1 } }));
  const r = await e.send({ type: 'shield:mask', text: 'x' }, CONTENT);
  assert.equal(e.calls[0].url, 'http://127.0.0.1:9123/api/mask');
  assert.deepEqual(JSON.parse(e.calls[0].opts.body), { text: 'x' });
  assert.equal(r.count, 3);
  ok();
}
{
  const e = env({ token: 'tok', port: 'abc' }, () => json({ masked: 'x' }));
  await e.send({ type: 'shield:mask', text: 'x' }, CONTENT);
  assert.equal(e.calls[0].url, 'http://127.0.0.1:7878/api/mask');
  ok();
}

// 9. Empty text: nothing to send. Unknown message: no answer.
{
  const e = env({ token: 'tok' }, () => json({}));
  const r = await e.send({ type: 'shield:mask', text: '' }, CONTENT);
  assert.deepEqual({ ...r }, { ok: true, masked: '', count: 0 });
  assert.equal(e.calls.length, 0);
  const u = await e.send({ type: 'shield:unmask', text: 'x' }, CONTENT);
  assert.equal(u, undefined);
  ok();
}

// 10. Status + dossiers from the options page.
{
  const e = env({ token: 'tok' }, (url) =>
    url.endsWith('/api/status') ? json({ version: '0.4.1' }) : json([{ code: 'DOSSIER_1', title: 'Synthétique c. Exemple' }]));
  const s = await e.send({ type: 'shield:status' }, OPTIONS_TAB);
  assert.equal(s.ok, true);
  assert.equal(s.status.version, '0.4.1');
  const d = await e.send({ type: 'shield:dossiers' }, PAGE);
  assert.equal(d.dossiers[0].code, 'DOSSIER_1');
  assert.ok(e.calls.every((c) => c.url.startsWith('http://127.0.0.1:')));
  ok();
}

console.log(`OK ${checks}`);
