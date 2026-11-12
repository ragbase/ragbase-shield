/* Options page: token, Desk port, on/off, dossier choice. Values stay in chrome.storage.local. */
'use strict';

const $ = (id) => document.getElementById(id);
let savedTimer = 0;
let tokenTimer = 0;

function flashSaved() {
  const el = $('saved');
  el.textContent = t('optSaved');
  clearTimeout(savedTimer);
  savedTimer = setTimeout(() => {
    el.textContent = '';
  }, 1500);
}

async function save(patch) {
  await chrome.storage.local.set(patch);
  flashSaved();
}

function showStatus(reply) {
  const el = $('status');
  el.textContent = statusText(reply);
  el.className = `status ${reply.ok ? 'ok' : 'err'}`;
}

async function testConnection() {
  const el = $('status');
  el.textContent = t('statusChecking');
  el.className = 'status';
  const reply = await sendToWorker({ type: 'shield:status' });
  showStatus(reply);
  return reply.ok;
}

function showDossierWarning() {
  // Without a dossier the masking is temporary: registered names become [PERSONNE] and restore is impossible.
  $('dossierWarn').hidden = Boolean($('dossier').value);
}

async function reloadDossiers() {
  const { dossier } = await chrome.storage.local.get(SHIELD_DEFAULTS);
  const reply = await sendToWorker({ type: 'shield:dossiers' });
  fillDossiers($('dossier'), reply.ok ? reply.dossiers : [], dossier, t('optDossierNone'));
  showDossierWarning();
  if (!reply.ok) showStatus(reply);
}

async function init() {
  localizePage();
  const s = await chrome.storage.local.get(SHIELD_DEFAULTS);
  $('enabled').checked = s.enabled !== false;
  $('token').value = s.token || '';
  $('port').value = String(s.port || SHIELD_DEFAULTS.port);
  fillDossiers($('dossier'), [], s.dossier, t('optDossierNone'));
  showDossierWarning();

  $('enabled').addEventListener('change', (e) => save({ enabled: e.target.checked }));
  $('token').addEventListener('input', (e) => {
    clearTimeout(tokenTimer);
    const value = e.target.value.trim();
    tokenTimer = setTimeout(() => save({ token: value }), 400);
  });
  $('toggleToken').addEventListener('click', () => {
    const field = $('token');
    const show = field.type === 'password';
    field.type = show ? 'text' : 'password';
    $('toggleToken').textContent = t(show ? 'optHide' : 'optShow');
  });
  $('port').addEventListener('change', (e) => {
    const n = Number(e.target.value);
    if (Number.isInteger(n) && n >= 1024 && n <= 65535) save({ port: n });
    else e.target.value = String(SHIELD_DEFAULTS.port);
  });
  $('dossier').addEventListener('change', (e) => {
    showDossierWarning();
    save({ dossier: e.target.value });
  });
  $('test').addEventListener('click', async () => {
    clearTimeout(tokenTimer);
    await chrome.storage.local.set({ token: $('token').value.trim() });
    if (await testConnection()) reloadDossiers();
  });
  $('reload').addEventListener('click', reloadDossiers);

  if (s.token) {
    if (await testConnection()) reloadDossiers();
  }
}

init();
