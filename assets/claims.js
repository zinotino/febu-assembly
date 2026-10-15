/* claims.js -- what the ledger pages do in the browser: open a folded window a link points into, copy a hash, an
   address or a post with one tap, check that the files this site serves still have the SHA-256 the page prints, and
   the member flows: the check card and "your next move" (front page), the weekly turn (weekly.html) and the entry form
   (write.html). Each flow writes text for a person to paste into the chat or into ledger.txt. Nothing here posts,
   stores or counts anything. The only requests go to this same site, for the files on the ledger page.
   The weekly page's reading of a chat (parse, review) needs no page: `node test_claims.js` runs it. */
(function () {
  'use strict';

  /* --- text the pages write -------------------------------------------------------------------------------------- */

  var WIDTH = 92;                               // ledger.txt's lines, as build.py and the README keep them
  var DOT = '  ·  ';                       // between the parts of a post's first line
  var PAD14 = new Array(15).join(' '), PAD16 = new Array(17).join(' ');
  var DAY = 864e5;

  function today() { return new Date().toISOString().slice(0, 10); }   // the ledger's dates are UTC
  function dec(s) { try { return decodeURIComponent(s); } catch (e) { return ''; } }   // a bad %-escape is no link
  var store = {   // this device's own memory: the name picked, unfinished check cards. Nothing leaves the page.
    get: function (k) { try { return localStorage.getItem('assembly:' + k); } catch (e) { return null; } },
    set: function (k, v) {
      try { if (v === null) localStorage.removeItem('assembly:' + k); else localStorage.setItem('assembly:' + k, v); } catch (e) {}
    }
  };

  function wrap(first, text, rest) {
    var lines = [], cur = first, empty = true;
    String(text).split(/\s+/).filter(Boolean).forEach(function (w) {
      if (!empty && cur.length + 1 + w.length > WIDTH) { lines.push(cur); cur = rest + w; }
      else cur += (empty ? '' : ' ') + w;
      empty = false;
    });
    return lines.concat(cur);
  }

  function stop(s) { s = String(s).trim(); return /[.!?]$/.test(s) ? s : s + '.'; }

  /* --- the weekly page's reading of a pasted chat ------------------------------------------------------------------
     A post's first line is the part a machine reads. The check card, the vote buttons and the entry form write them:
       CHECK FACT 8 · HOLDS · lines 1,2,3 · Laura · 2026-10-16      then Line n: / Saw: / New: / Minutes: lines
       VOTE YES · version 3 · Laura · 2026-10-16                     an objection adds two lines saying why
       ENTRY FACT 10 · Laura · 2026-10-16                            then the entry, as the ledger lays it out
     "|" or "•" work in place of "·", for anyone typing one on a phone. A blank line ends a post. Every other line is
     handed back to be read by a person. */

  var SEP = '\\s*[\\u00b7|\\u2022]\\s*', PART = '([^\\u00b7|\\u2022]+?)', ON = '(\\d{4}-\\d\\d-\\d\\d)\\s*$';
  var CHECK = new RegExp('\\bCHECK\\s+(FACT|PROMISE)\\s+(\\d+)' + SEP + "(HOLDS|DOESN'?T\\s+HOLD|KEPT|BROKEN)" +
                         '(?:' + SEP + 'lines?\\s*(\\d[\\d\\s,and-]*?))?' + SEP + PART + SEP + ON, 'i');
  var VOTE = new RegExp('\\bVOTE\\s+(YES|OBJECT)' + SEP + PART + SEP + PART + SEP + ON, 'i');
  var ENTRY = new RegExp('\\bENTRY\\s+(FACT|PROMISE)\\s+(\\d+)' + SEP + PART + SEP + ON, 'i');
  var RESULTS = { FACT: ['HOLDS', "DOESN'T HOLD"], PROMISE: ['KEPT', 'BROKEN'] };

  function numbers(s) {   // "1,2,3", "1, 2 and 3", "1-3"
    var out = [];
    String(s || '').replace(/(\d+)(?:\s*-\s*(\d+))?/g, function (_, a, b) {
      for (var n = +a; n <= +(b || a) && n - a < 50; n++) if (out.indexOf(n) < 0) out.push(n);
    });
    return out.sort(function (x, y) { return x - y; });
  }

  function parse(text) {
    var out = { checks: [], votes: [], entries: [], unread: [] }, cur = null;
    String(text).replace(/\r\n?/g, '\n').split('\n').forEach(function (raw, i) {
      var s = raw.replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim(), m;   // one space: the patterns stay linear
      if (!s) { cur = null; return; }
      if ((m = s.match(CHECK))) {
        out.checks.push(cur = { type: 'check', at: i + 1, kind: m[1].toUpperCase(), num: +m[2], lines: numbers(m[4]),
          word: m[3].toUpperCase().replace(/DOESN'?T\s+HOLD/, "DOESN'T HOLD"), who: m[5].trim(), date: m[6], saw: [],
          fresh: '', minutes: 0, opened: false, line: 0 });
      } else if ((m = s.match(VOTE))) {
        out.votes.push(cur = { type: 'vote', at: i + 1, say: m[1].toUpperCase(), subject: m[2].trim(), who: m[3].trim(),
          date: m[4], why: [] });
      } else if ((m = s.match(ENTRY))) {
        out.entries.push(cur = { type: 'entry', at: i + 1, kind: m[1].toUpperCase(), num: +m[2], who: m[3].trim(),
          date: m[4], text: [] });
      } else if (!(cur && more(cur, s, raw))) {
        out.unread.push({ at: i + 1, text: raw.trim() });
      }
    });
    return out;
  }

  function more(cur, s, raw) {   // a line of the post above it, or not
    var m;
    if (cur.type === 'entry') {   // to its closing ``` (or a blank line, if the chat dropped the fences)
      if (cur.fences > 1) return false;
      if (/^`{3}/.test(s)) cur.fences = (cur.fences || 0) + 1;
      else cur.text.push(raw.replace(/\s+$/, ''));
      return true;
    }
    if (cur.type === 'vote') {
      if (!/^(which line is wrong|what would change my mind)\b/i.test(s)) return false;
      cur.why.push(s);
      return true;
    }
    if ((m = s.match(/^line\s+(\d+)\s*:/i))) { cur.line = +m[1]; return true; }
    if ((m = s.match(/^saw\s*:\s*(.*)$/i))) { cur.saw.push({ line: cur.line, text: m[1].trim() }); return true; }
    if ((m = s.match(/^new\s*:\s*(.*)$/i))) { cur.fresh = m[1].trim(); return true; }
    if ((m = s.match(/^minutes?\s*:\s*(\d+)/i))) { cur.minutes = +m[1]; return true; }
    if (/^i opened the link/i.test(s)) { cur.opened = true; return true; }
    return false;
  }

  function label(e) { return e.kind + ' ' + e.num; }
  function same(a, b) { return a.join(',') === b.join(','); }
  function linesText(ls) { return ls.length ? ' on line' + (ls.length > 1 ? 's ' : ' ') + ls.join(', ') : ''; }

  function trouble(c, e, data) {   // why a CHECK post cannot go in as it stands, or ''
    if (!e) {
      var other = data.entries.filter(function (x) { return x.num === c.num; })[0];
      return other ? 'entry ' + c.num + ' is a ' + other.kind.toLowerCase() + ', not a ' + c.kind.toLowerCase()
        : 'the file has no entry ' + c.num + (c.num >= data.next ? ' yet: add the new entry first, then its checks' : '');
    }
    if (RESULTS[e.kind].indexOf(c.word) < 0) return 'a ' + e.kind.toLowerCase() + "'s result is " + RESULTS[e.kind].join(' or ');
    if (c.who === e.writer) return c.who + ' wrote ' + label(e) + ', and nobody checks their own entry (rule 3)';
    if (e.kind === 'FACT' && !c.lines.length) return 'it names no WRONG IF lines';
    var bad = c.lines.filter(function (n) { return n < 1 || n > e.lines; });
    if (bad.length) return label(e) + ' has ' + e.lines + ' WRONG IF line' + (e.lines === 1 ? '' : 's') + ', and the post names ' + bad.join(', ');
    if (!c.saw.some(function (s) { return s.text; })) return 'it does not say what they saw';
    if (!c.fresh) return 'it names nothing new on the page (HOW TO CHECK AN ENTRY, step 3)';
    if (!c.opened) return 'it does not say they opened the link themselves (Saw)';
    return '';
  }

  function seenText(c) {   // build.py reads this back (SEEN_ITEM): keep the part up to the first full stop as it is
    var saw = c.saw.filter(function (s) { return s.text; }).map(function (s) {
      return (s.line ? 'line ' + s.line + ', ' : '') + s.text.replace(/[\s.;]+$/, '');
    });
    return '- ' + c.who + ', ' + c.date + ': ' + c.word + linesText(c.lines) + '. Saw: ' + stop(saw.join('; ')) +
      ' New: ' + stop(c.fresh) + (c.minutes ? ' ' + c.minutes + ' minute' + (c.minutes === 1 ? '' : 's') + '.' : '');
  }

  function agreeing(found, writer, members) {   // rule 3: members other than the writer, by result and lines
    var by = {};
    found.forEach(function (r) {
      if (members.indexOf(r[0]) < 0 || r[0] === writer) return;
      var g = by[r[2] + ' ' + r[3].join(',')] = by[r[2] + ' ' + r[3].join(',')] || { word: r[2], lines: r[3], names: [] };
      if (g.names.indexOf(r[0]) < 0) g.names.push(r[0]);
    });
    return Object.keys(by).map(function (k) { return by[k]; });
  }
  function closing(groups) { return groups.filter(function (g) { return g.names.length >= 2; })[0] || null; }

  function review(p, data, now) {
    var find = {}, add = [], held = [], already = [];
    data.entries.forEach(function (e) { find[label(e)] = e; });
    p.checks.slice().sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : a.at - b.at; }).forEach(function (c) {
      var e = find[c.kind + ' ' + c.num], why = trouble(c, e, data);
      if (why) return held.push({ post: c, why: why });
      if (e.results.some(function (r) { return r[0] === c.who && r[1] === c.date && r[2] === c.word && same(r[3], c.lines); })) {
        return already.push(c);
      }
      var a = add.filter(function (x) { return x.entry === e; })[0];
      if (!a) add.push(a = { entry: e, posts: [] });
      a.posts.push(c);
    });
    add.forEach(function (a) {
      a.lines = [];
      a.posts.forEach(function (c, i) {
        a.lines = a.lines.concat(wrap(i === 0 && a.entry.empty ? '    SEEN      ' : PAD14, seenText(c), PAD16));
      });
      var before = agreeing(a.entry.results, a.entry.writer, data.members);
      var after = agreeing(a.entry.results.concat(a.posts.map(function (c) { return [c.who, c.date, c.word, c.lines]; })),
                           a.entry.writer, data.members);
      a.was = closing(before);
      a.closes = a.was ? null : closing(after);
      a.groups = after;
      a.outsiders = a.posts.filter(function (c) { return data.members.indexOf(c.who) < 0; }).map(function (c) { return c.who; });
    });

    var dated = p.checks.concat(p.votes).map(function (x) { return x.date; }).sort();
    var from = dated[0] || null, back = [];
    if (from) data.entries.forEach(function (e) {
      e.results.forEach(function (r) {
        var posted = p.checks.some(function (c) { return c.kind === e.kind && c.num === e.num && c.who === r[0] && c.date === r[1]; });
        if (r[1] >= from && !posted) back.push({ entry: e, who: r[0], date: r[1], word: r[2] });
      });
    });

    var votes = {}, order = [];
    data.votes.forEach(function (v) {
      var k = v.subject.toLowerCase();
      votes[k] = { subject: v.subject, by: v.by, last: {}, late: [], outsiders: [], posts: 0 };
      order.push(k);
    });
    p.votes.forEach(function (v) {
      var k = v.subject.toLowerCase().replace(/\s+/g, ' ');
      if (!votes[k]) { votes[k] = { subject: v.subject, by: null, last: {}, late: [], outsiders: [], posts: 0 }; order.push(k); }
      var t = votes[k];
      t.posts++;
      if (data.members.indexOf(v.who) < 0) t.outsiders.push(v.who);
      else if (t.by && v.date > t.by) t.late.push(v.who + ' (' + v.date + ')');
      else t.last[v.who] = v;   // a later post from the same member replaces their earlier one
    });
    var tally = order.map(function (k) {
      var t = votes[k], said = function (w) {
        return data.members.filter(function (m) { return t.last[m] && t.last[m].say === w; });
      };
      t.yes = said('YES');
      t.object = said('OBJECT');
      t.why = t.object.map(function (m) { return { who: m, why: t.last[m].why }; });
      t.silent = data.members.filter(function (m) { return !t.last[m]; });
      t.passes = t.yes.length >= 4 && t.object.length <= 1;
      t.over = !!(t.by && now > t.by);
      return t;
    });

    return { add: add, held: held, already: already, back: back, from: from, votes: tally, entries: p.entries,
      unread: p.unread, checks: p.checks.length, voted: p.votes.length };
  }

  if (typeof document === 'undefined') {   // under node, for test_claims.js
    module.exports = { parse: parse, review: review, wrap: wrap, seenText: seenText };
    return;
  }

  /* --- every page ---------------------------------------------------------------------------------------------- */

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function each(sel, fn, root) { [].forEach.call((root || document).querySelectorAll(sel), fn); }

  // The list of every entry starts open on a wide screen and folded on a phone.
  if (window.matchMedia && matchMedia('(min-width: 41em)').matches) {
    each('details[data-open-wide]', function (d) { d.open = true; });
  }

  // A link to something inside a folded window opens the window; a link to a check card opens the card.
  function reveal() {
    var id = location.hash.length > 1 && dec(location.hash.slice(1)), t = id && document.getElementById(id);
    if (!t) return;
    if (t.classList.contains('cc')) openCard(t, true);
    for (var d = t; d; d = d.parentElement) if (d.tagName === 'DETAILS') d.open = true;
    (t.closest('.pick') || t).scrollIntoView();
  }
  window.addEventListener('hashchange', reveal);

  // Hashes and addresses in the text copy with one tap.
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('code.tok');
    if (!t || String(window.getSelection()) || !navigator.clipboard) return;
    navigator.clipboard.writeText(t.textContent).then(function () {
      t.classList.add('copied');
      setTimeout(function () { t.classList.remove('copied'); }, 900);
    }, function () {});
  });

  // A "copy" button puts its post on the clipboard, with today's date where it says {today}.
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
  each('button.copy', function (b) { b.setAttribute('aria-live', 'polite'); });
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('button.copy');
    if (!b || b.disabled || b.classList.contains('copied')) return;
    var label = b.textContent, text = b.dataset.copy.replace(/\{today\}/g, today());
    copyText(text).then(function () {
      b.classList.add('copied');
      b.textContent = 'Copied';
      setTimeout(function () { b.classList.remove('copied'); b.textContent = label; }, 1500);
    }, function () { window.prompt('Copy this post:', text); });
  });

  // A post shown as the chat will show it, its first line (the part the weekly page reads) set apart.
  function showPost(pre, text) {
    var lines = text.split('\n');
    pre.textContent = '';
    pre.appendChild(el('span', 'first', lines[0]));
    if (lines.length > 1) pre.appendChild(document.createTextNode(lines.slice(1).join('\n')));
  }

  // "Still needed: ..." under a post, and its Copy button waiting until nothing is.
  function needs(p, buttons, missing, ready) {
    p.textContent = missing.length ? 'Still needed: ' + missing.join('; ') + '.' : ready;
    p.classList.toggle('ok', !missing.length);
    buttons.forEach(function (b) { b.disabled = missing.length > 0; });
  }

  function nameOf(root) {   // the name picked, or typed under "someone else"
    var who = root.querySelector('.who'), other = root.querySelector('.other');
    other.hidden = who.value !== '*';
    return (who.value === '*' ? other.value : who.value).trim();
  }

  /* --- front page: the check card ------------------------------------------------------------------------------- */

  function openCard(card, on) {
    card.hidden = !on;
    var b = document.querySelector('.cc-open[aria-controls="' + card.id + '"]');
    if (!b) return;
    b.setAttribute('aria-expanded', String(on));
    b.textContent = on ? 'Close the check' : 'Check it here';
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.cc-open');
    if (b) openCard($(b.getAttribute('aria-controls')), b.getAttribute('aria-expanded') !== 'true');
  });

  each('.cc', function (card) {
    var kind = card.dataset.kind, writer = card.dataset.writer, copy = card.querySelector('.cc-copy');
    copy.classList.add('copy');
    function write() {
      var ticked = [].filter.call(card.querySelectorAll('.ln-on'), function (b) { return b.checked; });
      each('.ln-on', function (b) { b.closest('li').querySelector('.saw').hidden = !b.checked; }, card);
      var name = nameOf(card), res = card.querySelector('input[type=radio]:checked');
      var fresh = card.querySelector('.new').value.trim(), mins = card.querySelector('.min').value.trim();
      var opened = card.querySelector('.opened').checked, missing = [];
      var head = ['CHECK ' + kind + ' ' + card.dataset.num, res ? res.value : '?'];
      if (kind === 'FACT') head.push('lines ' + (ticked.map(function (b) { return b.value; }).join(',') || '?'));
      var post = [head.concat(name || '?', today()).join(DOT)], blank = false;
      if (kind === 'FACT') {
        ticked.forEach(function (b) {
          var li = b.closest('li'), saw = li.querySelector('.saw').value.trim();
          blank = blank || !saw;
          post.push('Line ' + b.value + ': ' + li.querySelector('.t').textContent, 'Saw: ' + (saw || '?'));
        });
      } else {
        var saw = card.querySelector('.saw').value.trim();
        blank = !saw;
        post.push('Saw: ' + (saw || '?'));
      }
      post.push('New: ' + (fresh || '?'));
      if (mins) post.push('Minutes: ' + mins);
      if (opened) post.push('I opened the link myself. No AI wrote this result.');
      if (kind === 'FACT' && !ticked.length) missing.push('tick the WRONG IF lines you tested');
      else if (blank) missing.push('what you saw' + (kind === 'FACT' ? ' on each line you ticked' : ''));
      if (!fresh) missing.push('one thing on the page that is new');
      if (!res) missing.push('your result');
      if (!name) missing.push('your name');
      else if (name === writer) missing.push('a checker other than ' + writer + ', who wrote it (rule 3)');
      if (!opened) missing.push('a tick to say you opened the link yourself');
      showPost(card.querySelector('.post'), post.join('\n'));
      copy.dataset.copy = post.join('\n');
      needs(card.querySelector('.need'), [copy], missing, 'Ready. Copy it and paste it in the chat.');
    }
    var key = 'draft:' + kind + card.dataset.num, fields = card.querySelectorAll('input, select');
    var isTick = function (f) { return f.type === 'checkbox' || f.type === 'radio'; };
    var keep = function (e) {   // an unfinished card survives a reload, until its post is copied
      if (e && !e.isTrusted) return;   // the name picked under "your week" arrives by a made event: not a draft
      store.set(key, JSON.stringify([].map.call(fields, function (f) { return isTick(f) ? f.checked : f.value; })));
    };
    var draft = store.get(key);
    if (draft) {
      try {
        var filled = false;
        JSON.parse(draft).forEach(function (v, i) {
          var f = fields[i];
          if (!f) return;
          if (isTick(f)) f.checked = !!v; else f.value = v;
          if (!f.classList.contains('who') && (v === true || (typeof v === 'string' && v.trim()))) filled = true;
        });
        if (filled) openCard(card, true);
      } catch (err) { store.set(key, null); }
    }
    card.addEventListener('input', write);
    card.addEventListener('change', write);
    card.addEventListener('input', keep);
    card.addEventListener('change', keep);
    copy.addEventListener('click', function () { store.set(key, null); });
    write();
  });

  /* --- front page: your next move ------------------------------------------------------------------------------- */

  var next = $('next');
  if (next) {
    var turn = next.querySelector('.turn'), order = turn.dataset.order.split('|'), from = turn.dataset.from, me = '';
    var iso = function (t) { return new Date(t).toISOString().slice(0, 10); };
    var week = function () {   // rule 6: a week each, in Member order, counted from the first date in STATUS
      var days = Math.floor((Date.parse(today()) - Date.parse(from)) / DAY);
      if (!from || !(days >= 0)) return null;
      var w = Math.floor(days / 7), start = Date.parse(from) + w * 7 * DAY;
      return { w: w, who: order[w % order.length], after: order[(w + 1) % order.length], start: iso(start), end: iso(start + 6 * DAY) };
    };
    var daysLeft = function (d) { return Math.round((Date.parse(d) - Date.parse(today())) / DAY); };
    var left = function (n) { return n < 0 ? 'closed' : n === 0 ? 'today' : n + ' day' + (n === 1 ? '' : 's') + ' left'; };
    each('[data-due]', function (t) { t.insertAdjacentText('beforeend', ' (' + left(daysLeft(t.dataset.due)) + ')'); });
    var post = $('due-post'), copyBtn = post && post.parentNode.querySelector('button.copy');
    var fill = function (text, t) {   // the reminder's dates: days left, and this week's turn
      return text.replace(/\{days\}/g, post.dataset.by ? left(daysLeft(post.dataset.by)) : '')
        .replace(/\{turn\}/g, t ? t.who : 'see the site').replace(/\{turnend\}/g, t ? t.end : 'the end of the week')
        .replace(/\{next\}/g, t ? t.after : 'the next in order');
    };
    var showTurn = function () {
      var t = week();
      if (t) {
        turn.querySelector('.turn-now').textContent = 'This week, ' + t.start + ' to ' + t.end + ': ' + t.who +
          '. Next week: ' + t.after + '. A turn not done by the end of its week passes to the next member. Weeks are ' +
          'counted from ' + from + ', the date in STATUS, in Member order.';
      }
      each('.due-turn', function (s) { if (t) s.textContent = t.who + ', to ' + t.end; });
      each('.turn-me', function (p) {   // each member's own week: this one, or k weeks on
        if (!t) return;
        var k = ((order.indexOf(p.dataset.name) - t.w % order.length) + order.length) % order.length;
        var s = Date.parse(t.start) + k * 7 * DAY, chip = next.querySelector('.turn-chip[data-name="' + p.dataset.name + '"]');
        p.textContent = k ? 'Yours in ' + k + ' week' + (k === 1 ? '' : 's') + ': ' + iso(s) + ' to ' + iso(s + 6 * DAY) + '.'
          : 'Yours this week, to ' + t.end + '.';
        if (chip) { chip.textContent = k ? 'in ' + k + ' week' + (k === 1 ? '' : 's') : 'this week: you'; chip.classList.toggle('you', !k); }
      });
      each('.turn-you', function (p) { p.hidden = !(t && me === t.who); }, next);
      if (post) { post.textContent = fill(post.dataset.text || (post.dataset.text = post.textContent), t).replace(/\{today\}/g, today()); }
      if (copyBtn) { copyBtn.dataset.copy = fill(copyBtn.dataset.text || (copyBtn.dataset.text = copyBtn.dataset.copy), t); }
    };
    next.addEventListener('change', function (e) {
      if (e.target.name !== 'me') return;
      me = e.target.value;
      store.set('me', me);
      each('.moves', function (p) { p.hidden = p.dataset.who !== me; }, next);
      next.querySelector('.moves-none').hidden = true;
      each('.cc .who', function (s) {   // the check cards start from the name picked here
        if (s.value) return;
        s.value = me;
        s.dispatchEvent(new Event('change', { bubbles: true }));
      });
      showTurn();
    });
    showTurn();
    var pick = function (name) {   // #me=Name in the address, else the name this device remembers
      var r = [].filter.call(next.querySelectorAll('input[name=me]'), function (i) { return i.value === name; })[0];
      if (!r) return false;
      r.checked = true;
      r.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    };
    var fromUrl = (location.hash.match(/me=([^&]+)/) || [])[1];
    if (fromUrl && pick(dec(fromUrl))) next.scrollIntoView();
    else if (store.get('me')) pick(store.get('me'));
    window.addEventListener('hashchange', function () {
      var m = (location.hash.match(/me=([^&]+)/) || [])[1];
      if (m) pick(dec(m));
    });
  }

  /* --- weekly.html ---------------------------------------------------------------------------------------------- */

  var chat = $('chat');
  if (chat) {
    var data = JSON.parse($('ledger-data').textContent);
    var box = function (id) { var b = $(id + '-out'); b.textContent = ''; return b; };
    var head = function (to, text) { return to.appendChild(el('h3', 'wk-h', text)); };
    var para = function (to, text, cls) { return to.appendChild(el('p', cls || '', text)); };
    var list = function (to, rows) {
      var ul = to.appendChild(el('ul', 'wk-list'));
      rows.forEach(function (r) { ul.appendChild(el('li', '', r)); });
      return ul;
    };
    var block = function (to, text, button) {
      to.appendChild(el('pre', 'lit keep', text));
      var b = el('button', 'btn copy', button);
      b.type = 'button';
      b.dataset.copy = text;
      to.appendChild(el('p', 'acts')).appendChild(b);
    };
    var groupText = function (g) { return g.word + linesText(g.lines) + ': ' + g.names.join(', '); };

    var read = function () {
      var has = /\S/.test(chat.value);
      ['w-seen', 'w-back', 'w-close', 'w-votes', 'w-unread'].forEach(function (id) { $(id).hidden = !has; });
      $('w-sum').textContent = '';
      if (!has) return;
      var r = review(parse(chat.value), data, today()), out;
      $('w-sum').textContent = 'Read ' + r.checks + ' CHECK post' + (r.checks === 1 ? '' : 's') + ' and ' + r.voted +
        ' VOTE post' + (r.voted === 1 ? '' : 's') + '. ' + r.unread.length + ' line' + (r.unread.length === 1 ? '' : 's') +
        ' left for you to read (step 6).';

      out = box('w-seen');
      if (!r.add.length) para(out, 'No CHECK post to add.');
      r.add.forEach(function (a) {
        head(out, 'Under ' + label(a.entry));
        para(out, a.entry.empty ? 'Replace its line "SEEN      nobody yet" with these:' : 'Add these under its last SEEN line:');
        block(out, a.lines.join('\n'), 'Copy these lines');
        list(out, a.posts.map(function (c) {
          return 'Line ' + c.at + ' of what you pasted, posted as ' + c.who + ': check the chat shows ' + c.who + ' sent it.' +
            (data.members.indexOf(c.who) < 0 ? ' Not on the Member line: it counts toward reopening, not closing (rule 3).' : '');
        }));
      });
      r.entries.forEach(function (n) {
        head(out, 'New entry: ' + n.kind + ' ' + n.num + ', by ' + n.who);
        para(out, 'Put it under THE ENTRIES above "The next entry is number ' + data.next + '.", lined up like the ' +
          'entries above it, and raise that number by one.' + (n.num !== data.next ? ' The file\'s next number is ' +
          data.next + ': numbers go in the order entries were posted.' : ''));
        if (n.text.length) block(out, n.text.join('\n'), 'Copy the entry');
      });
      if (r.held.length) {
        head(out, 'Posts for you to read yourself');
        list(out, r.held.map(function (t) {
          return 'Line ' + t.post.at + ', ' + t.post.kind + ' ' + t.post.num + ' from ' + t.post.who + ': ' + t.why + '.';
        }));
        para(out, 'None of these is in the blocks above. Read each in the chat and add it by hand if it should count.', 'hint');
      }
      if (r.already.length) {
        para(out, 'Already in the file, so not repeated: ' + r.already.map(function (c) {
          return c.kind + ' ' + c.num + ' from ' + c.who + ', ' + c.date;
        }).join('; ') + '.', 'hint');
      }

      out = box('w-back');
      if (!r.from) para(out, 'No dated CHECK or VOTE post in what you pasted, so nothing to match.');
      else if (!r.back.length) para(out, 'Every SEEN line in the file dated ' + r.from + ' or later has its post in what you pasted.');
      else {
        para(out, 'These SEEN lines are dated ' + r.from + ' or later, and no CHECK post in what you pasted matches them. ' +
          'Find each one\'s post in the chat (rule 6), or tell the group it is missing.');
        list(out, r.back.map(function (b) { return label(b.entry) + ': ' + b.who + ', ' + b.date + ', ' + b.word; }));
      }

      out = box('w-close');
      if (!r.add.length) para(out, 'No new results, so nothing new to close.');
      r.add.forEach(function (a) {
        var e = a.entry, row = el('p', 'wk-close');
        row.appendChild(el('strong', '', label(e) + ' '));
        if (a.was) row.appendChild(document.createTextNode('was closed already, ' + groupText(a.was) + '.'));
        else if (a.closes) {
          row.classList.add('ok');
          row.appendChild(document.createTextNode('closes ' + a.closes.word + linesText(a.closes.lines) + ': ' +
            a.closes.names.join(' and ') + ', two members other than ' + e.writer + ', posted the same result on the same lines.'));
        } else {
          row.appendChild(document.createTextNode('stays open. ' + (a.groups.length ? 'So far: ' + a.groups.map(groupText).join('; ') +
            '. It closes when a second member other than ' + e.writer + ' posts the same result on the same WRONG IF lines.'
            : 'No result from a member other than ' + e.writer + ' yet.')));
        }
        out.appendChild(row);
        if (a.outsiders.length) para(out, 'Not counted toward closing: ' + a.outsiders.join(', ') + ' (not on the Member line).', 'hint');
      });
      para(out, 'This counts the SEEN lines the file holds in the weekly page\'s form, plus this week\'s. It does not ' +
        'know about a reopened entry or a member silent for 90 days: check those by hand.', 'hint');

      out = box('w-votes');
      if (!r.votes.length) para(out, 'Nothing in the ledger is up for a vote, and no VOTE post in what you pasted.');
      r.votes.forEach(function (t) {
        head(out, 'Ledger ' + t.subject + (t.by ? ', "yes" or "object" by ' + t.by : ''));
        var rows = ['Yes, ' + t.yes.length + ' of the 4 needed: ' + (t.yes.join(', ') || 'none yet'),
          'Object, at most 1 allowed: ' + (t.object.join(', ') || 'none'),
          'Not heard from in what you pasted: ' + (t.silent.join(', ') || 'nobody')];
        if (t.late.length) rows.push('After the closing date, not counted: ' + t.late.join(', '));
        if (t.outsiders.length) rows.push('Not on the Member line, not counted: ' + t.outsiders.join(', '));
        list(out, rows);
        t.why.forEach(function (w) { if (w.why.length) para(out, w.who + ': ' + w.why.join(' '), 'wk-why'); });
        para(out, !t.by ? 'The ledger gives no closing date for this: it is 7 days from the post that showed the text (rule 7).'
          : t.over ? 'Closed on ' + t.by + ': ' + (t.passes ? 'it passes on these counts.' : 'it does not pass on these counts.')
            : 'Open until ' + t.by + '. ' + (t.passes ? 'It would pass on these counts.' : 'On these counts it would not pass yet.'),
          'wk-close' + (t.passes ? ' ok' : ''));
      });
      if (r.votes.length) {
        para(out, 'Counts only the VOTE posts you pasted: paste every week since a vote opened to count all of it. A ' +
          'later post from the same member replaces their earlier one. If fewer than five members are active, every ' +
          'active member must say yes (rule 7).', 'hint');
      }

      out = box('w-unread');
      if (!r.unread.length) para(out, 'Nothing: every line belonged to a post this page reads.');
      else {
        para(out, 'Names and times from the chat, replies, results written another way: read them yourself. A result ' +
          'here counts as much as one above.');
        out.appendChild(el('pre', 'lit unread', r.unread.map(function (u) {
          return (new Array(6).join(' ') + u.at).slice(-5) + '  ' + u.text;
        }).join('\n')));
      }
    };
    chat.addEventListener('input', read);
    read();
  }

  /* --- write.html: the entry form ------------------------------------------------------------------------------- */

  var wf = document.querySelector('.wf');
  if (wf) {
    var wis = wf.querySelector('.wis'), spare = wis.firstElementChild.cloneNode(true);
    var copies = [].slice.call(document.querySelectorAll('.w-copy-chat, .w-copy-entry'));
    copies.forEach(function (b) { b.classList.add('copy'); });
    var renumber = function () {
      [].forEach.call(wis.children, function (li, i) {
        li.querySelector('.n').textContent = i + 1;
        li.querySelector('.wi-t').setAttribute('aria-label', 'WRONG IF line ' + (i + 1));
        li.querySelector('.wi-x').setAttribute('aria-label', 'Remove WRONG IF line ' + (i + 1));
        li.querySelector('.wi-x').hidden = wis.children.length === 1;
      });
    };
    var write = function () {
      var name = nameOf(wf), n = wf.dataset.next, date = today(), missing = [];
      var says = wf.querySelector('.says').value.replace(/\s+/g, ' ').trim();
      var links = wf.querySelector('.link').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
      var lines = [].map.call(wis.querySelectorAll('.wi-t'), function (i) {
        return i.value.replace(/\s+/g, ' ').trim().replace(/^or\s+/i, '').replace(/[\s.;,]+$/, '');
      });
      [].forEach.call(wis.children, function (li, i) {
        var warn = li.querySelector('.warn'), t = lines[i];
        warn.hidden = !t || (/\d{4}-\d\d-\d\d/.test(t) && !/[;,] or /i.test(t));
        warn.textContent = /[;,] or /i.test(t) ? 'This line holds ", or": the ledger counts each part after it as a WRONG ' +
          'IF line of its own. Make it two lines.' : 'No date in this line. Could a stranger make it true later, with a ' +
          'transfer or a new post? End-date it: "by the end of ' + date + '".';
      });
      lines = lines.filter(Boolean);
      var entry = ['  FACT ' + n + '. (' + (name || '?') + ', ' + date + ')']
        .concat(wrap('    SAYS      ', says || '?', PAD14));
      links.forEach(function (l, i) {
        entry = entry.concat(i === 0 ? wrap('    LINK      ', l, PAD14) : /^https?:\/\//i.test(l) ? [PAD16 + l] : wrap(PAD14, l, PAD14));
      });
      if (!links.length) entry.push('    LINK      ?');
      entry = entry.concat(wrap('    WRONG IF  ', lines.length ? lines.join('; or ') + '.' : '?', PAD14), '    SEEN      nobody yet');
      var text = entry.join('\n'), post = ['ENTRY FACT ' + n, name || '?', date].join(DOT) + '\n```\n' + text + '\n```';
      if (!name) missing.push('your name');
      if (!says) missing.push('what it SAYS');
      if (!links.some(function (l) { return /^https?:\/\/\S+$/i.test(l); })) missing.push('a LINK, on a line of its own, starting https://');
      if (!lines.length) missing.push('a WRONG IF line');
      showPost(document.querySelector('.chat-out'), post);
      document.querySelector('.entry-out').textContent = text;
      document.querySelector('.w-copy-chat').dataset.copy = post;
      document.querySelector('.w-copy-entry').dataset.copy = text;
      needs($('need-w'), copies, missing, 'Ready. Read it once more against SAYS: every part of it needs a WRONG IF line.');
    };
    wf.querySelector('.wi-add').addEventListener('click', function () {
      var li = wis.appendChild(spare.cloneNode(true));
      renumber();
      li.querySelector('.wi-t').focus();
      write();
    });
    wis.addEventListener('click', function (e) {
      var x = e.target.closest('.wi-x');
      if (!x) return;
      x.closest('li').remove();
      renumber();
      write();
    });
    wf.addEventListener('input', write);
    wf.addEventListener('change', write);
    renumber();
    write();
  }

  reveal();

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
