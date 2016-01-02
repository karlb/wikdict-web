$(function() {
    // search provider
    if (window.external && ("AddSearchProvider" in window.external)) {
        $('#add-search-provider-block').show();
        $('#add-search-provider').click(function () {
            window.external.AddSearchProvider('http://www.wikdict.com/opensearch/' + from_lang + '-' + to_lang);
        });
    }

    // language selection
    $('.lang-select').change(function () {
        window.location = '/' + this.value + '/';
    })

    // typeahead
    var substringMatcher = function() {
        var loaded_prefix;
        var loaded_langs;
        var merged_and_sorted;

        function match(q) {
            return $.grep(merged_and_sorted, function(x) {
                return x[0].toLowerCase().startsWith(q.toLowerCase());
            });
        }

        function load_lang(lang, prefix, q, cb_async) {
            //$.ajax('http://127.0.0.1:8080/' + lang + '/' + encodeURI(encodeURI(prefix.toLowerCase())) + '.json', {
            $.ajax('http://storage.googleapis.com/wikdict-cdn/typeahead2/' + lang + '/' + encodeURI(encodeURI(prefix.toLowerCase())) + '.json', {
                success: function (data) {
                    loaded_langs[lang] = data;
                    if (loaded_langs[from_lang] && loaded_langs[to_lang]) {
                        // add language info
                        $.each(loaded_langs[from_lang], function(i, x) {
                            x.push(from_lang);
                        });
                        $.each(loaded_langs[to_lang], function(i, x) {
                            x.push(to_lang);
                        });
                        // merge and sort
                        merged_and_sorted = loaded_langs[from_lang].concat(loaded_langs[to_lang]);
                        merged_and_sorted.sort(function (a, b) {return b[1] - a[1]});

                        cb_async(match(q));
                        loaded_prefix = prefix;
                    }
                }
            });
        }

        return function findMatches(q, cb, cb_async) {
            var prefix = q.slice(0, 3);
            if (loaded_prefix !== prefix) {
                merged_and_sorted = [];
                loaded_prefix = undefined;
                loaded_langs = {};
                load_lang(from_lang, prefix, q, cb_async);
                load_lang(to_lang, prefix, q, cb_async);
            }

            cb(match(q));
        };
    };

    $('.typeahead').typeahead({
            hint: true,
            highlight: true,
            minLength: 3
        },
        {
            source: substringMatcher(),
            limit: 5,
            display: function (x) {
                return x[0];
            },
            templates: {
                suggestion: function (x) {
                      return '<div class="suggestion clearfix"><span class="word">' + x[0]
                                + '</span><span class="language text-muted">' + x[2] + '</span></div>';
                }
            }
        });
    // hide suggestions until user types
    setTimeout(function () {$('.typeahead').typeahead('close')}, 0);
    // submit form when selecting a suggestion
    $('.typeahead').bind('typeahead:select', function(ev, suggestion) {
        $('.search-form').submit();
    });
})
