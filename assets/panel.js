/* Medical Sales Hub — Career Centre jobs-map panel.
 * Served to the live Hub page via jsDelivr; never inlined in page content,
 * because WordPress HTML-escapes literal & < > there and breaks the script.
 */
(function(){
  var css = "/* KORE-style restyle (Lou, 27/11/2026): navy stage, gold coastline, gold pins,\n   region cards with gold count badges, serif headline. Namespaced to #jmPanel. */\n#jmPanel{--k-navy:#071731;--k-deep:#030D1F;--k-gold:#CFA654;--k-gold2:#EECB6F;--k-goldt:#E0BE8E;--k-mist:#DBE3EE;--k-serif:'Cormorant Garamond',Georgia,serif;\n  background:radial-gradient(900px 420px at 85% 0%,rgba(207,166,84,.10),transparent 70%),linear-gradient(180deg,#071731 0%,#030D1F 100%)!important;\n  border:1px solid rgba(207,166,84,.32)!important;border-radius:22px!important;color:#fff;overflow:hidden;box-shadow:0 40px 80px -40px rgba(3,13,31,.7)}\n#jmPanel>h2,#jmPanel>.body{display:none!important}\n#jmPanel .jm{font-size:13px;color:#fff}\n.jm-head{padding:44px 40px 8px}\n.jm-kick{margin:0 0 10px;font:700 12px/1.3 Inter,system-ui,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--k-goldt)}\n.jm-head h3{margin:0;font:500 44px/1.08 var(--k-serif);color:#fff;letter-spacing:-.01em}\n.jm-head h3 em{font-style:italic;color:var(--k-goldt)}\n.jm-lede{margin:14px 0 0;max-width:760px;font-size:15px;line-height:1.6;color:var(--k-mist)}\n.jm-stamp{display:inline-flex;align-items:center;gap:8px;margin-top:16px;padding:7px 13px;border-radius:999px;border:1px solid rgba(207,166,84,.35);background:rgba(3,13,31,.55);font:600 12px/1 Inter,sans-serif;color:var(--k-mist)}\n.jm-stamp i{width:8px;height:8px;border-radius:50%;background:var(--k-gold2);box-shadow:0 0 10px var(--k-gold2);animation:jmblink 2s ease-in-out infinite}\n@keyframes jmblink{50%{opacity:.35}}\n.jm-wrap{display:grid;grid-template-columns:230px 1fr;gap:0;margin-top:26px;border-top:1px solid rgba(207,166,84,.22)}\n@media(max-width:860px){.jm-wrap{grid-template-columns:1fr}}\n.jm-filters{padding:18px 20px 22px;border-right:1px solid rgba(207,166,84,.22);background:rgba(3,13,31,.35)}\n@media(max-width:860px){.jm-filters{order:2;border-right:none;border-top:1px solid rgba(207,166,84,.22)}.jm-main{order:1}}\n.jm-grp{border-bottom:1px solid rgba(207,166,84,.16)}\n.jm-grp:last-of-type{border-bottom:none}\n.jm-grp>summary{padding:11px 2px;cursor:pointer;font-weight:700;color:#fff;list-style:none;display:flex;justify-content:space-between;align-items:center;font-size:12.5px;letter-spacing:.02em}\n.jm-grp>summary::-webkit-details-marker{display:none}\n.jm-grp>summary:hover{color:var(--k-goldt)}\n.jm-grp>summary::after{content:'+';color:var(--k-gold);font-weight:400;font-size:16px}\n.jm-grp[open]>summary::after{content:'\\2013'}\n.jm-opts{padding:0 2px 12px;display:flex;flex-direction:column;gap:8px}\n.jm-opts label{font-size:12.5px;display:flex;align-items:center;gap:8px;color:var(--k-mist);cursor:pointer;line-height:1.3}\n.jm-opts label:hover{color:#fff}\n.jm-opts input{accent-color:var(--k-gold);flex:none}\n.jm-n{color:var(--k-goldt);font-size:11px;margin-left:auto;font-variant-numeric:tabular-nums;opacity:.85}\n.jm-clear{width:100%;margin-top:16px;background:transparent;border:1px solid rgba(207,166,84,.45);border-radius:10px;padding:9px;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--k-goldt);cursor:pointer;font-family:inherit;font-weight:700}\n.jm-clear:hover{background:rgba(207,166,84,.12);color:#fff}\n.jm-main{min-width:0}\n.jm-bar{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:16px 24px;flex-wrap:wrap;border-bottom:1px solid rgba(207,166,84,.22)}\n.jm-count{font-size:13px;color:var(--k-mist)}.jm-count b{color:var(--k-gold2);font:600 22px/1 var(--k-serif);margin-right:3px}\n.jm-hint{font-size:12px;color:var(--k-mist);opacity:.85}\n.jm-stage{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:22px;padding:22px 24px;align-items:start;border-bottom:1px solid rgba(207,166,84,.22)}\n@media(max-width:1100px){.jm-stage{grid-template-columns:1fr}}\n.jm-mapbox{position:relative;min-width:0;border-radius:20px;overflow:hidden;padding:10px;background:radial-gradient(500px 400px at 70% 78%,rgba(207,166,84,.16),transparent 70%),linear-gradient(165deg,#0b1f3d 0%,#030D1F 100%);border:1px solid rgba(207,166,84,.32);box-shadow:0 40px 80px -40px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.08)}\n.jm-mapbox::before{content:\"\";position:absolute;inset:0;background-image:linear-gradient(rgba(207,166,84,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(207,166,84,.05) 1px,transparent 1px);background-size:40px 40px;pointer-events:none}\n.jm-mapbox svg{position:relative;width:100%;height:auto;display:block;max-height:640px;margin:0 auto}\n.jm-region{cursor:pointer;transition:fill .25s;fill-rule:evenodd}\n.jm-region:hover{fill:#1a3a63}\n.jm-region.sel{fill:#1d4373}\n.jm-coast{fill:none;stroke:#CFA654;stroke-width:1;stroke-opacity:.75;pointer-events:none}\n.jm-coast.sel{stroke:#EECB6F;stroke-width:2.2;stroke-opacity:1}\n.jm-pin{cursor:pointer;outline:none}\n.jm-pin .ring{pointer-events:none;fill:none;stroke:#EECB6F;stroke-width:1.4;transform-box:fill-box;transform-origin:center;animation:jmring 2.8s ease-out infinite}\n.jm-pin .ring.r2{animation-delay:1.4s}\n@keyframes jmring{0%{transform:scale(1);opacity:.8}100%{transform:scale(2.6);opacity:0}}\n.jm-pin .core{stroke:rgba(3,13,31,.6);stroke-width:1;transform-box:fill-box;transform-origin:center;transition:transform .25s}\n.jm-pin:hover .core,.jm-pin.on .core,.jm-pin:focus-visible .core{transform:scale(1.18);filter:drop-shadow(0 0 7px #EECB6F)}\n.jm-pin:focus-visible .core{stroke:#fff;stroke-width:2.5}\n.jm-pin text{pointer-events:none;font:700 11px Inter,sans-serif;fill:#030D1F;text-anchor:middle;dominant-baseline:central;font-variant-numeric:tabular-nums}\n.jm-leg{position:absolute;right:14px;bottom:12px;display:flex;gap:14px;margin:0;font:600 11.5px/1 Inter,sans-serif;color:var(--k-mist);background:rgba(3,13,31,.75);padding:8px 12px;border-radius:999px;border:1px solid rgba(207,166,84,.3)}\n.jm-leg span{display:flex;align-items:center;gap:7px}\n.jm-leg i{width:9px;height:9px;border-radius:50%;background:#EECB6F;box-shadow:0 0 10px #EECB6F;display:inline-block}\n.jm-key{min-width:0}\n.jm-key h4{margin:2px 0 12px;font:700 11px/1.3 Inter,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--k-goldt)}\n.jm-cards{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}\n@media(max-width:560px){.jm-cards{grid-template-columns:1fr}}\n.jm-rb{width:100%;text-align:left;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;padding:11px 13px;border-radius:12px;border:1px solid rgba(207,166,84,.3);background:linear-gradient(160deg,rgba(255,255,255,.07),rgba(255,255,255,.02));color:#fff;cursor:pointer;box-shadow:0 18px 36px -24px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.08);transition:transform .25s,border-color .25s,background .25s;font:inherit}\n.jm-rb:hover{border-color:#CFA654;transform:translateY(-2px)}\n.jm-rb:focus-visible{outline:2px solid #fff;outline-offset:2px}\n.jm-rb[aria-pressed=\"true\"]{border-color:#CFA654;background:linear-gradient(135deg,#14304F,#0b1f3d);box-shadow:0 18px 36px -18px rgba(207,166,84,.55),inset 0 1px 0 rgba(255,255,255,.12)}\n.jm-rb .nm{font:700 13.5px/1.3 Inter,sans-serif;color:#fff}\n.jm-rb .sb{grid-column:1;font-size:12px;color:var(--k-mist)}\n.jm-rb .bd{grid-row:1/span 2;grid-column:2;align-self:center;display:grid;place-items:center;min-width:30px;height:28px;padding:0 6px;border-radius:8px;font:700 13px/1 Inter,sans-serif;color:#030D1F;background:linear-gradient(135deg,#B58B41,#EECB6F);box-shadow:0 8px 18px -8px rgba(207,166,84,.8),inset 0 1px 0 rgba(255,255,255,.4);font-variant-numeric:tabular-nums}\n.jm-rb.zero{opacity:.45}\n.jm-rb.nat{grid-column:1/-1;border-style:dashed}\n.jm-list{padding:6px 16px 16px}\n.jm-row{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;margin-top:8px;padding:14px 18px;text-decoration:none!important;color:inherit;border-radius:14px;border:1px solid rgba(207,166,84,.18);background:linear-gradient(160deg,rgba(255,255,255,.05),rgba(255,255,255,.015));transition:border-color .2s,transform .2s,background .2s}\n.jm-row:hover{border-color:#CFA654;background:linear-gradient(135deg,#14304F,#0b1f3d);transform:translateX(3px)}\n.jm-title{font-weight:700;font-size:14px;color:#fff;line-height:1.35}\n.jm-meta{font-size:11.5px;color:var(--k-mist);margin-top:8px;display:flex;gap:7px;flex-wrap:wrap;align-items:center}\n.jm-tag{display:inline-block;font-size:10.5px;font-weight:600;padding:3px 9px;border-radius:99px;background:rgba(219,227,238,.08);border:1px solid rgba(219,227,238,.2);color:var(--k-mist);white-space:nowrap}\n.jm-tag.lvl{color:#fff;border-color:rgba(219,227,238,.35)}\n.jm-tag.clin{background:#fff;border-color:#fff;color:#030D1F}\n.jm-tag.sal{color:#030D1F;border-color:transparent;background:linear-gradient(135deg,#B58B41,#EECB6F)}\n.jm-go{color:var(--k-gold2);font-size:20px;flex:none;font-weight:700}\n.jm-empty{padding:38px 24px;text-align:center;color:var(--k-mist);font-size:13px;line-height:1.6}\n.jm-empty b{display:block;color:#fff;font:500 22px/1.3 var(--k-serif);margin-bottom:6px}\n.jm-more{text-align:center;padding:18px}\n.jm-more button{background:linear-gradient(135deg,#B58B41,#EECB6F);color:#030D1F;border:none;border-radius:999px;padding:12px 28px;font-weight:700;font-size:12.5px;letter-spacing:.04em;cursor:pointer;font-family:inherit;box-shadow:0 12px 26px -12px rgba(207,166,84,.8)}\n.jm-more button:hover{filter:brightness(1.08)}\n.jm-loading{padding:36px;text-align:center;color:var(--k-mist);font-size:13px}\n@media(max-width:640px){.jm-head{padding:30px 18px 4px}.jm-head h3{font-size:32px}.jm-stage{padding:16px}.jm-bar{padding:14px 16px}.jm-list{padding:4px 10px 12px}.jm-leg{position:static;margin:10px auto 2px;width:fit-content}}\n@media(prefers-reduced-motion:reduce){.jm-pin .ring,.jm-stamp i{animation:none;opacity:0}}\n";
  var tag = document.createElement('style');
  tag.setAttribute('data-jm','1');
  tag.appendChild(document.createTextNode(css));
  document.head.appendChild(tag);
})();

(function(){
  // Live feed, refreshed daily at 06:00 UTC by the msh-jobs-map GitHub Action.
  // A push to that repo's main IS a publish — see its verify.py.
  var JOBS_SRC = (window.JOBS_SRC_OVERRIDE)
    || "https://raw.githubusercontent.com/louisehoult-beep/msh-jobs-map/main/data/jobs-data.json";
  var NATIONAL = "UK-wide / field-national";

  var state = { jobs: [], filters: {}, limit: 25 };

  var FILTER_DEFS = [
    { key:"category",  label:"Role type", open:true,
      display:function(v){ return v === "sales" ? "Sales roles" : "Clinical and product roles"; } },
    { key:"region",    label:"Nation / territory", open:true },
    { key:"level",     label:"Role level" },
    { key:"speciality",label:"Speciality" },
    { key:"salaryBand",label:"Salary band" },
    { key:"postedBand",label:"Posted" },
    { key:"recruiter", label:"Source" },
    { key:"clinical",  label:"Clinical background", display:function(v){
        return v === "yes" ? "Requires clinical experience" : "No clinical requirement stated"; } }
  ];

  function salaryBand(j){
    var s = j.salary_min;
    if (!s) return "Not stated";
    if (s < 35000) return "Up to £35k";
    if (s < 45000) return "£35k–£45k";
    if (s < 60000) return "£45k–£60k";
    return "£60k+";
  }
  function daysAgo(d){
    if(!d) return null;
    var t = Date.parse(d); if(isNaN(t)) return null;
    return Math.floor((Date.now()-t)/86400000);
  }
  function postedBand(j){
    var d = daysAgo(j.posted_date);
    if (d === null) return "Not stated";
    if (d <= 7) return "New this week";
    if (d <= 30) return "Last 30 days";
    return "Older than 30 days";
  }
  function fmtSalary(j){
    if (!j.salary_min) return null;
    var f = function(n){ return "£" + Math.round(n/1000) + "k"; };
    return (j.salary_max && j.salary_max !== j.salary_min)
      ? f(j.salary_min) + "–" + f(j.salary_max) : f(j.salary_min);
  }
  // Built from char codes on purpose. WordPress escapes literal & < > " '
  // inside page content, which turned the old version's regex into
  // /[&#038;...]/ and stopped the whole panel script from parsing.
  // Nothing here contains a character WordPress will touch.
  var _A = String.fromCharCode(38), _L = String.fromCharCode(60),
      _G = String.fromCharCode(62), _Q = String.fromCharCode(34),
      _P = String.fromCharCode(39);
  var _ESCMAP = {};
  _ESCMAP[_A] = _A + "amp;";  _ESCMAP[_L] = _A + "lt;";
  _ESCMAP[_G] = _A + "gt;";   _ESCMAP[_Q] = _A + "quot;";
  _ESCMAP[_P] = _A + "#39;";
  var _ESCRE = new RegExp("[" + _A + _L + _G + _Q + _P + "]", "g");
  function esc(s){
    return String(s==null?"":s).replace(_ESCRE, function(c){ return _ESCMAP[c]; });
  }

  // Prefer the recruiter's own stated location over the region bucket, but
  // not a bare postcode ("YO103SJ") which means nothing to a reader.
  var POSTCODE_ONLY = /^[A-Z]{1,2}\d[A-Z0-9]?\s*\d?[A-Z]{0,2}$/i;
  function placeLabel(j){
    var t = (j.location_text||"").trim();
    if (!t || POSTCODE_ONLY.test(t)) return j.region;
    t = t.replace(/\s*,\s*/g, ", ").replace(/\s+/g," ");
    if (t.length > 34) t = t.slice(0,32).replace(/[,\s]+$/,"") + "…";
    return t;
  }

  function derive(j){
    j._salaryBand = salaryBand(j);
    j._postedBand = postedBand(j);
    j._clinical   = j.clinical_experience_required ? "yes" : "no";
    j._recruiter  = j.recruiter || (j.source||"").replace("recruiter:","") || "other";
    j._speciality = j.speciality || "Not specified";
    return j;
  }
  // Aggregator rows (Reed, Adzuna) name the advertiser, so a member can see
  // which agency or employer the role is with, not just the feed it came from.
  var AGGREGATORS = {adzuna:"Adzuna", reed:"Reed"};
  function advertiser(j){
    var feed = AGGREGATORS[j._recruiter];
    return feed && j.company ? j.company + " via " + feed : j._recruiter;
  }
  function valueOf(j, key){
    if (key === "salaryBand") return j._salaryBand;
    if (key === "postedBand") return j._postedBand;
    if (key === "clinical")   return j._clinical;
    if (key === "recruiter")  return j._recruiter;
    if (key === "speciality") return j._speciality;
    return j[key];
  }

  function matching(exceptKey){
    return state.jobs.filter(function(j){
      for (var k in state.filters){
        if (k === exceptKey) continue;
        var sel = state.filters[k];
        if (sel && sel.size && !sel.has(valueOf(j,k))) return false;
      }
      return true;
    });
  }
  function visible(){ return matching(null); }

  // The list only appears once the reader has narrowed something — otherwise
  // the panel opens as a map, not a 300-row dump.
  function anyFilterActive(){
    for (var k in state.filters){
      if (state.filters[k] && state.filters[k].size) return true;
    }
    return false;
  }
  function activeFilterLabels(){
    var out = [];
    for (var k in state.filters){
      var sel = state.filters[k];
      if (sel && sel.size) sel.forEach(function(v){ out.push(v); });
    }
    return out;
  }

  function buildFilters(){
    var host = document.getElementById("jmFilters"), html = "";
    FILTER_DEFS.forEach(function(def){
      var pool = matching(def.key), counts = {};
      pool.forEach(function(j){ var v = valueOf(j,def.key); if(v!=null) counts[v]=(counts[v]||0)+1; });
      var keys = Object.keys(counts).sort(function(a,b){ return counts[b]-counts[a] || String(a).localeCompare(b); });
      if (!keys.length) return;
      var sel = state.filters[def.key];
      var anyOn = sel && sel.size;
      html += '<details class="jm-grp"'+((def.open||anyOn)?" open":"")+'><summary>'+esc(def.label)+'</summary><div class="jm-opts">';
      keys.forEach(function(v){
        var on = sel && sel.has(v);
        var lbl = def.display ? def.display(v) : esc(v);
        html += '<label><input type="checkbox" data-k="'+esc(def.key)+'" data-v="'+esc(v)+'"'+(on?" checked":"")+'>'
             +  '<span>'+lbl+'</span><span class="jm-n">'+counts[v]+'</span></label>';
      });
      html += "</div></details>";
    });
    host.innerHTML = html;
    host.querySelectorAll("input[type=checkbox]").forEach(function(cb){
      cb.addEventListener("change", function(){
        var k = cb.dataset.k, v = cb.dataset.v;
        if (!state.filters[k]) state.filters[k] = new Set();
        if (cb.checked) state.filters[k].add(v); else state.filters[k].delete(v);
        state.limit = 25; render();
      });
    });
  }

  // KORE-style map (Lou, 27/11/2026): navy land with a gold dot texture and a
  // glowing gold coastline, one gold pin per region sized by its count, and
  // region cards with gold count badges in place of the old colour key.
  var NUDGE = { "England — North": [0, 22], "England — South & East": [-6, 22], "London": [10, -26] };
  var SHORT = function(n){ return n.replace("England — ", ""); };

  // Header in the KORE pattern, built from the page's own intro paragraph and
  // stamp so the live page markup does not need editing.
  (function head(){
    var panel = document.getElementById("jmPanel");
    if (!panel || panel.querySelector(".jm-head")) return;
    if (!document.querySelector("link[data-jm-font]")){
      var lk = document.createElement("link");
      lk.rel = "stylesheet"; lk.setAttribute("data-jm-font","1");
      lk.href = "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;1,500&display=swap";
      document.head.appendChild(lk);
    }
    var intro = panel.querySelector(".body p");
    var h = document.createElement("div");
    h.className = "jm-head";
    h.innerHTML = '<p class="jm-kick">Live sales jobs map</p>'
      + '<h3>Roles across <em>the UK and Ireland</em></h3>'
      + '<p class="jm-lede"></p><div class="jm-stamp"><i></i><span class="jm-st"></span></div>';
    h.querySelector(".jm-lede").textContent = intro ? intro.textContent : "";
    var stamp = document.getElementById("jmStamp");
    if (stamp) h.querySelector(".jm-st").appendChild(stamp);
    var jm = panel.querySelector(".jm");
    panel.insertBefore(h, jm);
  })();

  function toggleRegion(r){
    if (!state.filters.region) state.filters.region = new Set();
    if (state.filters.region.has(r)) state.filters.region.delete(r);
    else state.filters.region.add(r);
    state.limit = 25; render();
  }

  function buildMap(){
    var geo = window.__UK_MAP__;
    if (!geo) return;
    var pool = matching("region"), counts = {};
    pool.forEach(function(j){ counts[j.region] = (counts[j.region]||0)+1; });
    var names = Object.keys(geo.paths);
    var max = Math.max.apply(null, names.map(function(n){ return counts[n]||0; }).concat([1]));
    var sel = state.filters.region;

    var svgEl = document.getElementById("jmMap");
    svgEl.setAttribute("viewBox", geo.viewBox);
    var vb = geo.viewBox.split(" ");
    var svg = '<defs>'
      + '<pattern id="jmDots" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="3.5" cy="3.5" r="1" fill="rgba(207,166,84,.34)"/></pattern>'
      + '<linearGradient id="jmLand" x1="0" y1="0" x2=".4" y2="1"><stop offset="0" stop-color="#132a4a"/><stop offset="1" stop-color="#0a1830"/></linearGradient>'
      + '<radialGradient id="jmPinG" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="#FFF4D6"/><stop offset=".45" stop-color="#EECB6F"/><stop offset="1" stop-color="#B58B41"/></radialGradient>'
      + '<filter id="jmGl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
      + '<radialGradient id="jmHalo" cx="66%" cy="78%" r="55%"><stop offset="0" stop-color="rgba(207,166,84,.22)"/><stop offset="1" stop-color="rgba(207,166,84,0)"/></radialGradient>'
      + '</defs>';
    names.forEach(function(name){
      var isSel = sel && sel.has(name);
      svg += '<path class="jm-region'+(isSel?" sel":"")+'" d="'+geo.paths[name]+'" fill="url(#jmLand)" data-r="'+esc(name)+'"><title>'+esc(name)+': '+(counts[name]||0)+' vacancies</title></path>';
    });
    names.forEach(function(name){
      svg += '<path d="'+geo.paths[name]+'" fill="url(#jmDots)" style="pointer-events:none"/>';
    });
    names.forEach(function(name){
      var isSel = sel && sel.has(name);
      svg += '<path class="jm-coast'+(isSel?" sel":"")+'" d="'+geo.paths[name]+'" filter="url(#jmGl)"/>';
    });
    names.forEach(function(name){
      var n = counts[name]||0;
      if (!n) return;
      var c = geo.centroids[name], d = NUDGE[name] || [0,0];
      var x = c[0]+d[0], y = c[1]+d[1];
      var r = 10 + 8*Math.sqrt(n/max);
      var on = sel && sel.has(name);
      svg += '<g class="jm-pin'+(on?" on":"")+'" data-r="'+esc(name)+'" tabindex="0" role="button" aria-label="'+esc(name)+': '+n+' vacancies">'
        + '<circle class="ring" cx="'+x+'" cy="'+y+'" r="'+r+'"/><circle class="ring r2" cx="'+x+'" cy="'+y+'" r="'+r+'"/>'
        + '<circle class="core" cx="'+x+'" cy="'+y+'" r="'+r+'" fill="url(#jmPinG)"/>'
        + '<text x="'+x+'" y="'+y+'"'+(n>99?' style="font-size:10px"':'')+'>'+n+'</text></g>';
    });
    svgEl.innerHTML = svg;

    if (!svgEl.parentNode.querySelector(".jm-leg")){
      var leg = document.createElement("p");
      leg.className = "jm-leg";
      leg.innerHTML = '<span><i></i>Live vacancies by region</span>';
      svgEl.parentNode.appendChild(leg);
    }

    svgEl.querySelectorAll(".jm-region,.jm-pin").forEach(function(p){
      p.addEventListener("click", function(){ toggleRegion(p.dataset.r); });
      if (p.classList.contains("jm-pin")) p.addEventListener("keydown", function(v){
        if (v.key === "Enter" || v.key === " "){ v.preventDefault(); toggleRegion(p.dataset.r); }
      });
    });

    buildKey(counts, names);
  }

  // Region cards beside the map, KORE style: name, role count, gold badge.
  function buildKey(counts, names){
    var host = document.getElementById("jmKey");
    if (!host) return;
    var sel = state.filters.region;
    var list = names.slice().sort(function(a,b){ return (counts[b]||0)-(counts[a]||0) || a.localeCompare(b); });
    var html = '<h4>Choose a region</h4><ul class="jm-cards">';
    list.forEach(function(name){
      var n = counts[name]||0, on = sel && sel.has(name);
      html += '<li><button type="button" class="jm-rb'+(n?"":" zero")+'" data-r="'+esc(name)+'" aria-pressed="'+(on?"true":"false")+'">'
        + '<span class="nm">'+esc(SHORT(name))+'</span><span class="sb">'+n+' role'+(n===1?"":"s")+'</span><span class="bd">'+n+'</span></button></li>';
    });
    var nat = counts[NATIONAL] || 0;
    if (nat){
      var onN = sel && sel.has(NATIONAL);
      html += '<li style="grid-column:1/-1"><button type="button" class="jm-rb nat" data-r="'+esc(NATIONAL)+'" aria-pressed="'+(onN?"true":"false")+'">'
        + '<span class="nm">UK-wide and field-based</span><span class="sb">No fixed territory, so not on the map</span><span class="bd">'+nat+'</span></button></li>';
    }
    html += '</ul>';
    host.innerHTML = html;
    host.querySelectorAll(".jm-rb").forEach(function(b){
      b.addEventListener("click", function(){ toggleRegion(b.dataset.r); });
    });
  }

  function buildList(){
    var jobs = visible().slice().sort(function(a,b){
      return (Date.parse(b.posted_date)||0) - (Date.parse(a.posted_date)||0);
    });
    var host = document.getElementById("jmList");

    document.getElementById("jmShown").textContent = jobs.length;
    document.getElementById("jmShownLbl").textContent = jobs.length === 1 ? "vacancy" : "vacancies";

    var hintEl = document.getElementById("jmHint");

    if (hintEl){
      // Opening state lists every role (Lou, 28/10/2026: "I want all roles showing").
      var labels = activeFilterLabels();
      hintEl.textContent = !anyFilterActive()
        ? "Showing all roles · click a region or use the filters to narrow"
        : labels.length === 1
          ? "Showing: " + labels[0]
          : "Showing " + labels.length + " filters · use Clear all to reset";
    }

    if (!jobs.length){
      host.innerHTML = '<div class="jm-empty"><b>No vacancies match these filters</b>'
        + 'Nothing currently advertised fits every filter chosen. Try clearing one — territory and speciality together are the usual culprits.</div>';
      return;
    }

    var slice = jobs.slice(0, state.limit), html = "";
    slice.forEach(function(j){
      var sal = fmtSalary(j), d = daysAgo(j.posted_date);
      html += '<a class="jm-row" href="'+esc(j.url)+'" target="_blank" rel="noopener noreferrer">'
        + '<div><div class="jm-title">'+esc(j.title)+'</div><div class="jm-meta">'
        + '<span class="jm-tag">'+esc(placeLabel(j))+'</span>'
        + '<span class="jm-tag lvl">'+esc(j.level)+'</span>'
        + (sal ? '<span class="jm-tag sal">'+sal+'</span>' : "")
        + (j.clinical_experience_required ? '<span class="jm-tag clin">Clinical background</span>' : "")
        + (j.speciality ? '<span class="jm-tag">'+esc(j.speciality)+'</span>' : "")
        + '<span>'+esc(advertiser(j))+(d!==null&&d<=7?" · new this week":"")+'</span>'
        + '</div></div><span class="jm-go">›</span></a>';
    });
    if (jobs.length > state.limit){
      html += '<div class="jm-more"><button id="jmMore" type="button">Show more ('+(jobs.length-state.limit)+' remaining)</button></div>';
    }
    host.innerHTML = html;
    var more = document.getElementById("jmMore");
    if (more) more.addEventListener("click", function(){ state.limit += 25; buildList(); });
  }

  function render(){ buildFilters(); buildMap(); buildList(); }

  document.getElementById("jmClear").addEventListener("click", function(){
    state.filters = {}; state.limit = 25; render();
  });

  function boot(data){
    state.jobs = (data.jobs||[]).map(derive);
    var when = data.generated_at ? new Date(data.generated_at) : null;
    document.getElementById("jmStamp").textContent =
      state.jobs.length + " live · " + (when ? when.toLocaleDateString("en-GB",{day:"2-digit",month:"short"}) : "—");
    render();
  }

  if (window.__JOBS_DATA__){
    boot(window.__JOBS_DATA__);
  } else {
    fetch(JOBS_SRC, {cache:"no-store"})
      .then(function(r){ if(!r.ok) throw new Error("HTTP "+r.status); return r.json(); })
      .then(boot)
      .catch(function(e){
        document.getElementById("jmList").innerHTML =
          '<div class="jm-empty"><b>Vacancies are temporarily unavailable</b>The live jobs feed could not be loaded. Please try again shortly.</div>';
        document.getElementById("jmStamp").textContent = "feed unavailable";
        console.error("jobs-map feed error:", e);
      });
  }
})();
