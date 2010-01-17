
var JSON_DIR_URL;
var JSON_DIR_LIST;
if (window.location.toString().indexOf('file:///') == -1) {
    JSON_DIR_URL = "bench_results/";
    JSON_DIR_LIST = JSON_DIR_URL;
} else {
    JSON_DIR_URL  = "test/data/";
    JSON_DIR_LIST = JSON_DIR_URL + "dir";
}

function plot_main(benchname, benchresults, cpython_results) {
    $("#placeholder").append("<p class='caption'>" + benchname + "</p>");
    $("#placeholder").append("<div class='plot'></div>");
    var plotinput = [{
        label: 'pypy-c-jit',
        data : benchresults,
    },
    {
        label: 'cpython',
        data : cpython_results
    }];
    $.plot($("#placeholder").children(":last"), plotinput, {
        'series': {
            'points': {'show': true},
            'lines' : {'show': true},
        },
        'xaxis': {
            'min': 70630,
            'tickDecimals': 0,
        },
        'yaxis': {
            'min': 0,
        },
        'legend' : {
            'position' : 'sw'
        }
    });
}

