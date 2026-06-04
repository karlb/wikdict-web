$(function() {
    // language selection
    $('.lang-select').change(function () {
        window.location = '/' + this.value + '/';
    })

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

    // Group matches by source language (one section per language that has hits),
    // capped per section, in canonical pair order. The first row of each section
    // is tagged with `_head` so the suggestion template can draw its header band.
    var PER_GROUP = 5;
    function groupByLang(rows) {
        var byLang = {};
        rows.forEach(function (x) {
            x._head = null;  // clear any tag from a previous grouping
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

    // typeahead
    var substringMatcher = function() {
        var loaded_key;   // "<pair>:<prefix>"
        var loaded_data;

        function match(q) {
            if (loaded_data === undefined) {
                return;
            }
            var hits = $.grep(loaded_data, function(x) {
                return x[0].toLowerCase().startsWith(q.toLowerCase());
            });
            return groupByLang(hits);
        }

        return function findMatches(q, cb, cb_async) {
            var pair = currentPair();
            var prefix = q.slice(0, 3);
            var key = pair + ':' + prefix;
            if (loaded_key !== key) {
                loaded_data = undefined;
                loaded_key = key;
                $.ajax('/typeahead/' + pair + '/' + encodeURI(encodeURI(prefix.toLowerCase())), {
                    success: function (data) {
                        if (loaded_key !== key) {
                            return;  // pair or prefix changed while in flight
                        }
                        loaded_data = data;
                        cb_async(match(q));
                    }
                });
            }

            cb(match(q));
        };
    };

    input = $('.typeahead').typeahead({
            hint: true,
            highlight: true,
            minLength: 3
        },
        {
            source: substringMatcher(),
            limit: 12,
            display: function (x) {
                return x[0]
            },
            templates: {
                suggestion: function (x) {
                    return (x._head ? headBand(x._head) : '')
                        + '<div class="ta-row"><span class="ta-word">' + esc(x[0]) + '</span>'
                        + '<span class="ta-trans">' + esc(x[1]) + '</span></div>';
                },
                footer: function (ctx) {
                    return '<div class="ta-foot">↵ see all matches for <b>'
                        + esc(ctx.query) + '</b></div>';
                }
            }
        })
    input.focus();
    setTimeout(function () { input.select(); }, 50);
    // hide suggestions until user types
    setTimeout(function () {$('.typeahead').typeahead('close')}, 0);
    // submit form when selecting a suggestion
    $('.typeahead').bind('typeahead:select', function(ev, suggestion) {
        $('.search-form').submit();
    });

    // Weld the popover to the input: square the field's bottom corners while
    // suggestions are showing (render fires only with content, so an empty
    // result never leaves the corners squared with nothing below).
    $('.typeahead').on('typeahead:render', function () {
        $(this).closest('.input-group').addClass('ta-open');
    }).on('typeahead:close', function () {
        $(this).closest('.input-group').removeClass('ta-open');
    });

    // When the active pair changes (e.g. via the home-page picker, which fires a
    // change event on index_name), discard the suggestions rendered for the old
    // dictionary so they can't reappear when the input is refocused. Any typed
    // word is kept and re-queried against the new pair.
    $('input[name="index_name"]').on('change', function () {
        var el = input.get(0);
        var word = input.typeahead('val');
        input.typeahead('val', '');
        if (el && word) {
            el.value = word;
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    });
})
