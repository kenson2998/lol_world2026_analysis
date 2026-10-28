// Smoke test: run the built report's inline script against a tiny fake DOM to catch runtime errors.
// usage: node smoke_test.js data/worlds2026_soloq.html
const fs = require("fs");
const page = fs.readFileSync(process.argv[2], "utf8");
const src = page.slice(page.lastIndexOf("<script>") + 8, page.lastIndexOf("</script>"));
const els = {};
const mk = id => ({
  id, hidden: false, innerHTML: "", textContent: "", dataset: {}, style: {}, classList: { add() {}, remove() {} },
  tabIndex: 0, attrs: {},
  setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
  addEventListener() {}, querySelectorAll() { return []; }, querySelector(sel) { return (els[`${id} ${sel}`] ||= mk(`${id} ${sel}`)); },
  append() {}, focus() {}, scrollIntoView() {}, closest() { return null; }, offsetWidth: 0, offsetHeight: 0,
});
global.document = {
  getElementById: id => (els[id] ||= mk(id)),
  querySelectorAll: sel => (sel === ".vtab" ? ["worlds", "predict", "matchup", "player"].map(v => Object.assign(document.getElementById("tab-" + v), { dataset: { view: v } })) : []),
  querySelector: () => mk("q"), createElement: () => mk("new"), addEventListener() {}, body: { append() {} },
};
global.localStorage = { getItem: () => null, setItem() {} };
global.location = { hash: process.env.HASH || "" };
global.matchMedia = () => ({ matches: false });
global.scrollTo = () => {};
global.addEventListener = () => {};
global.requestAnimationFrame = f => f();
global.innerWidth = 1200;
global.CSS = { escape: s => s };
const api = new Function(src + "\n;return typeof TABLES === 'undefined' ? {} : { TABLES, drawTable, clickSort };")();
// sortable tables, driven through the same clickSort() the header buttons use
const rowsOf = (id, n) => (els[`${id} tbody`].innerHTML.split(/<tr[ >]/).slice(1, n + 1)).map(r =>
  [...r.matchAll(/<td[^>]*>(.*?)<\/td>/g)].map(m => m[1].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim()));
const C = api.TABLES?.["champ-table"];
if (C) {
  const col = name => C.cols.findIndex(c => c[0] === name);
  const top = n => rowsOf("champ-table", n).map(c => `${c[0]} 選${c[2]} 禁${c[3]} ${c[6]}`);
  const click = (name, multi) => { api.clickSort(C, col(name), multi); api.drawTable(C); };
  click("勝率", false); console.log("champ 勝率 ▼:", top(3));
  click("勝率", false); click("選用", true); console.log("champ 勝率 ▼ → 選用 ▼:", top(3));
}
const PT = api.TABLES?.["player-table"];
if (PT) {
  const col = name => PT.cols.findIndex(c => c[0] === name);
  const top = n => rowsOf("player-table", n).map(c => `${c[0]} ${c[1]} ${c[2]} | ${c[6]} KDA ${c[7]} | DPM ${c[11]} | GD15 ${c[14]}`);
  console.log("players (default KDA ▼):", top(4));
  api.clickSort(PT, col("每分傷害"), false); api.drawTable(PT); console.log("players 每分傷害 ▼:", top(3));
  PT.filter = r => r.role === "support"; api.drawTable(PT); console.log("supports only, 每分傷害 ▼:", top(3), "rows:", rowsOf("player-table", 99).length);
}
const body = els["wv-body"]?.innerHTML || "";
console.log("worlds html chars:", body.length, "| sections:", (body.match(/class="wsec"/g) || []).length,
  "| result cards:", (body.match(/class="res"/g) || []).length, "| foot chars:", (els["wv-foot"]?.innerHTML || "").length);
console.log("view-worlds hidden:", els["view-worlds"].hidden, "| view-predict hidden:", els["view-predict"]?.hidden,
  "| view-matchup hidden:", els["view-matchup"]?.hidden);
const mu = els["mu-body"]?.innerHTML || "";
console.log("matchup lane cards:", (mu.match(/class="cb"/g) || []).length, "| lane rows:", (mu.match(/<li class="r\d/g) || []).length);
const pv = els["pv-body"]?.innerHTML || "";
console.log("predict sections:", (pv.match(/class="wsec"/g) || []).length, "| kpis:",
  (pv.match(/<div class="kpi"><b>[^<]*<\/b><span>[^<]*/g) || []).map(s => s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()));
// optional extra patterns to count in the Worlds page, e.g. node smoke_test.js page.html 'class="pk"' '3-1'
for (const pat of process.argv.slice(3)) console.log(`count ${pat}:`, body.split(pat).length - 1);
