/* Shared helpers for the extension's own pages (options, side panel). No external libraries. */
'use strict';

const SHIELD_DEFAULTS = Object.freeze({ enabled: true, port: 7878, token: '', dossier: '' });

function t(key, subs) {
  return chrome.i18n.getMessage(key, subs) || key;
}

/** Fill every [data-i18n] text, [data-i18n-placeholder] and [data-i18n-title] from _locales. */
function localizePage() {
  const lang = (chrome.i18n.getUILanguage() || 'fr').toLowerCase().startsWith('fr') ? 'fr' : 'en';
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder));
  });
  document.querySelectorAll('[data-i18n-title]').forEach((el) => {
    el.setAttribute('title', t(el.dataset.i18nTitle));
  });
}

function sendToWorker(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (reply) => {
      if (chrome.runtime.lastError || !reply) resolve({ ok: false, error: 'EXTENSION' });
      else resolve(reply);
    });
  });
}

function statusText(reply) {
  if (reply.ok) {
    const version = reply.status && reply.status.version ? String(reply.status.version) : '?';
    return t('statusOk', [version]);
  }
  const keys = {
    DESK_DOWN: 'statusDown',
    DESK_TIMEOUT: 'statusTimeout',
    NO_TOKEN: 'statusNoToken',
    BAD_TOKEN: 'statusBadToken',
  };
  return t(keys[reply.error] || 'statusError');
}

/** Fill a <select> with dossiers. Titles are real values: they stay in this extension page. */
function fillDossiers(select, dossiers, selected, firstOption) {
  select.textContent = '';
  const none = document.createElement('option');
  none.value = '';
  none.textContent = firstOption;
  select.append(none);
  for (const d of dossiers) {
    if (!d || typeof d.code !== 'string') continue;
    const opt = document.createElement('option');
    opt.value = d.code;
    opt.textContent = d.title ? `${d.code} · ${d.title}` : d.code;
    select.append(opt);
  }
  if (selected && [...select.options].some((o) => o.value === selected)) select.value = selected;
}
