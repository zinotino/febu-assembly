// Vercel cron (vercel.json): once a day, ask the Internet Archive to save ledger.txt, so dated copies that nobody in
// the group controls pile up with nobody involved. Every copy is listed at
// https://web.archive.org/web/*/https://febu-ledger.vercel.app/ledger.txt
// Anyone may call it: it takes no input and asks for a save of a public file. If CRON_SECRET is set in Vercel, only
// the cron (which sends it) may.
const SAVE = "https://web.archive.org/save/https://febu-ledger.vercel.app/ledger.txt";

module.exports = async (req, res) => {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.authorization !== "Bearer " + secret) return res.status(401).json({ archive: "no" });
  try {
    const r = await fetch(SAVE, { redirect: "manual" });   // a save answers 302 to the new copy
    res.status(r.status < 400 ? 200 : 502).json({ archive: r.status, copy: r.headers.get("location") });
  } catch (e) {
    res.status(502).json({ archive: "unreachable" });
  }
};
