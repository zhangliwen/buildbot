
OpenEnd.require("/js/plot.js")
OpenEnd.require("/js/jquery.min.js")
OpenEnd.require("/js/underscore-min.js")

Tests = {
test_load_data: function() {
    var revnos = [70632, 70634];
    var loaded_data = [];
    for (var i in revnos) {
        $.ajax({
            url: '/test/data/' + revnos[i] + '.json',
            dataType: 'json',
            success: function(result) {
                loaded_data.push(result);
            },
            async: false
        });
    }
    var bench_data = extract_benchmark_data(loaded_data);
    aisDeeply(bench_data.results.ai, [[70632, 0.43707809448220003],
                                      [70634, 0.42492904663079994]]);
    var benchnames = _.keys(bench_data.results);
    benchnames.sort();
    var expected_keys = ['ai', "django", "html5lib", "richards", "rietveld",
                         "slowspitfire", "spambayes"]
    aisDeeply(benchnames, expected_keys);
    var benchnames = _.keys(bench_data.cpytimes);
    benchnames.sort();
    aisDeeply(benchnames, expected_keys);
    ais(bench_data.cpytimes.ai, 0.43372206687940001);
},

test_extract_revnos: function() {
    var dirdoc;
    $.ajax({
        url: "/test/data/dir",
        contentType: "text/xml",
        dataType: "html",
        success: function (result) {
            dirdoc = $(result);
        },
        async: false,
    });
    var revnos = extract_revnos(dirdoc);
    aisDeeply(revnos, [70632, 70634, 70641, 70643]);
}
}
