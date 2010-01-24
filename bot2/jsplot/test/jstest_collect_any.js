
OpenEnd.require("/js/collect.js")
OpenEnd.require("/js/jquery.min.js")
OpenEnd.require("/js/underscore-min.js")

var expected_benchnames = ['ai', "django", "html5lib", "richards", "rietveld",
                           "slowspitfire", "spambayes"]

Tests = {
    test_extract_benchmark_data: function() {
        var revnos = [70634, 70632];
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
        aisDeeply(benchnames, expected_benchnames);
        var benchnames = _.keys(bench_data.cpytimes);
        benchnames.sort();
        aisDeeply(benchnames, expected_benchnames);
        ais(bench_data.cpytimes.ai, 0.43372206687940001);
        ais(bench_data.lasttimes.ai, "1.0207x faster");
    },

    test_extract_revnos: function() {
        var dirdoc;
        $.ajax({
            url: "/test/data/dir.html",
            contentType: "text/xml",
            dataType: "html",
            success: function (result) {
                dirdoc = $(result);
            },
            async: false,
        });
        var revnos = extract_revnos(dirdoc);
        aisDeeply(revnos, [70632, 70634, 70641, 70643]);
    },

    test_collect_data: function() {
        var checkdata;
        var benchnames = [];
        function check(benchname, benchresults, cpyresults) {
            benchnames.push(benchname);
            if (benchname == "html5lib") {
                checkdata = [benchresults, cpyresults];
            }
        }
        collect_data(check, "/test/data/dir.html", "/test/data/", false);
        aisDeeply(benchnames, expected_benchnames);
        aisDeeply(checkdata, [[[70632, 18.3431589603], [70634, 18.2035400867],
                               [70641, 19.623087883], [70643, 18.1294131279]],
                              [[70632, 11.7123618126],
                               [70643, 11.7123618126]]]);
    },

    test_collect_latest_data: function() {
        var checkdata;
        function check(data) {
            checkdata = data;
        };
        collect_latest_data(check, "/test/data/dir.html", "/test/data/", false);
        ais(checkdata.results[0][0], 0.4273978233336)
        ais(checkdata.results[1][0], 0.43415923118599997);
        ais(checkdata.benchnames[0], 'ai');
    },
}
