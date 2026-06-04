// Home-page language-pair picker.
//
// The active pair is always selected; tapping a third tile drops the older of
// the two. Selecting a valid pair updates the hero pills, navbar and the search
// form's target in place — navigation to /from-to/ only happens when the user
// actually searches.

// Leading ";" guards against the preceding bundled file lacking a trailing
// semicolon (the files are concatenated into one packed.js).
;(function () {
  "use strict";

  var dataEl = document.getElementById("wd-picker-data");
  var tape = document.getElementById("wd-tape");
  if (!dataEl || !tape) return; // not the home page

  var data = JSON.parse(dataEl.textContent);
  var LANGUAGES = data.languages; // weight order
  var PAIRS = data.pairs; // "a-b" (a<b) -> translation count
  var byCode = {};
  LANGUAGES.forEach(function (l) {
    byCode[l.code] = l;
  });

  function pairKey(a, b) {
    return a < b ? a + "-" + b : b + "-" + a;
  }
  function pairExists(a, b) {
    return a !== b && PAIRS[pairKey(a, b)] !== undefined;
  }
  function pairCount(a, b) {
    return PAIRS[pairKey(a, b)] || 0;
  }
  function fmtCount(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (n >= 1e3) return Math.round(n / 1e3) + "k";
    return String(n);
  }
  function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
  }

  // selected: codes in FIFO order (oldest first). Starts as the current pair.
  var selected = data.current.slice();

  function commit(next, popCode) {
    selected = next;
    if (next.length === 2 && pairExists(next[0], next[1])) {
      updateCommittedPair(next[0], next[1]);
    }
    render(popCode);
  }

  function handleTile(code) {
    var idx = selected.indexOf(code);
    if (idx !== -1) {
      commit(selected.filter(function (c) {
        return c !== code;
      }));
      return;
    }
    if (selected.length === 0) {
      commit([code], code);
      return;
    }
    if (selected.length === 1) {
      if (pairExists(selected[0], code)) commit([selected[0], code], code);
      return;
    }
    var oldest = selected[0];
    var newest = selected[1];
    if (pairExists(newest, code)) commit([newest, code], code);
    else if (pairExists(oldest, code)) commit([oldest, code], code);
  }

  function tileState(code) {
    if (selected.indexOf(code) !== -1) return "confirmed";
    var anchor = selected.length > 0 ? selected[selected.length - 1] : null;
    if (anchor === null) return "default";
    if (pairExists(anchor, code)) return "available";
    if (selected.length === 2 && pairExists(selected[0], code)) return "available-alt";
    return "unavailable";
  }

  // --- In-place "committed pair" updates (no reload) -------------------------

  function updateCommittedPair(a, b) {
    // navbar pair text
    var spans = document.querySelectorAll(".navbar-lang");
    if (spans.length >= 2) {
      spans[0].textContent = capitalize(byCode[a].name);
      spans[1].textContent = capitalize(byCode[b].name);
    }
    // Search form target: the single source of truth for the active pair. Both
    // the /lookup redirect (on submit) and the typeahead (in lookup.js) read it,
    // so they can never disagree about which dictionary is in use. The change
    // event lets the typeahead drop suggestions rendered for the old pair.
    var indexName = document.querySelector('input[name="index_name"]');
    if (indexName) {
      indexName.value = a + "-" + b;
      indexName.dispatchEvent(new Event("change", { bubbles: true }));
    }
    // Keep the address bar in sync so reload/bookmark/share reflect the active
    // pair, without a navigation. Canonical order (a<b) matches the URL the
    // server would redirect to, so a later reload won't bounce.
    history.replaceState(null, "", "/" + pairKey(a, b) + "/");
  }

  // --- Rendering -------------------------------------------------------------

  var CHECK_SVG =
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5L20 7"/></svg>';

  function render(popCode) {
    renderTape(popCode);
    renderPills();
  }

  function renderTape(popCode) {
    var html = "";
    LANGUAGES.forEach(function (l) {
      var state = tileState(l.code);
      var count = null;
      if (state === "available") count = pairCount(selected[selected.length - 1], l.code);
      else if (state === "available-alt") count = pairCount(selected[0], l.code);

      var meta = "";
      if (count !== null) {
        meta = '<span class="wd-tile-count">' + fmtCount(count) + "</span>";
      } else if (state === "default") {
        meta = '<span class="wd-tile-pairs">' + l.partners + " pairs</span>";
      }
      var check =
        state === "confirmed"
          ? '<span class="wd-tile-check" aria-hidden="true">' + CHECK_SVG + "</span>"
          : "";

      html +=
        '<button type="button" class="wd-tile wd-tile-' + state +
        (l.code === popCode ? " wd-tile-pop" : "") + '"' +
        ' data-code="' + l.code + '"' +
        (state === "unavailable" ? " disabled" : "") +
        ' aria-pressed="' + (state === "confirmed") + '">' +
        '<span class="wd-tile-flag">' + l.flag + "</span>" +
        '<span class="wd-tile-name">' + l.name + "</span>" +
        meta +
        check +
        "</button>";
    });
    tape.innerHTML = html;
  }

  function pillHtml(code, role) {
    if (!code) {
      return '<span class="wd-pair-pill wd-pair-pill-empty">Pick a language</span>';
    }
    var l = byCode[code];
    return (
      '<span class="wd-pair-pill wd-pair-pill-' + role + '">' +
      '<span class="wd-pair-pill-flag">' + l.flag + "</span>" +
      '<span class="wd-pair-pill-name">' + l.name + "</span>" +
      '<button type="button" class="wd-pair-pill-x" data-lang="' + code +
      '" aria-label="Remove ' + l.name + '">×</button>' +
      "</span>"
    );
  }

  function renderPills() {
    var pills = document.getElementById("wd-pair-pills");
    if (!pills) return;
    pills.innerHTML =
      '<span class="wd-pair-pills-label">Translating</span>' +
      pillHtml(selected[0], "older") +
      '<span class="wd-pair-pills-arrow">↔</span>' +
      pillHtml(selected[1], "newer");
  }

  // --- Events (delegated) ----------------------------------------------------

  tape.addEventListener("click", function (e) {
    var btn = e.target.closest(".wd-tile");
    if (btn && !btn.disabled) handleTile(btn.dataset.code);
  });

  var pillsEl = document.getElementById("wd-pair-pills");
  if (pillsEl) {
    pillsEl.addEventListener("click", function (e) {
      var x = e.target.closest(".wd-pair-pill-x");
      if (x) handleTile(x.dataset.lang);
    });
  }

  render();

  // On arrival the page may render at "/" (last-used pair from the session)
  // while the URL doesn't name the pair. Sync it once so reload/bookmark/share
  // reflect what's shown — idempotent when already at /from-to/.
  if (selected.length === 2 && pairExists(selected[0], selected[1])) {
    history.replaceState(null, "", "/" + pairKey(selected[0], selected[1]) + "/");
  }
})();
