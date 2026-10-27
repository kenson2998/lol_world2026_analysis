// Signed GET against the scoregg API, reusing the site's own sign module (scripts/scoregg_sign.js).
// usage: node scoregg.js /services/path.php '{"param":"value"}'
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const md5 = s => crypto.createHash("md5").update(String(s)).digest("hex");
const src = fs.readFileSync(path.join(__dirname, "scoregg_sign.js"), "utf8");
const exp = {};
const req = id => (id === 13 ? { a: x => typeof x } : id === 439 ? md5 : {});
req.d = (t, k, g) => Object.defineProperty(t, k, { get: g, enumerable: true });
new Function("return " + src)()({}, exp, req);
const sign = exp.a;

const [apiPath, extra] = process.argv.slice(2);
const params = Object.assign({ timezone: "8", appid: "1", api_version: "9.9.9", plate: "web", platform: "web",
  language_id: "1", gameID: "1", ts: String(Math.round(Date.now() / 1000)) }, JSON.parse(extra || "{}"));
params.sign = sign(params);
const url = "https://api-v2.scoregg.com" + apiPath + "?" + new URLSearchParams(params).toString();
process.stdout.write(execFileSync("curl", ["-s", "--max-time", "30", "-A", "Mozilla/5.0 Chrome/128",
  "-H", "Origin: https://www.scoregg.com", "-H", "Referer: https://www.scoregg.com/", url]));
