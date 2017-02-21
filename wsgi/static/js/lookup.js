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
            var prefix = q.slice(0, 3);
            if (loaded_prefix !== prefix) {
                loaded_data = undefined;
                loaded_prefix = undefined;
                $.ajax('/typeahead/' + from_lang + '-' + to_lang + '/' + encodeURI(encodeURI(prefix.toLowerCase())), {
                    success: function (data) {
                        loaded_data = data;
                        cb_async(match(q));
                        loaded_prefix = prefix;
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
})
