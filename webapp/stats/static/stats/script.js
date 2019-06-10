function show_matches(elem) {
    var span = $(elem);
    var matches_div = span.siblings('.matches-list');
    matches_div.show();
}

function hide_matches(elem) {
    var span = $(elem);
    var matches_div = span.siblings('.matches-list');
    matches_div.hide();
}

/*
Modified based on the example from
http://html5.litten.com/graphing-data-in-the-html5-canvas-element-part-iv-simple-pie-charts/
*/
function getTotal(myData){
    var myTotal = 0;
    for (var j = 0; j < myData.length; j++) {
      myTotal += (typeof myData[j] == 'number') ? myData[j] : 0;
    }
    return myTotal;
}

function plotData(myData, elemId) {
    var canvas;
    var ctx;
    var lastend = 0;
    var myTotal = getTotal(myData);
    var myColor = ["#87F717", "#FF4500", "#4682B4"];

    canvas = document.getElementById(elemId);
    var middle_x = canvas.width / 2;
    var middle_y = canvas.height / 2;

    ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (var i = 0; i < myData.length; i++) {
      ctx.fillStyle = myColor[i];
      ctx.beginPath();
      ctx.moveTo(middle_x, middle_y);
      ctx.arc(middle_x, middle_y, middle_y, lastend, lastend + Math.PI * 2 * (myData[i] / myTotal), false);
      ctx.lineTo(middle_x, middle_y);
      ctx.fill();
      lastend += Math.PI * 2 * (myData[i] / myTotal);
    }
}

function sortTable(tableId, col, asc) {
    var trId = "#" + tableId + " tr";
    var tableCells = new Array();

    // fill the array with values from the table
    $(trId).each(function(rowId, row) {
        if (rowId > 0) {
            tableCells[rowId - 1] = new Array();
            $(this).children('td').each(function(cellId, cell) {
                tableCells[rowId - 1][cellId] = this.outerHTML;
            });
        }
    });

    console.log(tableCells);
    // sort the array by the specified column number (col) and order (asc)
    tableCells.sort(function(a, b) {
        var retval = 0;
        var valA = $(a[col]).attr("title");
        var valB = $(b[col]).attr("title");

        if (typeof valA == "undefined" || typeof valB == "undefined") {
            valA = $(a[col]).text();
            valB = $(b[col]).text();
        }
        
        var fA = parseFloat(valA);
        var fB = parseFloat(valB);
        if (valA != valB) {
            if ((fA == valA) && (fB == valB)) {
                retval = (fA > fB) ? asc : -1 * asc; //numerical
            } else {
                retval = (valA > valB) ? asc : -1 * asc;
            }
        }
        return retval;
    });
    
    $(trId).each(function(rowId, row) {
        if (rowId > 0) {
            $(this).children('td').each(function(cellId, cell) {
                this.outerHTML = tableCells[rowId - 1][cellId];
            });
        }
    });
    
}

function request_stats(event, a) {
    event.preventDefault();

    let link = $(a);
    $.ajax({
        url: link.attr("href"),
        success: function (data, text_status, jqxhr) {
            link.hide();
            process_stat_reply(data);
        },
        error: function (jqxhr, status, type) {
            process_stat_error(jqxhr);
        }
    });
}

function process_stat_reply(data) {
    let div = $("div.stat-status");
    div.text(data.msg + " " + data.eta);
}

function process_stat_error(jqxhr) {
    let div = $("div.stat-status");
    div.text(jqxhr.responseText);
    div.addClass("stat-error");
}






































































