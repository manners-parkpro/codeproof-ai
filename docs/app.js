/* CodeProof AI 대시보드 — 기록된 리뷰 · 브라우저 Ruff · 이 컴퓨터의 리뷰 (`uv run codeproof serve`).
 *
 * 데이터는 생성물이다 (data/reviews.js · data/ruff.js — `uv run codeproof report`).
 * 모델이 쓴 문장과 코드는 전부 textContent 로 넣는다 — HTML 로 해석하지 않는다.
 * Ruff(WebAssembly)는 「분석」을 누를 때만 받고, 받은 파일은 SRI 해시로 검증한다.
 * 붙임 코드(vendor/)는 npm 의 같은 판에서 가져왔다 — 바깥 스크립트를 실행하지 않는다.
 */
(function () {
  "use strict";

  var RUFF_GLUE = "./vendor/ruff-wasm-web-0.16.8/ruff_wasm.js";
  var RUFF_WASM = "https://cdn.jsdelivr.net/npm/@astral-sh/ruff-wasm-web@0.16.8/ruff_wasm_bg.wasm";
  var RUFF_SRI = "sha384-dKPj/bI0rt0iEb/aCeqvSNf9M6AFqPC32sLBK7M/HeRSX5OD78u4M3wZQOjAZbPJ";

  // 짝 판정은 결함 쪽 지적과 증명 범위 안의 헛경고만으로 정한다 - 범위 밖 지적은 판정에 들지 않는다
  var VERDICTS = {
    "P-C": ["구별 성공 — 결함을 짚고 헛경고 없음", "ok"],
    "P-V": ["결함도 짚었지만 헛경고도 냄", "warn"],
    "P-B": ["결함을 놓침", "none"],
    "P-R": ["거꾸로 — 헛경고를 내고 결함은 놓침", "bad"],
  };
  var MARKS = {
    tp: ["결함 자리를 짚음", "tp"],
    fp: ["헛경고 — 안전하다고 증명한 범위를 짚음", "fp"],
    style: ["관례 주장 — 결함 주장이 아니라 채점하지 않음", ""],
  };
  var SIDE_NAMES = { safe: "안전한 코드", buggy: "버그 코드" };

  function $(id) { return document.getElementById(id); }

  function el(tag, props) {
    var node = document.createElement(tag);
    var children = Array.prototype.slice.call(arguments, 2);
    if (props) {
      Object.keys(props).forEach(function (k) {
        if (k === "text") node.textContent = props[k];
        else if (k === "cls") node.className = props[k];
        else node.setAttribute(k, props[k]);
      });
    }
    children.forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function span(lines) { return lines[0] === lines[1] ? "L" + lines[0] : "L" + lines[0] + "–" + lines[1]; }

  // 채점하지 않은 결함 주장 - 정답 구간에서 몇 줄 떨어졌는지 보인다 (선언한 규칙은 겹친 지적만 센다)
  function outside(f, side, src) {
    var ref = side === "safe" ? src.covered : src.defect;
    var gap = f[1] < ref[0] ? ref[0] - f[1] : f[0] - ref[1];
    return side === "safe"
      ? "증명 범위(" + span(ref) + ")에서 " + gap + "줄 떨어짐 — 범위 밖이라 채점하지 않음"
      : "결함 자리(" + span(ref) + ")에서 " + gap + "줄 떨어짐 — 선언한 규칙은 겹친 지적만 센다";
  }

  // ── 탭 ──────────────────────────────────────────────────────────────────
  function selectTab(which) {
    ["records", "code"].forEach(function (name) {
      var on = name === which;
      var tab = $("tab-" + name);
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
      $("panel-" + name).hidden = !on;
    });
  }

  function setupTabs() {
    var tabs = [$("tab-records"), $("tab-code")];
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { selectTab(tab.id.slice(4)); });
      tab.addEventListener("keydown", function (e) {
        var to = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
        if (to === undefined) return;
        e.preventDefault();
        var next = tabs[(to + tabs.length) % tabs.length];
        selectTab(next.id.slice(4));
        next.focus();
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-open]"), function (link) {
      link.addEventListener("click", function () { selectTab(link.getAttribute("data-open")); });
    });
  }

  // ── 기록된 리뷰 ─────────────────────────────────────────────────────────
  var R = window.CODEPROOF_REVIEWS;
  var state = { pair: 0, side: "buggy", run: 0 };
  var order = [];

  function correct(pair, who) {
    return pair.reviews[who].filter(function (r) { return r.verdict === "P-C"; }).length;
  }

  function pairLabel(pair) {
    var kind = R.kinds[pair.kind] || pair.kind;
    var counts = R.reviewers.map(function (rv, i) {
      return rv.name.split(" ")[0] + " " + correct(pair, i) + "/" + pair.reviews[i].length;
    });
    return pair.id.split("-")[0] + " · " + kind + " — 구별 " + counts.join(" · ");
  }

  function buildPairs() {
    var a = R.reviewers[0].name, b = R.reviewers[1].name;
    var groups = [
      { label: a + " 가 더 자주 구별한 짝", test: function (p) { return correct(p, 0) > correct(p, 1); }, items: [] },
      { label: b + " 가 더 자주 구별한 짝", test: function (p) { return correct(p, 0) < correct(p, 1); }, items: [] },
      { label: "같은 횟수로 구별한 짝", test: function () { return true; }, items: [] },
    ];
    R.pairs.forEach(function (p, i) {
      for (var g = 0; g < groups.length; g++) {
        if (groups[g].test(p)) { groups[g].items.push(i); break; }
      }
    });
    var select = $("pair");
    clear(select);
    order = [];
    groups.forEach(function (g) {
      if (!g.items.length) return;
      var og = el("optgroup", { label: g.label + " (" + g.items.length + ")" });
      g.items.forEach(function (i) {
        og.appendChild(el("option", { value: String(i), text: pairLabel(R.pairs[i]) }));
        order.push(i);
      });
      select.appendChild(og);
    });
    select.addEventListener("change", function () { state.pair = Number(select.value); renderPair(); });
    $("prev").addEventListener("click", function () { step(-1); });
    $("next").addEventListener("click", function () { step(1); });
    $("side-safe").addEventListener("click", function () { state.side = "safe"; renderPair(); });
    $("side-buggy").addEventListener("click", function () { state.side = "buggy"; renderPair(); });
    var runs = Math.max.apply(null, R.reviewers.map(function (rv) { return rv.runs; }));
    var seg = $("runs");
    for (var r = 0; r < runs; r++) {
      (function (r) {
        var b = el("button", { type: "button", "aria-pressed": "false", text: (r + 1) + "회차" });
        b.addEventListener("click", function () { state.run = r; renderPair(); });
        seg.appendChild(b);
      })(r);
    }
    var featured = (R.featured || []).map(function (id) {
      return R.pairs.findIndex(function (p) { return p.id === id; });
    }).filter(function (i) { return i >= 0; });
    // 예시 바로가기 - 점수판의 규칙이 고른 짝 (손으로 고르지 않는다)
    if (featured.length) {
      var picks = el("div", { cls: "seg", role: "group", "aria-label": "예시 짝" });
      featured.forEach(function (i) {
        var pair = R.pairs[i];
        var won = correct(pair, 0) > correct(pair, 1) ? 0 : 1;
        var b = el("button", { type: "button", text: "예시 " + pair.id.split("-")[0] + " · " + R.reviewers[won].name.split(" ")[0] + " 만 구별" });
        b.addEventListener("click", function () { state.pair = i; renderPair(); });
        picks.appendChild(b);
      });
      $("examples").appendChild(picks);
    }
    state.pair = featured.length ? featured[0] : order[0];
  }

  function step(delta) {
    var at = order.indexOf(state.pair);
    state.pair = order[(at + delta + order.length) % order.length];
    renderPair();
  }

  function renderStory(pair) {
    var story = $("story");
    clear(story);
    story.appendChild(el("dt", { text: "함정" }));
    story.appendChild(el("dd", { text: (R.kinds[pair.kind] || pair.kind) + " (" + pair.id + ")" }));
    story.appendChild(el("dt", { text: "안전한 이유" }));
    story.appendChild(el("dd", { text: pair.claim }));
    story.appendChild(el("dt", { text: "버그 코드" }));
    story.appendChild(el("dd", { text: pair.bug.trim() }));
  }

  function within(lines, n) { return lines && n >= lines[0] && n <= lines[1]; }

  function renderCode(pair) {
    var view = $("code-view");
    clear(view);
    var src = pair[state.side];
    var marks = {};
    pair.reviews.forEach(function (runs, who) {
      var run = runs[state.run];
      if (!run) return;
      run[state.side].forEach(function (f) {
        for (var n = f[0]; n <= f[1]; n++) {
          marks[n] = marks[n] || {};
          marks[n][who] = true;
        }
      });
    });
    src.code.replace(/\n$/, "").split("\n").forEach(function (line, i) {
      var n = i + 1;
      // 색으로만 가르지 않는다 - 화면 낭독기에는 줄의 뜻을 글로 준다
      var cls = "ln", what = "";
      if (state.side === "safe") {
        if (within(src.guard, n)) { cls += " guard"; what = "안전장치"; }
        else if (within(src.covered, n)) { cls += " cover"; what = "덮는 범위"; }
      } else if (within(src.defect, n)) {
        cls += " defect"; what = "결함";
      }
      var dots = el("span", { cls: "marks" });
      [0, 1].forEach(function (who) {
        var name = R.reviewers[who].name + " 지적";
        if (marks[n] && marks[n][who]) dots.appendChild(el("i", { cls: "dot " + (who ? "b" : "a"), role: "img", "aria-label": name, title: name }));
      });
      view.appendChild(el("div", { cls: cls },
        el("span", { cls: "no", text: String(n) }, what ? el("span", { cls: "sr", text: " " + what }) : null),
        dots, el("span", { text: line || " " })));
    });
    var legend = $("legend");
    clear(legend);
    var items = state.side === "safe"
      ? [["k-guard", "안전장치 (덮는 범위 안)"], ["k-cover", "안전 근거가 덮는 범위 — 여기를 결함이라 하면 헛경고"]]
      : [["k-defect", "안전장치를 지우거나 바꾼 자리 — 결함"]];
    items.push(["k-a", R.reviewers[0].name + " 지적"], ["k-b", R.reviewers[1].name + " 지적"]);
    items.forEach(function (it) { legend.appendChild(el("span", null, el("i", { cls: it[0] }), it[1])); });
  }

  function renderReviews(pair) {
    var box = $("reviews");
    clear(box);
    var other = state.side === "safe" ? "buggy" : "safe";
    pair.reviews.forEach(function (runs, who) {
      var rv = R.reviewers[who];
      var run = runs[state.run];
      var card = el("article", { cls: "review" });
      var badge = run ? VERDICTS[run.verdict] : ["이 회차 없음", "none"];
      card.appendChild(el("header", null,
        el("span", { cls: "swatch", style: "background: var(--" + (who ? "b" : "a") + ")" }),
        el("span", { cls: "name", text: rv.name }),
        el("span", { cls: "model", text: rv.model }),
        el("span", { cls: "badge " + badge[1], text: badge[0] })));
      if (run) {
        var shown = run[state.side];
        if (!shown.length) card.appendChild(el("p", { cls: "quiet", text: SIDE_NAMES[state.side] + "에는 지적이 없었다." }));
        shown.forEach(function (f) {
          var mark = f[3] === "out" ? [outside(f, state.side, pair[state.side]), ""] : MARKS[f[3]];
          card.appendChild(el("p", { cls: "finding" },
            el("span", { cls: "meta " + mark[1], text: span(f) + " · " + mark[0] }),
            f[4]));
        });
        var rest = run[other];
        var alarms = rest.filter(function (f) { return f[3] === "fp"; }).length;
        var hits = rest.filter(function (f) { return f[3] === "tp"; }).length;
        var tail = other === "safe" ? (alarms ? " · 헛경고 " + alarms + "건" : "") : (hits ? " · 결함 자리 " + hits + "건" : "");
        card.appendChild(el("p", { cls: "quiet", text: SIDE_NAMES[other] + "에는 지적 " + rest.length + "건" + tail }));
      }
      box.appendChild(card);
    });
    var summary = R.reviewers.map(function (rv, who) {
      return rv.name + " " + correct(pair, who) + "/" + pair.reviews[who].length;
    });
    box.appendChild(el("p", { cls: "runs", text: "구별 성공 횟수 — " + summary.join(" · ") +
      ". 짝마다 같은 코드를 여러 번 리뷰했고, 점수는 한 번 리뷰했을 때의 기대값이다." }));
  }

  function renderPair() {
    var pair = R.pairs[state.pair];
    $("pair").value = String(state.pair);
    $("side-safe").setAttribute("aria-pressed", state.side === "safe" ? "true" : "false");
    $("side-buggy").setAttribute("aria-pressed", state.side === "buggy" ? "true" : "false");
    Array.prototype.forEach.call($("runs").children, function (b, i) {
      b.setAttribute("aria-pressed", i === state.run ? "true" : "false");
    });
    renderStory(pair);
    renderCode(pair);
    renderReviews(pair);
  }

  function setupRecords() {
    if (!R || !R.pairs || !R.pairs.length) {
      Array.prototype.forEach.call($("panel-records").querySelectorAll(".controls, .story, .pane"), function (n) { n.hidden = true; });
      $("panel-records").appendChild(el("p", { cls: "quiet", text: "기록 데이터를 읽지 못했다 (data/reviews.js)." }));
      return;
    }
    buildPairs();
    renderPair();
  }

  // ── 내 코드 — 브라우저 Ruff ──────────────────────────────────────────────
  var RULES = window.CODEPROOF_RUFF;
  var ruff = null;

  function example() {
    if (!R || !R.pairs.length) return "";
    var id = (R.featured || [])[0];
    var pair = R.pairs.find(function (p) { return p.id === id; }) || R.pairs[0];
    return pair.buggy.code;
  }

  function loadRuff() {
    if (!ruff) {
      ruff = import(RUFF_GLUE).then(function (glue) {
        var wasm = fetch(RUFF_WASM, { integrity: RUFF_SRI, mode: "cors", credentials: "omit" });
        return glue.default({ module_or_path: wasm }).then(function () { return glue; });
      });
      ruff.catch(function () { ruff = null; });
    }
    return ruff;
  }

  function runRuff(glue, code) {
    // 일반 객체로 넘긴다 - defaultSettings() 는 Map 을 돌려주어 속성으로 넣은 값이 무시된다 [실측]
    var ws = new glue.Workspace({ "target-version": RULES.target, lint: { select: ["ALL"] } }, glue.PositionEncoding.Utf16);
    try { return ws.check(code); } finally { ws.free(); }
  }

  function renderRuff(glue, diags, code) {
    var box = $("ruff-result");
    clear(box);
    var convention = new Set(RULES.convention);
    var counts = { defect: 0, style: 0, syntax: 0 };
    var rows = diags.slice().sort(function (x, y) {
      return x.start_location.row - y.start_location.row || x.start_location.column - y.start_location.column;
    }).map(function (d) {
      // 구문 오류는 룰이 아니다 - Ruff 는 null 이 아니라 이 코드로 준다 [실측]
      var kind = d.code === RULES.syntax ? "syntax" : convention.has(d.code) ? "style" : "defect";
      counts[kind]++;
      var tag = kind === "syntax" ? "구문 오류 — 파이썬으로 읽지 못함" : kind === "style" ? "관례(형식) 주장" : "결함 주장";
      return el("p", { cls: "finding" },
        el("span", { cls: "meta" + (kind === "defect" ? " fp" : ""), text: "L" + d.start_location.row + " · " + d.code + " · " + tag }),
        d.message);
    });
    var version = glue.Workspace.version();
    box.appendChild(el("h3", { text: "Ruff " + version + " · 전체 규칙 (ALL) · 대상 " + RULES.target }));
    if (version !== RULES.version) {
      box.appendChild(el("p", { cls: "quiet", text: "⚠ 측정에 쓴 Ruff 는 " + RULES.version + " 이다 — 판이 달라 분류가 어긋날 수 있다." }));
    }
    box.appendChild(el("p", { cls: "sum", text: diags.length
      ? "지적 " + diags.length + "건 — 결함 주장 " + counts.defect + " · 관례(형식) 주장 " + counts.style + (counts.syntax ? " · 구문 오류 " + counts.syntax : "")
      : "지적 없음" }));
    if (counts.syntax) {
      box.appendChild(el("p", { cls: "callout", text: "구문 오류가 있다 — 이 화면은 파이썬 코드만 분석한다. 자바 같은 다른 언어나 잘린 코드 조각은 읽지 못한다." }));
    }
    rows.forEach(function (r) { box.appendChild(r); });
    // 예시 코드면 같은 코드에 두 AI 가 낸 결과를 나란히 - 린터와 AI 가 보는 것의 차이가 이 화면의 요점이다
    var pair = R && R.pairs.find(function (p) { return p.buggy.code === code; });
    if (pair) {
      box.appendChild(el("p", { cls: "callout", text: "이 코드는 " + pair.id + " 의 버그 코드다 — " + pair.bug.trim() + " 같은 코드를 " +
        R.reviewers.map(function (rv, who) {
          var hit = pair.reviews[who].filter(function (r) { return r.verdict === "P-C" || r.verdict === "P-V"; }).length;
          return rv.name + " 는 " + pair.reviews[who].length + "번 중 " + hit + "번";
        }).join(", ") + " 결함 자리를 짚었다." }));
    }
    box.appendChild(el("p", { cls: "hint", text: "린터가 결함 주장을 내지 않아도 결함이 없다는 뜻은 아니다 — 안전장치가 빠진 논리 결함은 대부분 린터 규칙 밖이다." +
      " 파일 경로가 필요한 규칙(INP001 등)은 브라우저에서 돌지 않는다." }));
  }

  function showRuffError(what, err) {
    var box = $("ruff-result");
    clear(box);
    box.appendChild(el("h3", { text: "Ruff 를 돌리지 못했다" }));
    box.appendChild(el("p", { cls: "quiet", text: what }));
    box.appendChild(el("p", { cls: "hint", text: "원문: " + String(err && err.message ? err.message : err) }));
  }

  function setupRuff() {
    var source = $("source");
    source.value = example();
    $("reset-source").addEventListener("click", function () { source.value = example(); });
    var button = $("run-ruff");
    if (location.protocol === "file:") {
      button.disabled = true;
      $("ruff-note").textContent = "받은 파일로 열면 브라우저가 WebAssembly 를 받지 못한다 — 웹 주소나 uv run codeproof serve 로 연다.";
      return;
    }
    if (!RULES) {
      button.disabled = true;
      $("ruff-note").textContent = "규칙 분류 데이터를 읽지 못했다 (data/ruff.js).";
      return;
    }
    button.addEventListener("click", function () {
      var code = source.value;
      button.disabled = true;
      var label = button.textContent;
      button.textContent = ruff ? "분석 중…" : "Ruff 를 받는 중…";
      loadRuff().then(function (glue) {
        try {
          renderRuff(glue, runRuff(glue, code), code);
        } catch (err) {
          showRuffError("Ruff 가 이 코드를 분석하다 멈췄다 — 다른 코드로 다시 해 본다.", err);
        }
      }, function (err) {
        showRuffError("Ruff(WebAssembly)를 받지 못했다 — 네트워크에서 jsDelivr 에 닿지 못했거나, 받은 파일의 해시가 " +
          "고정한 값과 달라 브라우저가 실행을 막았다. 브라우저 콘솔에 자세한 이유가 남는다.", err);
      }).then(function () {
        button.disabled = false;
        button.textContent = label;
      });
    });
  }

  // ── 이 컴퓨터의 리뷰 — `uv run codeproof serve` 로 열었을 때만 ──────────────
  function setupLocal() {
    var local = location.protocol === "http:" && (location.hostname === "127.0.0.1" || location.hostname === "localhost");
    if (!local) return;
    fetch("/api/info", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (info) {
      if (!info) return;
      var box = $("local-box");
      clear(box);
      box.appendChild(el("h3", { text: "이 컴퓨터에서 리뷰 — 지적마다 근거를 붙인다" }));
      box.appendChild(el("p", { text: "Ruff · mypy 는 늘 돈다. 아래를 고르면 같은 코드를 모델도 리뷰한다 — 측정과 같은 실행기 · 같은 설정이다." }));
      var agent = el("input", { type: "checkbox", id: "use-agent" });
      var model = el("input", { type: "text", id: "ollama-model", placeholder: "예: qwen3:4b", size: "14" });
      var useOllama = el("input", { type: "checkbox", id: "use-ollama" });
      box.appendChild(el("p", null, agent, " ", el("label", { "for": "use-agent", text: "Claude Code 도 리뷰 — 코드를 Anthropic 으로 보낸다 (구독 로그인 · 분 단위)" })));
      box.appendChild(el("p", null, useOllama, " ", el("label", { "for": "use-ollama", text: "로컬 Ollama 모델도 리뷰 — 이 컴퓨터 안에서 돈다" }), " ", model));
      var go = el("button", { type: "button", cls: "btn primary", text: "이 컴퓨터에서 리뷰" });
      var out = el("div", { cls: "result", "aria-live": "polite" });
      box.appendChild(el("div", { cls: "row" }, go));
      box.appendChild(out);
      go.addEventListener("click", function () {
        var started = Date.now();
        go.disabled = true;
        clear(out);
        var wait = el("p", { cls: "quiet", text: "리뷰 중…" });
        out.appendChild(wait);
        var timer = setInterval(function () { wait.textContent = "리뷰 중… " + Math.round((Date.now() - started) / 1000) + "초"; }, 1000);
        fetch("/api/review", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            code: $("source").value,
            agent: agent.checked ? info.agents[0] : null,
            ollama: useOllama.checked && model.value.trim() ? model.value.trim() : null,
          }),
        }).then(function (r) { return r.json().then(function (body) { return [r.ok, body]; }); })
          .then(function (res) { renderLocal(out, res[0], res[1]); })
          .catch(function (err) { clear(out); out.appendChild(el("p", { cls: "quiet", text: String(err) })); })
          .then(function () { clearInterval(timer); go.disabled = false; });
      });
    }).catch(function () { /* 정적 웹 판 - 서버가 없다 */ });
  }

  function renderLocal(out, ok, body) {
    clear(out);
    if (!ok) {
      out.appendChild(el("h3", { text: "리뷰를 내지 못했다" }));
      out.appendChild(el("p", { cls: "quiet", text: body.error || "알 수 없는 오류" }));
      return;
    }
    var rep = body.report;
    out.appendChild(el("h3", { text: "지적 " + rep.entries.length + "건 · " + rep.reviewers.join(" · ") }));
    out.appendChild(el("p", { cls: "hint" }, "도구 설정 — ", el("code", { text: rep.settings.join(" · ") }),
      ". 브라우저 Ruff 는 전체 규칙(ALL)이라 지적 수가 다를 수 있다."));
    if (!rep.entries.length) {
      out.appendChild(el("p", { cls: "quiet", text: "리뷰어가 짚은 것이 없다 — 결함이 없다는 뜻은 아니다." }));
    }
    out.appendChild(el("p", { cls: "hint", text: "결함을 확인하는 보고서가 아니다 — 근거를 못 찾은 것은 지적이 틀렸다는 뜻이 아니고, 「모인 근거」는 확률이 아니다." }));
    if (rep.rejected.length) {
      out.appendChild(el("p", { cls: "quiet", text: "⚠ 파서가 버린 모델 지적 " + rep.rejected.length + "건 — 아래 목록에 없다." }));
    }
    rep.entries.forEach(function (e) {
      var item = el("div", { cls: "finding" },
        el("span", { cls: "meta", text: "L" + e.line + " · " + e.reviewer + (e.rule ? " " + e.rule : "") + (e.defect_claim ? "" : " · 관례 주장") + " · 모인 근거 " + e.confidence.toFixed(2) }),
        e.message);
      var list = el("ul", { cls: "hint" });
      e.evidence.forEach(function (ev) { list.appendChild(el("li", { text: ev.kind + ": " + ev.verdict + " — " + ev.detail })); });
      item.appendChild(list);
      out.appendChild(item);
    });
    var limits = el("details", null, el("summary", { text: "검증자가 보지 못하는 것" }));
    var ul = el("ul", { cls: "hint" });
    rep.limits.forEach(function (l) { ul.appendChild(el("li", { text: l })); });
    limits.appendChild(ul);
    out.appendChild(limits);
  }

  function start() {
    setupTabs();
    setupRecords();
    setupRuff();
    setupLocal();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
