
var JSON_DIR_URL;
var JSON_DIR_LIST;
if (window.location.toString().indexOf('file:///') == -1) {
    JSON_DIR_URL = "bench_results/";
    JSON_DIR_LIST = JSON_DIR_URL;
} else {
    JSON_DIR_URL  = "test/data/";
    JSON_DIR_LIST = JSON_DIR_URL + "dir";
}

var large_displayed = false;
var large_data;

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
    $("#placeholder").find("tr:last").append("<td><p class='smallcaption'>" + capt + "</p><a href='#down' id='goto_" + benchname + "'><div class='miniplot'></div></a></td>");
    $("#goto_" + benchname).click(function(e) {
        display_large(benchname, benchresults, cpython_results, lasttime);
    });
    var elem = $("#placeholder").find("div:last");
    var attrs = attrs_for_miniature();
    var data;
    $("#revstart")[0].value = benchresults[0][0];
    $("#revstart").change(function(event) {
        redisplay(elem, benchresults, cpython_results);
    });
    data = get_plot_input(benchresults, cpython_results);
    attrs.legend.container = "#legend";
    $.plot(elem, data, attrs);
}

function display_large(benchname, benchresults, cpython_results, lasttime)
{
    $("#large_caption").html(benchname + " " + lasttime);
    var attrs = common_attrs();
    attrs.xaxis.min = $("#revstart")[0].value;
    $.plot($("#large_graph"), get_plot_input(benchresults, cpython_results),
          attrs);
    large_displayed = true;
    large_data = [benchname, benchresults, cpython_results, lasttime];
}

function redisplay(elem, benchresults, cpython_results)
{
    var attrs = attrs_for_miniature();
    attrs.xaxis.min = $("#revstart")[0].value;
    $.plot(elem, [benchresults, cpython_results], attrs);
    if (large_displayed) {
        display_large(large_data[0], large_data[1], large_data[2], large_data[3]);
    }
}

function plot_main(benchname, benchresults, cpython_results, lasttime) {
    var capt = benchname + " " + lasttime;
    $("#placeholder").append("<p class='caption'>" + capt + "</p>");
    $("#placeholder").append("<div class='plot'></div>");
    var plotinput = get_plot_input(benchresults, cpython_results)
    $.plot($("#placeholder").children(":last"), plotinput, common_attrs());
}
