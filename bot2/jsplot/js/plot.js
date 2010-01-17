
var JSON_DIR_URL;
var JSON_DIR_LIST;
if (window.location.toString().indexOf('file:///') == -1) {
    JSON_DIR_URL = "bench_results/";
    JSON_DIR_LIST = JSON_DIR_URL;
} else {
    JSON_DIR_URL  = "test/data/";
    JSON_DIR_LIST = JSON_DIR_URL + "dir";
}

function Collector(revnos)
{
    this.plotdata = [];
    this.counter = revnos.length;

    this.finish_collecting = function() {
        this.plotdata = extract_benchmark_data(this.plotdata);
        var benchnames = _.keys(this.plotdata.results);
        benchnames.sort()
        for (var i = 0; i < benchnames.length; ++i) {
            var benchname = benchnames[i];
            var benchresults = this.plotdata.results[benchname];
            var cpystart = benchresults[0][0];
            var cpyend = benchresults[benchresults.length - 1][0];
            var cpyval = this.plotdata.cpytimes[benchname];
            var cpython_results = [[cpystart, cpyval], [cpyend, cpyval]]
            $("#placeholder").append("<p>" + benchname + "</p>");
            $("#placeholder").append("<div class='plot'></div>");
            $.plot($("#placeholder").children(":last"), [benchresults, cpython_results], {
                'series': {
                    'points': {'show': true},
                    'lines' : {'show': true},
                },
                'xaxis': {
                    'min': 70630,
                    'max': revnos[revnos.length - 1],
                    'tickDecimals': 0,
                },
                'yaxis': {
                    'min': 0,
                }
            });
        }
    }

    this.collect = function(next) {
        this.plotdata.push(next);
        this.counter--;
        if (this.counter == 0) {
            this.finish_collecting()
        }
    }
}

$(document).ready(function() {
    $.ajax({
        url: JSON_DIR_LIST,
        dataType: 'html',
        success: function(htmlstr) {
            var revnos = extract_revnos($(htmlstr));
            collector = new Collector(revnos);
            for (var i in revnos) {
                $.getJSON(JSON_DIR_URL + revnos[i] + '.json', function(data) {
                    collector.collect(data)
                });
            }
        },
        error: function (a, b, c) {
            console.log(a, b, c);
        },
    });
});

function extract_benchmark_data(data)
{
    var retval = {};
    var cpytimes = {};
    var lastrev = 0;
    var lastrevindex = 0;
    for (var i = 0; i < data.length; i++) {
        var revno = data[i]["revision"];
        if (revno > lastrev) {
            lastrev = revno;
            lastrevindex = i;
        }
        var results = data[i]["results"];
        for (var j = 0; j < results.length; j++) {
            var result = results[j];
            var name = result[0];
            var dataelem = result[2];
            var avg;
            if (dataelem["avg_changed"]) {
                avg = dataelem["avg_changed"];
            } else {
                avg = dataelem["changed_time"];
            }
            if (retval[name]) {
                retval[name].push([revno, avg]);
            } else {
                retval[name] = [[revno, avg]];
            }
        }
    }
    for (var name in retval) {
        retval[name].sort(function (a, b) {
            if (a[0] > b[0]) {
                return 1;
            } else {
                return -1;
            }
        });
    }
    var cpyelem = data[lastrevindex]
    for (var i = 0; i < cpyelem.results.length; i++) {
        var dataelem = cpyelem.results[i][2];
        var benchname = cpyelem.results[i][0];
        if (dataelem.avg_base) {
            cpytimes[benchname] = dataelem.avg_base;
        } else {
            cpytimes[benchname] = dataelem.base_time;
        }
    }
    return {'results': retval, 'cpytimes': cpytimes};
}

function extract_revnos(xmldoc)
{
    var res = [];
    $(xmldoc).find("a").each(function (no, elem) {
        var s = elem.getAttribute("href");
        s = s.substr(0, s.length - ".json".length);
        res.push(s);
    });
    return res;
}