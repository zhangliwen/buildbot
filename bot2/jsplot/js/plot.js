
var JSON_DIR_URL;
var JSON_DIR_LIST;
if (window.location.toString().indexOf('file:///') == -1) {
    JSON_DIR_URL = "bench_results/";
    JSON_DIR_LIST = JSON_DIR_URL;
} else {
    JSON_DIR_URL  = "test/data/";
    JSON_DIR_LIST = JSON_DIR_URL + "dir";
}

function common_attrs()
{
    return {
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
            'autoscaleMargin': 0.1,
        },
        'legend' : {
            'position': 'nw',
        }
    }
}

function get_plot_input(benchresults, cpython_results)
{
    return [{
        label: 'pypy-c-jit',
        data : benchresults,
    },
    {
        label: 'cpython 2.6.2',
        data : cpython_results
    }];
}

function attrs_for_miniature()
{
    var attrs = common_attrs();
    attrs.xaxis.ticks = 0;
    attrs.yaxis.ticks = 0;
    return attrs;
}

var MAX_PER_LINE = 4;

function plot_miniature(benchname, benchresults, cpython_results, lasttime)
{
    if ($("#placeholder").find("td").length % MAX_PER_LINE == 0) {
        $("#placeholder").append("<tr></tr>");
    }
    var capt = benchname + " " + lasttime;
    $("#placeholder").find("tr:last").append("<td><p class='smallcaption'>" + capt + "</p><div class='miniplot'></div></td>");
    var elem = $("#placeholder").find("div:last");
    var attrs = attrs_for_miniature();
    var data;
    if (!$("#legend").children() == []) {
        // a bit of a hack, if we didn't add a legend, do it now
        $("#revstart")[0].value = benchresults[0][0];
        $("#revstart").change(function(event) {
            redisplay(elem, benchresults, cpython_results);
        });
        data = get_plot_input(benchresults, cpython_results);
        attrs.legend.container = "#legend";
    } else {
        data = [benchresults, cpython_results];
    }
    $.plot(elem, data, attrs);
}

function redisplay(elem, benchresults, cpython_results)
{
    var attrs = attrs_for_miniature();
    attrs.xaxis.min = $("#revstart")[0].value;
    $.plot(elem, [benchresults, cpython_results], attrs);
}

function plot_main(benchname, benchresults, cpython_results, lasttime) {
    var capt = benchname + " " + lasttime;
    $("#placeholder").append("<p class='caption'>" + capt + "</p>");
    $("#placeholder").append("<div class='plot'></div>");
    var plotinput = get_plot_input(benchresults, cpython_results)
    $.plot($("#placeholder").children(":last"), plotinput, common_attrs());
}
