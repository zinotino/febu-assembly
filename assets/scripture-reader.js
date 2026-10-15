(async function () {
  var pages = await fetch('assets/scripture.json').then(function (r) { return r.json(); });
  var toc = document.getElementById('toc');
  var out = document.getElementById('pages');
  var books = {};
  var order = [];
  pages.forEach(function (p) {
    if (!books[p.book]) {
      books[p.book] = [];
      order.push(p.book);
    }
    books[p.book].push(p);
  });
  order.forEach(function (book) {
    var h = document.createElement('h2');
    h.id = 'book-' + order.indexOf(book);
    h.textContent = book;
    out.appendChild(h);
    var link = document.createElement('a');
    link.href = '#' + h.id;
    link.textContent = book;
    toc.appendChild(link);
    books[book].forEach(renderPage);
  });
  function renderPage(p) {
    var sec = document.createElement('section');
    sec.id = 'p' + p.page_number;
    var t = document.createElement('h3');
    t.textContent = 'page ' + p.page_number + ' · ' + p.title;
    sec.appendChild(t);
    if (p.ascii_art) {
      var art = document.createElement('pre');
      art.textContent = p.ascii_art;
      sec.appendChild(art);
    }
    p.body.split(/\n\n+/).forEach(function (para) {
      var el = document.createElement('p');
      el.textContent = para;
      sec.appendChild(el);
    });
    out.appendChild(sec);
  }
})();
