"""Appli de test Action : statut du serveur actif. L'état (visites, historique des serveurs) vit dans le volume /data :
s'il survit à un transfert, la liste des serveurs s'allonge et le compteur continue."""
import json, os, shutil, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA = "/data/state.json"
HOST = open("/host/hostname").read().strip() if os.path.exists("/host/hostname") else os.uname().nodename
BOOT = time.time()

def load():
    try:
        return json.load(open(DATA))
    except Exception:
        return {"visits": 0, "first": time.time(), "servers": []}

def save(st):
    tmp = DATA + ".tmp"
    json.dump(st, open(tmp, "w"))
    os.replace(tmp, DATA)

st = load()
if not st["servers"] or st["servers"][-1]["host"] != HOST:
    st["servers"].append({"host": HOST, "since": time.time()})
    save(st)

def info():
    mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
    du = shutil.disk_usage("/")
    return {
        "host": HOST, "now": time.time(), "boot": BOOT,
        "uptime_host": float(open("/proc/uptime").read().split()[0]),
        "load": os.getloadavg(), "cpus": os.cpu_count(),
        "mem_total": mem["MemTotal"] * 1024, "mem_avail": mem["MemAvailable"] * 1024,
        "disk_total": du.total, "disk_used": du.used,
        "visits": st["visits"], "first": st["first"], "servers": st["servers"],
    }

PAGE = """<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Statut du serveur</title>
<style>:root{color-scheme:light dark;--bg:#f4f1ec;--card:#fff;--fg:#1c1c1e;--mut:#8a8a8e;--app:#5b5bd6}@media(prefers-color-scheme:dark){:root{--bg:#000;--card:#1c1c1e;--fg:#f2f2f7}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px system-ui,sans-serif;padding:20px}main{max-width:720px;margin:auto}h1{font-size:22px;margin:0 0 4px}.m{color:var(--mut)}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}.c{background:var(--card);border-radius:18px;padding:16px;box-shadow:0 2px 12px #0001}
.c b{display:block;font-size:24px;margin-top:4px}.bar{height:8px;border-radius:4px;background:#8882;margin-top:8px;overflow:hidden}.bar i{display:block;height:100%;background:var(--app)}
li{padding:6px 0}code{font-family:ui-monospace,monospace}</style>
<main><h1>Statut du serveur actif</h1><div class="m" id="sub">chargement…</div>
<div class="g"><div class="c">Serveur<b id="host"></b></div><div class="c">Actif depuis<b id="up"></b></div><div class="c">Visites (survit aux transferts)<b id="vis"></b></div></div>
<div class="g"><div class="c">Charge (1 / 5 / 15 min)<b id="load"></b></div><div class="c">Mémoire<b id="mem"></b><div class="bar"><i id="memb"></i></div></div><div class="c">Disque<b id="disk"></b><div class="bar"><i id="diskb"></i></div></div></div>
<div class="c"><b style="font-size:17px">Serveurs successifs</b><ol id="srv"></ol></div></main>
<script>
const g=n=>(n/2**30).toFixed(1)+" Go",d=s=>{s=Math.round(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return (h?h+" h ":"")+m+" min "+(s%60)+" s"},$=i=>document.getElementById(i);
async function t(){try{const j=await (await fetch("/api/status",{cache:"no-store"})).json();
$("sub").textContent="Mis à jour à "+new Date(j.now*1000).toLocaleTimeString("fr-FR");$("host").textContent=j.host;$("up").textContent=d(j.now-j.boot);$("vis").textContent=j.visits;
$("load").textContent=j.load.map(x=>x.toFixed(2)).join(" / ");const mu=j.mem_total-j.mem_avail;$("mem").textContent=g(mu)+" / "+g(j.mem_total);$("memb").style.width=(100*mu/j.mem_total)+"%";
$("disk").textContent=g(j.disk_used)+" / "+g(j.disk_total);$("diskb").style.width=(100*j.disk_used/j.disk_total)+"%";
$("srv").innerHTML=j.servers.map((s,i)=>"<li><code>"+s.host+"</code> <span class='m'>depuis "+new Date(s.since*1000).toLocaleString("fr-FR")+(i==j.servers.length-1?" · actif":"")+"</span></li>").join("");
}catch(e){$("sub").textContent="serveur injoignable…"}setTimeout(t,2000)}t();
</script></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/status"):
            st["visits"] += 1; save(st)
            body, ct = json.dumps(info()).encode(), "application/json"
        elif self.path in ("/", "/index.html"):
            body, ct = PAGE.encode(), "text/html; charset=utf-8"
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header("content-type", ct); self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body))); self.end_headers(); self.wfile.write(body)

ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
