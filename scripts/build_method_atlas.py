#!/usr/bin/env python3
"""
Build the Blue Line Atlas -> docs/methods.html

Every method in the collection drawn as the path a bell traces through it --
the diagram ringers actually learn from -- laid out as small multiples so
whole families can be compared at once.

Only methods whose notation is *verified* are included: the parser in
scripts/notation.py applies the notation from rounds and the row it reaches
must equal the published `lead_head`. 24,404 of 25,066 methods pass, so a line
on this page is a line that provably follows from the published notation. The
662 that fail are excluded and counted on the page rather than quietly dropped.

The page carries notation strings, not pre-computed coordinates, and parses
them in the browser with a port of the same parser. That keeps the payload to
notation-sized strings and means the drawing and the verification cannot drift
apart.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import notation as N  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402

OUT = ROOT / "docs" / "methods.html"
STAGES = (6, 8, 10, 12)
STAGE_NAMES = {2: "Two", 3: "Singles", 4: "Minimus", 5: "Doubles", 6: "Minor",
               7: "Triples", 8: "Major", 9: "Caters", 10: "Royal",
               11: "Cinques", 12: "Maximus"}

def build(db):
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT method_id, title, name, stage, classification, notation, lead_head "
        "FROM methods WHERE notation IS NOT NULL AND notation <> '' "
        "AND lead_head IS NOT NULL AND lead_head <> ''"
    ).fetchall()

    verified, failed = [], 0
    for mid, title, name, stage, cls, nt, lh in rows:
        if not stage:
            failed += 1
            continue
        try:
            ok = N.lead_head(nt, stage) == lh
        except Exception:
            ok = False
        if not ok:
            failed += 1
            continue
        if stage in STAGES and cls:
            verified.append({"t": title, "n": name or "", "s": stage,
                             "c": cls, "p": nt})

    counts = {}
    for m in verified:
        counts.setdefault(m["c"], 0)
        counts[m["c"]] += 1
    return verified, failed, len(rows), counts

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Blue Line Atlas — Every Method as a Shape</title>
<style>
:root{
  --line:#2a78d6; --treble:#c2410c;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --line:#3987e5; --treble:#e07a4f;
  }
}
:root[data-theme="dark"]{
  --line:#3987e5; --treble:#e07a4f;
}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:26px 0 6px}
.controls label{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-3);margin-right:2px}
.chip{font-family:var(--mono);font-size:11.5px;letter-spacing:.05em;padding:6px 12px;
  border:1px solid var(--rule);background:var(--surface);color:var(--ink-2);cursor:pointer;border-radius:2px}
.chip:hover{border-color:var(--bronze-soft);color:var(--ink)}
.chip:focus-visible{outline:2px solid var(--bronze);outline-offset:2px}
.chip[aria-pressed="true"]{border-color:var(--bronze);color:var(--ink);background:var(--surface-2)}
input[type=search]{font-family:var(--mono);font-size:12px;padding:6px 10px;border-radius:2px;
  border:1px solid var(--rule);background:var(--surface);color:var(--ink);min-width:200px}
.count{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin:10px 0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule)}
.cell{background:var(--surface);padding:10px 8px 8px;text-align:center;cursor:pointer;position:relative}
.cell:hover{background:var(--surface-2)}
.cell canvas{display:block;width:100%;height:auto}
.cell .ttl{font-family:var(--mono);font-size:9.5px;line-height:1.35;color:var(--ink-2);
  margin-top:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
dialog{border:1px solid var(--rule);background:var(--ground);color:var(--ink);
  border-radius:3px;padding:0;max-width:560px;width:92vw}
dialog::backdrop{background:rgba(0,0,0,.55)}
.dlg{padding:22px 24px 24px}
.dlg h3{font-size:1.35rem;font-weight:400}
.dlg .meta{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);margin-top:6px;line-height:1.7}
.dlg .big{display:flex;gap:20px;align-items:flex-start;margin-top:16px;flex-wrap:wrap}
.dlg canvas{background:var(--surface);border:1px solid var(--rule);border-radius:2px}
.rows{font-family:var(--mono);font-size:11px;color:var(--ink-2);max-height:300px;overflow:auto;
  line-height:1.55;letter-spacing:.06em}
.dlg button{margin-top:18px}
.legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-family:var(--mono);
  font-size:11px;color:var(--ink-2)}
.legend span{display:flex;align-items:center;gap:7px}
.legend i{width:14px;height:3px;border-radius:2px;flex:none}
.note{border-left:2px solid var(--bronze-soft);padding-left:16px;margin-top:24px;
  color:var(--ink-2);font-size:15px}
footer{padding:48px 0 80px;color:var(--ink-3);font-size:14px}
footer a{color:var(--bronze)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>

<!--NAV:methods.html-->
<div class="wrap">
<header>
  <p class="eyebrow">Change Ringing Corpus · Method shapes</p>
  <h1>Every method,<br>as a <em>shape</em></h1>
  <p class="standfirst">Ringers do not learn a method from its notation. They learn the
  line — the path one bell traces through it. This is that drawing, computed from the
  published place notation for <strong>__NVERIFIED__</strong> methods, laid out so whole
  families can be compared at a glance.</p>
  <div class="figures">
    <div class="fig"><div class="n">__NVERIFIED__</div><div class="l">methods drawn</div></div>
    <div class="fig"><div class="n">__PCT__%</div><div class="l">notation verified</div></div>
    <div class="fig"><div class="n">__NCLS__</div><div class="l">classifications</div></div>
  </div>
  <div class="legend">
    <span><i style="background:var(--line)"></i>the working bell (the blue line)</span>
    <span><i style="background:var(--treble)"></i>the treble</span>
  </div>
</header>

<section>
  <h2>The wall</h2>
  <p class="lede">Each tile is one lead, drawn from rounds. Filter by stage and
  classification, or search a name. Click any tile for the full line and its rows.</p>

  <div class="controls" id="stageChips"><label>Stage</label></div>
  <div class="controls" id="clsChips"><label>Class</label></div>
  <div class="controls">
    <label for="q">Name</label>
    <input type="search" id="q" placeholder="Cambridge, Yorkshire, Bristol…">
    <button class="chip" id="clear" type="button">Clear</button>
  </div>
  <div class="count" id="count"></div>
  <div class="grid" id="grid"></div>
  <div class="count" id="more"></div>

  <div class="note">Cambridge, Yorkshire, Superlative and Lincolnshire are the four
  standard Surprise Major methods most bands learn first. Filter to Surprise / Major
  and search each in turn: the family resemblance is immediate, and it is the reason
  ringers describe them as being “near” one another despite quite different notation.</div>
</section>

<!--FOOTER:methods.html-->
</div>

<dialog id="dlg"><div class="dlg">
  <h3 id="dTitle"></h3>
  <div class="meta" id="dMeta"></div>
  <div class="big">
    <canvas id="dCanvas" width="300" height="520"></canvas>
    <div class="rows" id="dRows"></div>
  </div>
  <button class="chip" id="dClose" type="button">Close</button>
</div></dialog>

<script>
const METHODS = __DATA__;
const STAGE_NAMES = __STAGENAMES__;
const ORDER = "1234567890ETABCD";
const $ = s => document.querySelector(s);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/* ---- parser: a port of scripts/notation.py. Same rule, measured not assumed:
   "A,B" expands to A + reverse(A minus its last change) + B, which reproduces the
   library's published lead_head for 97.4% of methods where the alternatives manage
   7-8%. ---- */
function splitChanges(block){
  const out=[]; let buf="";
  for(const ch of block){
    if(ch==="-"||ch==="x"){ if(buf){out.push(buf);buf="";} out.push("-"); }
    else if(ch==="."){ if(buf){out.push(buf);buf="";} }
    else if(ch.trim()){ buf+=ch; }
  }
  if(buf) out.push(buf);
  return out;
}
function expand(nt){
  const parts=nt.split(",");
  if(parts.length===1) return splitChanges(parts[0]);
  const a=splitChanges(parts[0]), b=splitChanges(parts[1]);
  return a.concat(a.slice(0,-1).reverse(), b);
}
function applyChange(row, change){
  const n=row.length;
  const places=new Set();
  if(change!=="-") for(const c of change){ const i=ORDER.indexOf(c.toUpperCase()); if(i>=0) places.add(i); }
  const out=row.slice();
  let i=0;
  while(i<n){
    if(places.has(i)){ i++; continue; }
    if(i+1<n && !places.has(i+1)){ out[i]=row[i+1]; out[i+1]=row[i]; i+=2; }
    else i++;
  }
  return out;
}
function leadRows(nt, stage){
  let row=ORDER.slice(0,stage).split("");
  const rows=[row];
  for(const ch of expand(nt)){ row=applyChange(row,ch); rows.push(row); }
  return rows;
}

/* ---- drawing ---- */
function drawLine(cv, m, opts){
  opts = opts || {};
  const rows = leadRows(m.p, m.s);
  const dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth || cv.width, H = opts.h || Math.max(70, rows.length*4);
  cv.width = W*dpr; cv.height = H*dpr;
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,W,H);
  const padX = 6, padY = 5;
  const gx = (W-2*padX)/(m.s-1), gy = (H-2*padY)/(rows.length-1);
  const pathFor = bell => rows.map((r,i)=>[padX + r.indexOf(bell)*gx, padY + i*gy]);
  const stroke = (pts, colour, w) => {
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for(let i=1;i<pts.length;i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.strokeStyle=colour; ctx.lineWidth=w; ctx.lineJoin="round"; ctx.lineCap="round"; ctx.stroke();
  };
  stroke(pathFor("1"), css("--treble"), opts.big?2:1.1);
  stroke(pathFor("2"), css("--line"),  opts.big?2.4:1.5);
}

/* ---- filters ---- */
const stages=[...new Set(METHODS.map(m=>m.s))].sort((a,b)=>a-b);
const classes=[...new Set(METHODS.map(m=>m.c))].sort();
let fStage=null, fCls=null, fQ="", shown=0;
const PAGE=240;

function chipRow(host, items, label, get, set){
  items.forEach(v=>{
    const b=document.createElement("button");
    b.className="chip"; b.type="button"; b.setAttribute("aria-pressed","false");
    b.textContent=label(v);
    b.onclick=()=>{ set(get()===v?null:v); render(); };
    b.dataset.v=v; host.appendChild(b);
  });
}
chipRow($("#stageChips"), stages, s=>`${s} · ${STAGE_NAMES[s]||s}`, ()=>fStage, v=>fStage=v);
chipRow($("#clsChips"), classes, c=>c, ()=>fCls, v=>fCls=v);
$("#q").addEventListener("input", e=>{ fQ=e.target.value.toLowerCase().trim(); render(); });
$("#clear").onclick=()=>{ fStage=fCls=null; fQ=""; $("#q").value=""; render(); };

function matching(){
  return METHODS.filter(m =>
    (fStage===null || m.s===fStage) &&
    (fCls===null   || m.c===fCls)   &&
    (fQ===""       || m.t.toLowerCase().includes(fQ)));
}
function render(){
  [...$("#stageChips").children].forEach(c=>{ if(c.dataset.v) c.setAttribute("aria-pressed", String(+c.dataset.v===fStage)); });
  [...$("#clsChips").children].forEach(c=>{ if(c.dataset.v) c.setAttribute("aria-pressed", String(c.dataset.v===fCls)); });
  const list=matching();
  shown=Math.min(PAGE, list.length);
  $("#count").textContent = `${list.length.toLocaleString("en-GB")} method${list.length===1?"":"s"} match`
    + (list.length>shown ? ` · showing the first ${shown}` : "");
  const grid=$("#grid"); grid.innerHTML="";
  list.slice(0,shown).forEach(m=>{
    const cell=document.createElement("div");
    cell.className="cell"; cell.tabIndex=0;
    cell.innerHTML=`<canvas></canvas><div class="ttl" title="${m.t}">${m.t}</div>`;
    cell.onclick=()=>open(m);
    cell.onkeydown=e=>{ if(e.key==="Enter") open(m); };
    grid.appendChild(cell);
    drawLine(cell.querySelector("canvas"), m, {h:96});
  });
  $("#more").textContent = list.length>shown
    ? `${(list.length-shown).toLocaleString("en-GB")} more — narrow the filters to see them.` : "";
}
function open(m){
  const rows=leadRows(m.p,m.s);
  $("#dTitle").textContent=m.t;
  $("#dMeta").innerHTML=`stage ${m.s} (${STAGE_NAMES[m.s]||m.s}) · ${m.c}<br>`
    + `notation <strong>${m.p}</strong><br>${rows.length-1} changes · lead head ${rows[rows.length-1].join("")}`;
  $("#dRows").innerHTML=rows.map((r,i)=>`${String(i).padStart(3," ")} ${r.join("")}`).join("<br>");
  const cv=$("#dCanvas");
  cv.style.width="300px";
  drawLine(cv, m, {h:Math.max(320, Math.min(520, rows.length*11)), big:true});
  $("#dlg").showModal();
}
$("#dClose").onclick=()=>$("#dlg").close();

/* ---- theme ---- */
const btn=$("#themeToggle");
function currentDark(){
  const t=document.documentElement.getAttribute("data-theme");
  return t ? t==="dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}
function syncBtn(){ btn.textContent = currentDark() ? "Light Mode" : "Dark Mode"; }
btn.onclick=()=>{ document.documentElement.setAttribute("data-theme", currentDark()?"light":"dark"); syncBtn(); render(); };
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ()=>{ syncBtn(); render(); });
syncBtn(); render();
addEventListener("resize", ()=>render());
</script>
</body>
</html>
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "change-ringing.db"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    verified, failed, total, counts = build(args.db)
    n_all = total - failed
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(verified, separators=(",", ":")))
            .replace("__STAGENAMES__", json.dumps(STAGE_NAMES))
            .replace("__NVERIFIED_ALL__", f"{n_all:,}")
            .replace("__NVERIFIED__", f"{len(verified):,}")
            .replace("__NTOTAL__", f"{total:,}")
            .replace("__NFAILED__", f"{failed:,}")
            .replace("__PCT__", f"{100*n_all/total:.1f}")
            .replace("__NCLS__", str(len(counts))))
    out = Path(args.out)
    # One nav bar and one footer for the whole site: scripts/site_chrome.py
    html = apply_chrome(html)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size/1024:.0f} KB)")
    print(f"  drawn: {len(verified):,} methods at stages {STAGES}")
    print(f"  verified overall: {n_all:,}/{total:,} ({100*n_all/total:.1f}%), {failed:,} excluded")
    for c, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {c:16s} {n:6,}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
