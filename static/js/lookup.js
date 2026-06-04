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

    // typeahead
    var substringMatcher = function() {
        var loaded_key;   // "<pair>:<prefix>"
        var loaded_data;

        function match(q) {
            if (loaded_data === undefined) {
                return;
            }
            return $.grep(loaded_data, function(x) {
                return x[0].toLowerCase().startsWith(q.toLowerCase());
            });
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
            limit: 5,
            display: function (x) {
                return x[0]
            },
            templates: {
                suggestion: function (x) {
                      return '<div class="suggestion clearfix"><span class="word">' + x[0]
                                + ' <span class="text-muted">(' + x[2] + ')</span></span>'
                                + '<span class="simple-trans">' + x[1] + '</span></div>';
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
