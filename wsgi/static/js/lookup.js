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
    var substringMatcher = function(strs) {
        var loaded_prefix;

        function matches(q) {
            return $.grep(strs, function(x) {
                return x[0].toLowerCase().startsWith(q.toLowerCase());
            });
        }

        return function findMatches(q, cb, cb_async) {
            var prefix = q.slice(0, 3);
            if (loaded_prefix != prefix) {
                strs = [];
                $.ajax('http://127.0.0.1:8080/' + from_lang + '/' + encodeURI(encodeURI(prefix.toLowerCase())) + '.json', {
                //$.ajax('http://storage.googleapis.com/wikdict-cdn/typeahead/{{from_lang}}/' + encodeURI(encodeURI(prefix.toLowerCase())) + '.txt', {
                    success: function (data) {
                        strs = data;
                        var m = matches(q);
                        cb_async(m);
                        loaded_prefix = prefix;
                    }
                });
            }

            cb(matches(q));
        };
    };

    $('.typeahead').typeahead({
            hint: true,
            highlight: true,
            minLength: 3
        },
        {
            source: substringMatcher([]),
            limit: 5,
            display: function (x) {
                return x[0];
            },
            templates: {
                suggestion: function (x) {
                      return '<div>' + x[0] + ' &mdash; de</div>';
                }
            }
        });
    // hide suggestions until user types
    setTimeout(function () {$('.typeahead').typeahead('close')}, 0);
})
