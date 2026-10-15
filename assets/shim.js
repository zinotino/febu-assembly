/* Thin layer between the archived bundle and its backend (the febu-host Supabase project).
   - scripture_pages is served from assets/scripture.json (164 archived pages; the table was never re-created).
   - the AI tables and every edge function (ai/ii chat, graduation, review) answer empty / "not wired"; they have no backend here.
   - everything else (auth, community, jobs, storage, realtime, the visitor counter) goes to the real project.
   - if the project is unreachable (free projects pause after a week idle) community reads fall back to the 2026-07-15
     snapshot in assets/community.json and the counter to its last archived reading, so the site still renders. */
(function () {
  var VISITORS = 32817; // last archived reading, 2026-09-23T19:20:34Z (INVESTIGATION.md P92)
  var AI_TABLES = { graduated_iis: 1, ai_progress_global: 1, transmissions: 1 };
  var realFetch = window.fetch.bind(window);
  var scripture, community;
  function json(body, status, extra) {
    var h = { 'Content-Type': 'application/json' };
    for (var k in extra) h[k] = extra[k];
    return new Response(JSON.stringify(body), { status: status || 200, headers: h });
  }
  function rows(list, url) {
    var out = query.call(list, url);
    return json(out, 200, { 'Content-Range': '0-' + Math.max(out.length - 1, 0) + '/' + out.length });
  }
  function load() {
    return scripture || (scripture = realFetch('/assets/scripture.json').then(function (r) { return r.json(); }));
  }
  function loadCommunity() {
    return community || (community = realFetch('/assets/community.json').then(function (r) { return r.json(); }));
  }
  function query(url) {
    var q = url.searchParams, list = this;
    q.forEach(function (v, k) {
      var m = /^eq\.(.*)$/.exec(v), n = /^in\.\((.*)\)$/.exec(v);
      if (m && k !== 'select') list = list.filter(function (r) { return String(r[k]) === m[1]; });
      if (n) { var ids = n[1].split(',').map(function (x) { return x.replace(/^"|"$/g, ''); }); list = list.filter(function (r) { return ids.indexOf(String(r[k])) !== -1; }); }
    });
    var o = /^(\w+)\.(asc|desc)$/.exec(q.get('order') || '');
    if (o) {
      list = list.slice().sort(function (a, b) { return (a[o[1]] > b[o[1]] ? 1 : a[o[1]] < b[o[1]] ? -1 : 0) * (o[2] === 'desc' ? -1 : 1); });
    }
    if (q.get('limit')) list = list.slice(0, +q.get('limit'));
    return list;
  }
  var FALLBACK = {
    community_posts: function (u) { return loadCommunity().then(function (c) { return rows(c.community_posts, u); }); },
    community_comments: function (u) { return loadCommunity().then(function (c) { return rows(c.community_comments, u); }); },
    community_messages: function (u) { return loadCommunity().then(function (c) { return rows(c.community_messages, u); }); },
    site_stats: function () { return json([{ key: 'visitors', count: VISITORS }]); }
  };
  window.fetch = function (input, init) {
    var raw = typeof input === 'string' ? input : input && input.url;
    var u;
    try { u = new URL(raw, location.href); } catch (e) { return realFetch(input, init); }
    if (!/\.supabase\.co$/.test(u.hostname)) return realFetch(input, init);
    var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    var path = u.pathname;
    var t = /^\/rest\/v1\/(\w+)$/.exec(path), table = t && t[1];
    if (method === 'GET' && table === 'scripture_pages') return load().then(function (all) { return rows(all, u); });
    if (method === 'GET' && AI_TABLES[table]) return Promise.resolve(json([], 200, { 'Content-Range': '*/0' }));
    if (path.indexOf('/functions/v1/') === 0) return Promise.resolve(json({ code: 'NOT_WIRED', message: 'the ai surfaces are not wired in this archive' }, 503));
    var res = realFetch(input, init);
    if (method === 'GET' && table && FALLBACK[table]) {
      return res.then(function (r) { return r.ok ? r : FALLBACK[table](u); }, function () { return FALLBACK[table](u); });
    }
    return res;
  };
})();
