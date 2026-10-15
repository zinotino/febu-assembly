// Vercel cron (vercel.json): one cheap read a day so the free Supabase project never idles into a pause.
const URL = "https://tytebptpuiiemuxlaeab.supabase.co/rest/v1/site_stats?select=count&limit=1";
const KEY = "sb_publishable_bLoFVOha_bibytVyIewvQQ_z8QEmHpu"; // publishable: already public in the bundle

module.exports = async (req, res) => {
  const r = await fetch(URL, { headers: { apikey: KEY } });
  res.status(r.ok ? 200 : 502).json({ supabase: r.status });
};
