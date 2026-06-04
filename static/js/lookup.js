$(function() {
    // The active pair is read from the search form's hidden index_name input —
    // the exact value the form submits — so the typeahead can never query a
    // different dictionary than the search itself will use. Loaded suggestions
    // are keyed on the pair, so changing the language pair invalidates the cache.
    function currentPair() {
        var v = $('input[name="index_name"]').val() || (from_lang + '-' + to_lang);
        return v.split('-').sort().join('-');  // canonical order (from < to)
    }

    // Escape text coming from the dictionary data before inserting it as HTML.
    function esc(s) {
        return $('<div>').text(s == null ? '' : s).html();
    }
    function flagFor(lang) {
        return (window.lang_flags || {})[lang] || '';
    }

    // Header band for a language section, mirroring the result-page cards:
    // "<flag> <source>" on the left, "<target> <flag>" on the right.
    function headBand(lang) {
        var pair = currentPair().split('-');
        var other = pair[0] === lang ? pair[1] : pair[0];
        return '<div class="ta-head"><span>' + flagFor(lang) + ' ' + lang + '</span>'
            + '<span>' + other + ' ' + flagFor(other) + '</span></div>';
    }

    // Highlight the matched substring (first occurrence, case-insensitive).
    function highlight(text, q) {
        text = text == null ? '' : String(text);
        var i = q ? text.toLowerCase().indexOf(q.toLowerCase()) : -1;
        if (i < 0) return esc(text);
        return esc(text.slice(0, i))
            + '<strong class="ta-hl">' + esc(text.slice(i, i + q.length)) + '</strong>'
            + esc(text.slice(i + q.length));
    }

    // Group matches by source language (one section per language that has hits),
    // capped per section, in canonical pair order. The first row of each section
    // is tagged with `_head` so a header band is drawn before it.
    var PER_GROUP = 5;
    function groupByLang(rows) {
        var byLang = {};
        rows.forEach(function (x) {
            x._head = null;
            (byLang[x[2]] = byLang[x[2]] || []).push(x);
        });
        var out = [];
        currentPair().split('-').forEach(function (lang) {
            var g = (byLang[lang] || []).slice(0, PER_GROUP);
            if (g.length) {
                g[0]._head = lang;
                out = out.concat(g);
            }
        });
        return out;
    }

    /* ---------- typeahead ----------

       A small self-contained autocomplete. It fetches the matches for the first
       MIN_LEN characters once per prefix+pair, caches them, then filters and
       groups that data on the client as the user keeps typing. */
    var MIN_LEN = 3;
    var input = $('.typeahead');
    if (input.length) {
        var group = input.closest('.input-group');
        var menu = $('<div class="ta-menu" id="ta-menu" role="listbox"></div>')
            .appendTo(group).hide();
        input.attr({
            role: 'combobox', 'aria-autocomplete': 'list',
            'aria-controls': 'ta-menu', 'aria-expanded': 'false'
        });

        var loadedKey, loadedData;   // cache: "<pair>:<prefix>" -> rows
        var rows = [];               // selectable rows currently shown
        var active = -1;

        function visible() { return menu.is(':visible'); }

        function close() {
            menu.hide().empty();
            group.removeClass('ta-open');
            input.attr('aria-expanded', 'false').removeAttr('aria-activedescendant');
            rows = [];
            active = -1;
        }

        // Relevance of a row for query q: the backend's popularity score
        // (max_score * coalesce(rel_importance, 0.01)) weighted by a length
        // factor in (0, 1] that favours shorter words. So "fun" outranks the
        // longer "function" unless the latter is far more popular.
        function rank(x, q) {
            var base = (x[3] || 0) * (x[4] != null ? x[4] : 0.01);
            return base * (q.length / x[0].length);
        }

        function matches(q) {
            if (loadedData === undefined) return [];
            var ql = q.toLowerCase();
            var hits = $.grep(loadedData, function (x) {
                return x[0].toLowerCase().startsWith(ql);
            });
            hits.sort(function (a, b) {
                var ax = a[0].toLowerCase() === ql, bx = b[0].toLowerCase() === ql;
                if (ax !== bx) return ax ? -1 : 1;   // exact match pinned first
                return rank(b, q) - rank(a, q);      // then length-weighted score
            });
            return hits;
        }

        function render(q) {
            rows = groupByLang(matches(q));
            if (!rows.length) { close(); return; }
            var html = '';
            rows.forEach(function (row, i) {
                if (row._head) html += headBand(row._head);
                html += '<div class="ta-item" role="option" id="ta-opt-' + i + '" data-i="' + i + '">'
                    + '<div class="ta-row"><span class="ta-word">' + highlight(row[0], q) + '</span>'
                    + '<span class="ta-trans">' + highlight(row[1], q) + '</span></div></div>';
            });
            html += '<div class="ta-foot">↵ see all matches for <b>' + esc(q) + '</b></div>';
            menu.html(html).show();
            group.addClass('ta-open');
            input.attr('aria-expanded', 'true');
            setActive(-1);
        }

        function load(q) {
            var prefix = q.slice(0, MIN_LEN);
            var key = currentPair() + ':' + prefix;
            if (loadedKey !== key) {
                loadedKey = key;
                loadedData = undefined;
                $.ajax('/typeahead/' + currentPair() + '/' + encodeURI(prefix.toLowerCase()), {
                    success: function (data) {
                        if (loadedKey !== key) return;  // pair/prefix changed in flight
                        loadedData = data;
                        if (input.val().length >= MIN_LEN) render(input.val());
                    }
                });
            }
            render(q);
        }

        function setActive(i) {
            var opts = menu.find('.ta-item');
            opts.removeClass('is-active');
            active = i;
            if (i >= 0 && opts[i]) {
                opts.eq(i).addClass('is-active');
                input.attr('aria-activedescendant', 'ta-opt-' + i);
                opts[i].scrollIntoView({ block: 'nearest' });
            } else {
                input.removeAttr('aria-activedescendant');
            }
        }

        function select(i) {
            if (rows[i]) input.val(rows[i][0]);
            $('.search-form').submit();
        }

        input.on('input', function () {
            var q = input.val();
            if (q.length < MIN_LEN) { close(); return; }
            load(q);
        });

        input.on('keydown', function (e) {
            if (e.key === 'ArrowDown') {
                if (!visible()) {
                    if (input.val().length >= MIN_LEN) load(input.val());
                } else {
                    setActive(active + 1 >= rows.length ? 0 : active + 1);
                }
                e.preventDefault();
            } else if (e.key === 'ArrowUp') {
                if (visible()) {
                    setActive(active <= 0 ? rows.length - 1 : active - 1);
                    e.preventDefault();
                }
            } else if (e.key === 'Enter') {
                // With a row highlighted, open it; otherwise let the form submit
                // the typed query (the "see all matches" path).
                if (visible() && active >= 0) { select(active); e.preventDefault(); }
            } else if (e.key === 'Escape') {
                if (visible()) { close(); e.preventDefault(); }
            }
        });

        menu.on('mouseenter', '.ta-item', function () {
            setActive($(this).data('i'));
        }).on('mousedown', '.ta-item', function (e) {
            e.preventDefault();   // keep input focus so the submit fires cleanly
            select($(this).data('i'));
        });

        input.on('blur', function () { window.setTimeout(close, 120); });

        input.focus();
        setTimeout(function () { input.select(); }, 50);

        // When the active pair changes (e.g. via the home-page picker, which fires
        // a change event on index_name) the cached suggestions are for the old
        // dictionary, so drop them and re-query the typed word against the new pair.
        $('input[name="index_name"]').on('change', function () {
            loadedKey = undefined;
            loadedData = undefined;
            var q = input.val();
            if (input.is(':focus') && q.length >= MIN_LEN) load(q);
            else close();
        });
    }
})
