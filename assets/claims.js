/* claims.js -- what the ledger pages do in the browser: open a folded window a link points into, copy a hash, an
   address or a result post with one tap, and check that the files this site serves still have the SHA-256 the page prints.
   Nothing here stores anything or counts anything. The only requests go to this same site, for those files. */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  // The list of every entry starts open on a wide screen and folded on a phone.
  if (window.matchMedia && matchMedia('(min-width: 41em)').matches) {
    [].forEach.call(document.querySelectorAll('details[data-open-wide]'), function (d) { d.open = true; });
  }

  // A link to something inside a folded window opens the window.
  function reveal() {
    var t = location.hash.length > 1 && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!t) return;
    for (var d = t; d; d = d.parentElement) if (d.tagName === 'DETAILS') d.open = true;
    t.scrollIntoView();
  }
  window.addEventListener('hashchange', reveal);
  reveal();

  // Hashes and addresses in the text copy with one tap.
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('code.tok');
    if (!t || String(window.getSelection()) || !navigator.clipboard) return;
    navigator.clipboard.writeText(t.textContent).then(function () {
      t.classList.add('copied');
      setTimeout(function () { t.classList.remove('copied'); }, 900);
    }, function () {});
  });

  // "Copy result post" (front page) puts the post to fill in for that entry on the clipboard.
  function copyText(text) {
    function viaBox() {   // copy out of a temporary text box: older browsers, or a page the clipboard API refuses
      return new Promise(function (ok, no) {
        var box = document.createElement('textarea'), done = false;
        box.value = text;
        box.setAttribute('readonly', '');
        box.style.position = 'fixed';
        box.style.opacity = '0';
        document.body.appendChild(box);
        box.select();
        try { done = document.execCommand('copy'); } catch (err) { done = false; }
        document.body.removeChild(box);
        return done ? ok() : no();
      });
    }
    return navigator.clipboard && window.isSecureContext ? navigator.clipboard.writeText(text).catch(viaBox) : viaBox();
  }
  [].forEach.call(document.querySelectorAll('button.copy'), function (b) { b.setAttribute('aria-live', 'polite'); });
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button.copy');
    if (!b) return;
    var label = b.textContent;
    copyText(b.dataset.copy).then(function () {
      b.classList.add('copied');
      b.textContent = 'Copied';
      setTimeout(function () { b.classList.remove('copied'); b.textContent = label; }, 1500);
    }, function () { window.prompt('Copy this post:', b.dataset.copy); });
  });

  /* --- ledger.html: the files and their SHA-256 ---------------------------------------------------------------- */

  var printed = [].slice.call(document.querySelectorAll('code[data-sha-of]'));
  if (!printed.length) return;
  var said = function (code, text) { code.parentElement.querySelector('.served').textContent = text; };
  if (!(window.crypto && crypto.subtle)) {
    printed.forEach(function (c) { said(c, 'This browser cannot work out SHA-256 here. Any SHA-256 tool can, on the downloaded file.'); });
    return;
  }

  function sha(bytes) {
    return crypto.subtle.digest('SHA-256', bytes).then(function (d) {
      return Array.prototype.map.call(new Uint8Array(d), function (b) { return b.toString(16).padStart(2, '0'); }).join('');
    });
  }

  printed.forEach(function (code) {
    fetch(code.dataset.shaOf, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.arrayBuffer();
    }).then(sha).then(function (got) {
      said(code, got === code.textContent
        ? 'Your browser just read this file from the site and got this SHA-256.'
        : 'Your browser just read this file from the site and got a different SHA-256: ' + got + '. Tell the group.');
    }).catch(function () { said(code, 'Your browser could not read this file to check it.'); });
  });

  $('copy-file').addEventListener('change', function () {
    var f = this.files[0], out = $('copy-result');
    if (!f) return;
    f.arrayBuffer().then(function (buf) {
      var bytes = new Uint8Array(buf);
      var unix = bytes.filter(function (b, i) { return !(b === 13 && bytes[i + 1] === 10); });   // Windows line ends made plain
      return Promise.all([sha(bytes), sha(unix)]);
    }).then(function (s) {
      var exact = printed.filter(function (c) { return c.textContent === s[0]; })[0];
      var ends = printed.filter(function (c) { return c.textContent === s[1]; })[0];
      out.className = 'msg ' + (exact || ends ? 'ok' : 'err');
      out.textContent = exact ? 'Same text as ' + exact.dataset.name + ', letter for letter.'
        : ends ? 'Same text as ' + ends.dataset.name + '. Only the line ends differ, which Windows does when it saves a file.'
          : 'Not the same text as any file listed here. Your copy\'s SHA-256 is ' + s[0] + '.';
    });
  });
})();
