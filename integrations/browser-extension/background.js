/* RAGbase Shield browser extension: service worker.
 *
 * The only network peer is the local Shield Desk API on http://127.0.0.1:<port> (default 7878),
 * with the per-install token in the X-Shield-Token header. Nothing else is contacted.
 *
 * Message types:
 *   shield:mask         {text}           from provider pages (content.js) and extension pages
 *   shield:openOptions  {}               from provider pages and extension pages
 *   shield:status       {}               extension pages only (options, side panel)
 *   shield:dossiers     {}               extension pages only (returns real dossier titles)
 *   shield:restore      {text, dossier}  extension pages only: real names never go to a provider page
 */
'use strict';

const DEFAULTS = Object.freeze({ enabled: true, port: 7878, token: '', dossier: '' });
// "chrome-extension://<id>/". Compared as a prefix: URL.origin is "null" for this scheme outside Chrome.
const EXT_PREFIX = chrome.runtime.getURL('');
const MAX_TEXT = 5000000; // characters
const CONTENT_ALLOWED = new Set(['shield:mask', 'shield:openOptions']);

class DeskError extends Error {
  constructor(code, status) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

function openPanelOnActionClick() {
  try {
    const p = chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
    if (p && typeof p.catch === 'function') p.catch(() => {});
  } catch (_) {
    /* sidePanel API not available */
  }
}

openPanelOnActionClick();

chrome.runtime.onInstalled.addListener((details) => {
  openPanelOnActionClick();
  if (details && details.reason === 'install') {
    chrome.runtime.openOptionsPage();
  }
});

async function getSettings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

function validPort(value) {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1024 && n <= 65535 ? n : DEFAULTS.port;
}

async function callDesk(path, { method = 'GET', body, timeoutMs = 10000 } = {}) {
  const settings = await getSettings();
  if (!settings.token) throw new DeskError('NO_TOKEN');
  const headers = { 'X-Shield-Token': String(settings.token) };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`http://127.0.0.1:${validPort(settings.port)}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      credentials: 'omit',
      cache: 'no-store',
      redirect: 'error',
      referrerPolicy: 'no-referrer',
    });
  } catch (err) {
    throw new DeskError(err && err.name === 'AbortError' ? 'DESK_TIMEOUT' : 'DESK_DOWN');
  } finally {
    clearTimeout(timer);
  }
  if (res.status === 401 || res.status === 403) throw new DeskError('BAD_TOKEN', res.status);
  if (!res.ok) throw new DeskError('DESK_ERROR', res.status);
  try {
    return await res.json();
  } catch (_) {
    throw new DeskError('DESK_ERROR', res.status);
  }
}

function countFound(reply) {
  if (Array.isArray(reply.found)) return reply.found.length;
  if (reply.counts && typeof reply.counts === 'object') {
    return Object.values(reply.counts).reduce((sum, n) => sum + (Number(n) || 0), 0);
  }
  return 0;
}

const handlers = {
  async 'shield:mask'(msg) {
    const text = typeof msg.text === 'string' ? msg.text : '';
    if (!text) return { ok: true, masked: '', count: 0 };
    if (text.length > MAX_TEXT) throw new DeskError('TOO_LARGE');
    const settings = await getSettings();
    const body = { text };
    if (settings.dossier) body.dossier = String(settings.dossier);
    const reply = await callDesk('/api/mask', { method: 'POST', body, timeoutMs: 30000 });
    if (!reply || typeof reply.masked !== 'string') throw new DeskError('DESK_ERROR');
    return { ok: true, masked: reply.masked, count: countFound(reply) };
  },

  async 'shield:openOptions'() {
    await chrome.runtime.openOptionsPage();
    return { ok: true };
  },

  async 'shield:status'() {
    const status = await callDesk('/api/status', { timeoutMs: 4000 });
    return { ok: true, status };
  },

  async 'shield:dossiers'() {
    const list = await callDesk('/api/dossiers');
    return { ok: true, dossiers: Array.isArray(list) ? list : [] };
  },

  async 'shield:restore'(msg) {
    const dossier = typeof msg.dossier === 'string' ? msg.dossier : '';
    if (!dossier) throw new DeskError('NO_DOSSIER');
    const text = typeof msg.text === 'string' ? msg.text : '';
    if (text.length > MAX_TEXT) throw new DeskError('TOO_LARGE');
    const reply = await callDesk('/api/restore', {
      method: 'POST',
      body: { text, dossier },
      timeoutMs: 30000,
    });
    if (!reply || typeof reply.text !== 'string') throw new DeskError('DESK_ERROR');
    return {
      ok: true,
      text: reply.text,
      unknownCodes: Array.isArray(reply.unknown_codes) ? reply.unknown_codes : [],
      restored: Number(reply.restored) || 0,
    };
  },
};

function isExtensionPage(sender) {
  return (
    Boolean(sender) &&
    sender.id === chrome.runtime.id &&
    typeof sender.url === 'string' &&
    EXT_PREFIX.length > 0 &&
    sender.url.startsWith(EXT_PREFIX)
  );
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const type = msg && typeof msg.type === 'string' ? msg.type : '';
  if (!Object.prototype.hasOwnProperty.call(handlers, type)) return false;
  if (!CONTENT_ALLOWED.has(type) && !isExtensionPage(sender)) {
    sendResponse({ ok: false, error: 'FORBIDDEN' });
    return false;
  }
  handlers[type](msg, sender).then(sendResponse, (err) => {
    sendResponse({
      ok: false,
      error: err instanceof DeskError ? err.code : 'INTERNAL',
      status: err && err.status,
    });
  });
  return true; // async response
});
