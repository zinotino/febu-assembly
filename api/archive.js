// Vercel cron (vercel.json): once a day, ask the Internet Archive to save ledger.txt, so dated copies that nobody in
// the group controls pile up with nobody involved. Every copy is listed at
// https://web.archive.org/web/*/https://febu-ledger.vercel.app/ledger.txt
const SAVE = "https://web.archive.org/save/https://febu-ledger.vercel.app/ledger.txt";

module.exports = async (req, res) => {
  const r = await fetch(SAVE, { redirect: "manual" });   // a save answers 302 to the new copy
  res.status(r.status < 400 ? 200 : 502).json({ archive: r.status, copy: r.headers.get("location") });
};
