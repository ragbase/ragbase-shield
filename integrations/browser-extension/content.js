/* RAGbase Shield browser extension: content script for the AI chat sites.
 *
 * On a paste or a drag and drop of text into a prompt box (textarea, text input or contenteditable
 * editor) it:
 *   1. stops the paste or the drop before the page sees it,
 *   2. asks the service worker to mask the text through the local Shield Desk API (an HTML-only
 *      clipboard is turned into plain text first),
 *   3. inserts the MASKED text instead and shows a small badge with the count.
 * If Shield Desk cannot be reached it does NOT paste the raw text: it shows a panel with
 * "Paste anyway" (explicit user choice) and "Cancel".
 * A FILE pasted or dropped anywhere on the page is stopped too (Shield cannot mask a file the provider
 * uploads): a panel tells the user to connect the folder in Shield Desk; "Attach anyway" is an explicit choice.
 * A "beforeinput" listener is the second net for pastes and drops that reach an editor another way.
 *
 * This script never asks for restored text: real names are shown only in the extension's
 * side panel, never written into the provider page.
 */
(() => {
  'use strict';

  if (window.__ragbaseShieldContentLoaded) return;
  window.__ragbaseShieldContentLoaded = true;

  const BADGE_MS = 4000;
  const PANEL_MS = 60000;
  const TEXT_INPUT_TYPES = new Set(['', 'text', 'search', 'url']);

  function t(key, subs) {
    try {
      return chrome.i18n.getMessage(key, subs) || key;
    } catch (_) {
      return key;
    }
  }

  // ---- settings -------------------------------------------------------------------------
  let enabled = true;
  try {
    chrome.storage.local.get({ enabled: true }).then(
      (s) => {
        enabled = s.enabled !== false;
      },
      () => {}
    );
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'local' && changes.enabled) enabled = changes.enabled.newValue !== false;
    });
  } catch (_) {
    /* extension context gone: keep the default (on) */
  }

  // ---- editable targets -----------------------------------------------------------------
  function isTextField(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.tagName === 'TEXTAREA') return !el.readOnly && !el.disabled;
    if (el.tagName === 'INPUT') {
      const type = (el.getAttribute('type') || '').toLowerCase();
      return TEXT_INPUT_TYPES.has(type) && !el.readOnly && !el.disabled;
    }
    return false;
  }

  function editableRoot(node) {
    const el = node && node.nodeType === 1 ? node : node && node.parentElement;
    if (!el) return null;
    if (isTextField(el)) return el;
    if (el.isContentEditable) {
      let root = el;
      while (root.parentElement && root.parentElement.isContentEditable) root = root.parentElement;
      return root;
    }
    return null;
  }

  function saveSelection(root) {
    if (isTextField(root)) {
      try {
        return { start: root.selectionStart, end: root.selectionEnd };
      } catch (_) {
        return {};
      }
    }
    const sel = root.ownerDocument.getSelection();
    return sel && sel.rangeCount ? { range: sel.getRangeAt(0).cloneRange() } : {};
  }

  function restoreSelection(root, saved) {
    try {
      root.focus({ preventScroll: true });
    } catch (_) {
      /* ignore */
    }
    try {
      if (isTextField(root)) {
        if (saved.start != null) root.setSelectionRange(saved.start, saved.end);
        return;
      }
      if (saved.range && root.contains(saved.range.startContainer)) {
        const sel = root.ownerDocument.getSelection();
        sel.removeAllRanges();
        sel.addRange(saved.range);
      }
    } catch (_) {
      /* the editor changed under us: insert at the current caret */
    }
  }

  /** Insert text where the paste happened, in a way that rich editors and React inputs accept. */
  function insertText(target, root, saved, text) {
    if (!root.isConnected) return false;
    restoreSelection(root, saved);
    const dispatchOn = target && target.isConnected && root.contains(target) ? target : root;
    // 1. A synthetic paste: ProseMirror, Lexical, Quill and Slate editors handle it themselves.
    //    (Our own listener ignores untrusted events, so this does not loop.)
    try {
      const data = new DataTransfer();
      data.setData('text/plain', text);
      const ev = new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true });
      dispatchOn.dispatchEvent(ev);
      if (ev.defaultPrevented) return true;
    } catch (_) {
      /* fall through */
    }
    // 2. insertText: works in textarea, input and contenteditable, and fires input events.
    try {
      if (document.execCommand && document.execCommand('insertText', false, text)) return true;
    } catch (_) {
      /* fall through */
    }
    // 3. Plain text field fallback.
    if (isTextField(root)) {
      const start = root.selectionStart != null ? root.selectionStart : root.value.length;
      const end = root.selectionEnd != null ? root.selectionEnd : start;
      root.setRangeText(text, start, end, 'end');
      root.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertFromPaste', data: text }));
      return true;
    }
    return false;
  }

  // ---- messaging ------------------------------------------------------------------------
  function sendToWorker(message) {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage(message, (reply) => {
          if (chrome.runtime.lastError || !reply) resolve({ ok: false, error: 'EXTENSION' });
          else resolve(reply);
        });
      } catch (_) {
        resolve({ ok: false, error: 'EXTENSION' });
      }
    });
  }

  // ---- UI (closed shadow DOM, no page styles, no real text) ------------------------------
  const CSS = `
    :host { all: initial; }
    .box { font: 13px/1.4 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #10202f;
      background: #ffffff; border: 1px solid #c9d4df; border-radius: 10px;
      box-shadow: 0 6px 24px rgba(0,0,0,.18); padding: 10px 12px; max-width: 360px; }
    .badge { display: flex; gap: 8px; align-items: center; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: #2f8f5b; flex: none; }
    .panel { border-color: #d08a2e; }
    .title { font-weight: 600; margin: 0 0 4px; }
    .help { margin: 0 0 10px; color: #3b4b5b; }
    .row { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
    button { font: inherit; border-radius: 7px; padding: 5px 10px; cursor: pointer;
      border: 1px solid #9fb0c0; background: #f3f6f9; color: inherit; }
    button.primary { background: #17324d; border-color: #17324d; color: #fff; }
    button.risky { background: #fff; border-color: #b45309; color: #92400e; }
    button:focus-visible { outline: 2px solid #3b82f6; outline-offset: 1px; }
    @media (prefers-color-scheme: dark) {
      .box { background: #18222c; color: #e6edf3; border-color: #34465a; }
      .help { color: #b5c2cf; }
      button { background: #223140; border-color: #46596d; }
      button.primary { background: #c7def4; border-color: #c7def4; color: #10202f; }
      button.risky { background: transparent; border-color: #f59e0b; color: #fbbf24; }
    }`;

  let host = null;
  let shadow = null;
  let badgeTimer = 0;

  function uiRoot() {
    if (host && host.isConnected) return shadow;
    host = document.createElement('ragbase-shield-ui');
    host.setAttribute('style', 'all: initial; position: fixed; z-index: 2147483647; right: 16px; bottom: 16px;');
    shadow = host.attachShadow({ mode: 'closed' });
    const style = document.createElement('style');
    style.textContent = CSS;
    shadow.append(style);
    (document.body || document.documentElement).append(host);
    return shadow;
  }

  function clearUi() {
    clearTimeout(badgeTimer);
    if (shadow) shadow.querySelectorAll('.box').forEach((n) => n.remove());
  }

  function showBadge(count) {
    const root = uiRoot();
    clearUi();
    const box = document.createElement('div');
    box.className = 'box badge';
    box.setAttribute('role', 'status');
    box.setAttribute('aria-live', 'polite');
    const dot = document.createElement('span');
    dot.className = 'dot';
    const label = document.createElement('span');
    if (count === 0) label.textContent = t('badgeNothing');
    else if (count === 1) label.textContent = t('badgeMaskedOne');
    else label.textContent = t('badgeMasked', [String(count)]);
    box.append(dot, label);
    root.append(box);
    badgeTimer = setTimeout(() => box.remove(), BADGE_MS);
  }

  const ERRORS = {
    DESK_DOWN: ['errDeskDown', 'errDeskDownHelp'],
    DESK_TIMEOUT: ['errDeskTimeout', 'errDeskDownHelp'],
    NO_TOKEN: ['errNoToken', 'errTokenHelp'],
    BAD_TOKEN: ['errBadToken', 'errTokenHelp'],
    TOO_LARGE: ['errTooLarge', 'errNotPasted'],
    EXTENSION: ['errExtension', 'errExtensionHelp'],
    FILE: ['errFileBlocked', 'errFileBlockedHelp'],
  };

  function showBlocked(error, onPasteAnyway, onClose) {
    const root = uiRoot();
    clearUi();
    const [titleKey, helpKey] = ERRORS[error] || ['errDesk', 'errNotPasted'];
    const box = document.createElement('div');
    box.className = 'box panel';
    box.setAttribute('role', 'alertdialog');
    box.setAttribute('aria-label', t(titleKey));
    const title = document.createElement('p');
    title.className = 'title';
    title.textContent = t(titleKey);
    const help = document.createElement('p');
    help.className = 'help';
    help.textContent = t(helpKey);
    const row = document.createElement('div');
    row.className = 'row';

    let done = false;
    const finish = (pasteAnyway) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      box.remove();
      if (pasteAnyway) onPasteAnyway();
      onClose();
    };
    const timer = setTimeout(() => finish(false), PANEL_MS);

    if (error === 'NO_TOKEN' || error === 'BAD_TOKEN') {
      const opts = document.createElement('button');
      opts.textContent = t('btnOptions');
      opts.addEventListener('click', () => {
        sendToWorker({ type: 'shield:openOptions' });
        finish(false);
      });
      row.append(opts);
    }
    const anyway = document.createElement('button');
    anyway.className = 'risky';
    anyway.textContent = t(error === 'FILE' ? 'btnAttachAnyway' : 'btnPasteAnyway');
    anyway.addEventListener('click', () => finish(true));
    const cancel = document.createElement('button');
    cancel.className = 'primary';
    cancel.textContent = t('btnCancel');
    cancel.addEventListener('click', () => finish(false));
    box.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') {
        ev.stopPropagation();
        finish(false);
      }
    });
    row.append(anyway, cancel);
    box.append(title, help, row);
    root.append(box);
    cancel.focus({ preventScroll: true });
  }

  // ---- clipboard and drag data ----------------------------------------------------------
  const BLOCK_TAGS = new Set(['P', 'DIV', 'LI', 'TR', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE', 'PRE',
    'SECTION', 'ARTICLE', 'TABLE', 'UL', 'OL']);

  /** Plain text of an HTML fragment (DOMParser: no script runs, nothing is loaded). */
  function htmlToText(html) {
    try {
      const doc = new DOMParser().parseFromString(String(html), 'text/html');
      doc.querySelectorAll('script, style, noscript, template').forEach((n) => n.remove());
      const out = [];
      const walk = (node) => {
        if (node.nodeType === 3) {
          out.push(node.nodeValue);
          return;
        }
        if (node.nodeType !== 1) return;
        if (node.tagName === 'BR') out.push('\n');
        if (node.tagName === 'TD' || node.tagName === 'TH') out.push(' | ');
        node.childNodes.forEach(walk);
        if (BLOCK_TAGS.has(node.tagName)) out.push('\n');
      };
      walk(doc.body || doc.documentElement);
      return out.join('').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
    } catch (_) {
      return '';
    }
  }

  /** {text, files} of a DataTransfer: text/plain, else the text of text/html; files as an array. */
  function readTransfer(dt) {
    if (!dt) return { text: '', files: [] };
    let text = '';
    try {
      text = dt.getData('text/plain') || '';
      if (!text) {
        const html = dt.getData('text/html');
        if (html) text = htmlToText(html);
      }
    } catch (_) {
      text = '';
    }
    let files = [];
    try {
      files = Array.from(dt.files || []);
    } catch (_) {
      files = [];
    }
    return { text, files };
  }

  /** Give the files back to the page as the user asked ("Attach anyway"): a synthetic paste or drop. */
  function redispatchFiles(kind, target, files, point) {
    try {
      const data = new DataTransfer();
      files.forEach((f) => data.items.add(f));
      const init = { bubbles: true, cancelable: true };
      const ev = kind === 'drop'
        ? new DragEvent('drop', { ...init, dataTransfer: data, clientX: point.x, clientY: point.y })
        : new ClipboardEvent('paste', { ...init, clipboardData: data });
      (target && target.isConnected ? target : document.body).dispatchEvent(ev);
    } catch (_) {
      /* the page does not accept synthetic files: the user can switch the extension off to attach */
    }
  }

  function blockFiles(kind, e, files) {
    e.preventDefault();
    e.stopImmediatePropagation();
    const target = e.target && e.target.nodeType === 1 ? e.target : document.body;
    const point = { x: e.clientX || 0, y: e.clientY || 0 };
    showBlocked('FILE', () => redispatchFiles(kind, target, files, point), () => {});
  }

  // ---- paste, drop and beforeinput handlers ----------------------------------------------
  function maskAndInsert(target, root, saved, text) {
    sendToWorker({ type: 'shield:mask', text }).then((reply) => {
      if (reply.ok) {
        text = null;
        if (insertText(target, root, saved, reply.masked)) showBadge(Number(reply.count) || 0);
        return;
      }
      showBlocked(
        reply.error,
        () => {
          if (text) insertText(target, root, saved, text);
        },
        () => {
          text = null;
          restoreSelection(root, saved);
        }
      );
    });
  }

  function onPaste(e) {
    if (!e.isTrusted || !enabled || !e.clipboardData) return;
    const { text, files } = readTransfer(e.clipboardData);
    const root = editableRoot(e.target);
    if (!text) {
      if (files.length) blockFiles('paste', e, files); // a client file would reach the provider unmasked
      return;
    }
    if (!root) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const target = e.target && e.target.nodeType === 1 ? e.target : root;
    maskAndInsert(target, root, saveSelection(root), text);
  }

  function caretAt(x, y) {
    try {
      if (document.caretRangeFromPoint) return document.caretRangeFromPoint(x, y);
      if (document.caretPositionFromPoint) {
        const pos = document.caretPositionFromPoint(x, y);
        if (pos) {
          const range = document.createRange();
          range.setStart(pos.offsetNode, pos.offset);
          return range;
        }
      }
    } catch (_) {
      /* ignore */
    }
    return null;
  }

  function onDrop(e) {
    if (!e.isTrusted || !enabled || !e.dataTransfer) return;
    const { text, files } = readTransfer(e.dataTransfer);
    if (files.length) {
      blockFiles('drop', e, files); // dropped anywhere: the chat sites upload a dropped file
      return;
    }
    const root = editableRoot(e.target);
    if (!text || !root) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    let saved = {};
    if (isTextField(root)) {
      saved = saveSelection(root);
    } else {
      const range = caretAt(e.clientX, e.clientY);
      saved = range && root.contains(range.startContainer) ? { range } : saveSelection(root);
    }
    const target = e.target && e.target.nodeType === 1 ? e.target : root;
    maskAndInsert(target, root, saved, text);
  }

  const RAW_INPUTS = new Set(['insertFromPaste', 'insertFromDrop', 'insertFromPasteAsQuotation', 'insertFromYank']);

  function onBeforeInput(e) {
    if (!e.isTrusted || !enabled || !RAW_INPUTS.has(e.inputType)) return;
    const { text, files } = readTransfer(e.dataTransfer);
    const raw = text || e.data || '';
    const root = editableRoot(e.target);
    if (!raw) {
      if (files.length) {
        e.preventDefault();
        e.stopImmediatePropagation();
        showBlocked('FILE', () => {}, () => {});
      }
      return;
    }
    if (!root) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const target = e.target && e.target.nodeType === 1 ? e.target : root;
    maskAndInsert(target, root, saveSelection(root), raw);
  }

  window.addEventListener('paste', onPaste, true);
  window.addEventListener('drop', onDrop, true);
  window.addEventListener('beforeinput', onBeforeInput, true);
})();
