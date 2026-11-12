/* Side panel: paste an AI answer, choose the dossier, restore the real names LOCALLY.
 * The restored text is shown here only. Nothing is written into the provider page. */
'use strict';

const $ = (id) => document.getElementById(id);

function setMessage(text, kind) {
  const el = $('message');
  el.textContent = text || '';
  el.className = `status ${kind || ''}`;
}

function clearResult() {
  $('output').value = '';
  $('resultBox').hidden = true;
  $('unknown').hidden = true;
  $('unknown').textContent = '';
}

async function refreshConnection() {
  const reply = await sendToWorker({ type: 'shield:status' });
  $('dot').className = `dot ${reply.ok ? 'ok' : 'err'}`;
  $('conn').textContent = statusText(reply);
  $('conn').className = `status ${reply.ok ? 'ok' : 'err'}`;
  return reply.ok;
}

async function loadDossiers() {
  const { dossier } = await chrome.storage.local.get(SHIELD_DEFAULTS);
  const reply = await sendToWorker({ type: 'shield:dossiers' });
  fillDossiers($('dossier'), reply.ok ? reply.dossiers : [], dossier, t('spChoose'));
}

async function restore() {
  const text = $('input').value;
  const dossier = $('dossier').value;
  clearResult();
  if (!dossier) return setMessage(t('spNeedDossier'), 'err');
  if (!text.trim()) return setMessage(t('spEmpty'), 'err');
  $('restore').disabled = true;
  try {
    const reply = await sendToWorker({ type: 'shield:restore', text, dossier });
    if (!reply.ok) return setMessage(statusText(reply), 'err');
    $('output').value = reply.text;
    $('resultBox').hidden = false;
    setMessage(t('spRestored', [String(reply.restored)]), 'ok');
    if (reply.unknownCodes.length) {
      $('unknown').textContent = t('spUnknown', [reply.unknownCodes.join(', ')]);
      $('unknown').hidden = false;
    }
  } finally {
    $('restore').disabled = false;
  }
}

async function copyResult() {
  const value = $('output').value;
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
  } catch (_) {
    $('output').select();
    document.execCommand('copy');
  }
  const btn = $('copy');
  btn.textContent = t('spCopied');
  setTimeout(() => {
    btn.textContent = t('spCopy');
  }, 1500);
}

async function init() {
  localizePage();
  fillDossiers($('dossier'), [], '', t('spChoose'));
  $('restore').addEventListener('click', restore);
  $('copy').addEventListener('click', copyResult);
  $('clear').addEventListener('click', () => {
    $('input').value = '';
    clearResult();
    setMessage('');
  });
  $('options').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
  if (await refreshConnection()) loadDossiers();
}

init();
