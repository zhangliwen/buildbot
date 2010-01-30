
var JSON_DIR_URL;
var JSON_DIR_LIST;
if (window.location.toString().indexOf('file:///') == -1) {
    JSON_DIR_URL = "bench_results/";
    JSON_DIR_LIST = JSON_DIR_URL;
} else {
    JSON_DIR_URL  = "test/data/";
    JSON_DIR_LIST = JSON_DIR_URL + "dir.html";
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

function colored_capt(benchname, lasttime) {
    return benchname + " " + lasttime.replace('slower', 
                                              '<font color="red">slower</font')
}

function plot_miniature(benchname, benchresults, cpython_results, lasttime)
{
    if ($("#placeholder").find("td").length % MAX_PER_LINE == 0) {
        $("#placeholder").append("<tr></tr>");
    }
    var capt = colored_capt(benchname, lasttime);
    $("#placeholder").find("tr:last").append("<td><p class='smallcaption'>" + capt + "</p><a href='#down' id='goto_" + benchname + "'><div class='miniplot'></div></a></td>");
    $("#goto_" + benchname).click(function(e) {
        display_large(benchname, benchresults, cpython_results, lasttime);
    });
    var elem = $("#placeholder").find("div:last");
    var attrs = attrs_for_miniature();
    var data;
    var oldval = $("#revstart")[0].value;
    if (!oldval || benchresults[0][0] < oldval) {
        // only update stuff when our starting revision is smaller, so we
        // get a minimum
        $("#revstart")[0].value = benchresults[0][0];
    }
    $("#revstart").change(function(event) {
        redisplay(elem, benchresults, cpython_results);
    });
    data = get_plot_input(benchresults, cpython_results);
    attrs.legend.container = "#legend";
    $.plot(elem, data, attrs);
}

function showTooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
        position: 'absolute',
        display: 'none',
        top: y + 5,
        left: x + 5,
        border: '1px solid #fdd',
        padding: '2px',
        'background-color': '#fee',
        opacity: 0.80
    }).appendTo("body").fadeIn(200);
}

function display_large(benchname, benchresults, cpython_results, lasttime)
{
    $("#large_caption").html(benchname + " " + lasttime);
    var attrs = common_attrs();
    attrs.xaxis.min = $("#revstart")[0].value;
    attrs.grid = {hoverable: true};
    $.plot($("#large_graph"), get_plot_input(benchresults, cpython_results),
          attrs);
    large_displayed = true;
    large_data = [benchname, benchresults, cpython_results, lasttime];

    var previousPoint = null;

    $("#large_graph").bind("plothover", function (event, pos, item) {
        if (item) {
            if (previousPoint != item.datapoint) {
                previousPoint = item.datapoint;
                    
                $("#tooltip").remove();
                var x = item.datapoint[0].toFixed(0),
                y = item.datapoint[1].toFixed(2);
                
                showTooltip(item.pageX, item.pageY,
                            item.series.label + " of " + x + " = " + y);
            }
        }
        else {
            $("#tooltip").remove();
            previousPoint = null;            
        }
    });
}

function redisplay(elem, benchresults, cpython_results)
{
    var attrs = attrs_for_miniature();
    attrs.xaxis.min = $("#revstart")[0].value;
    $.plot(elem, [benchresults, cpython_results], attrs);
    if (large_displayed) {
        display_large(large_data[0], large_data[1], large_data[2],
                      large_data[3], fals);
    }
}

function plot_main(benchname, benchresults, cpython_results, lasttime) {
    var capt = benchname + " " + lasttime;
    $("#placeholder").append("<p class='caption'>" + capt + "</p>");
    $("#placeholder").append("<div class='plot'></div>");
    var plotinput = get_plot_input(benchresults, cpython_results)
    $.plot($("#placeholder").children(":last"), plotinput, common_attrs());
}

function plot_one(plotdata) {
    function lg(v) {
        return Math.log(v) / Math.log(2);
    }

    var results = plotdata.results;
    var data = [];
    var min = 1, max = 1;
    for (var i = 0; i < results[0].length; ++i) {
        var next = lg(results[1][i] / results[0][i]);
        if (next < min) {
            min = Math.floor(next);
        }
        if (next > max) {
            max = Math.ceil(next);
        }
        data.push([i - .3, next]);
    }
    var yticks = [];
    for (var i = min; i < max; i++) {
        var v = Math.pow(2, i);
        if (v < 1) {
            yticks.push([i, 1/v + "x slower"]);
        } else if (v == 1) {
            yticks.push([i, "equal"]);
        } else {
            yticks.push([i, v + "x faster"]);
        }
    }
    var xticks = [];
    for (var i = 0; i < plotdata.benchnames.length; ++i) {
        xticks.push([i, plotdata.benchnames[i]]);
    }
    $.plot($("#placeholder"), [data],
           {
               series: {
                   bars: {
                       show: true,
                       barWidth: .6,
                       align: 'left',
                   },
                   hoverable: true,
               },
               yaxis: {
                   ticks: yticks,
               },
               xaxis: {
                   ticks: xticks,
               },
               grid: {
                   hoverable: true,
               }
           });
}
