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

/*
Modified based on the example from
http://codereview.stackexchange.com/questions/37632/how-should-i-sort-an-html-table-with-javascript-in-a-more-efficient-manner
*/
function sortTable(tableId, col, asc) {
    var tbody = document.getElementById(tableId);
    var rows = tbody.rows;
    var rlen = rows.length;
    var arr = new Array();
    var i, j, cells, clen;

    // fill the array with values from the table
    for(i = 1; i < rlen; i++) {
        cells = rows[i].cells;
        clen = cells.length;
        arr[i - 1] = new Array();
        for(j = 0; j < clen; j++) { 
            arr[i - 1][j] = cells[j].innerHTML;
        }
    }
    console.log(arr)

    // sort the array by the specified column number (col) and order (asc)
    arr.sort(function(a, b) {
        var retval = 0;
        var fA = parseFloat(a[col]);
        var fB = parseFloat(b[col]);
        if(a[col] != b[col]) {
            if((fA == a[col]) && (fB == b[col])) {
                retval = (fA > fB) ? asc : -1 * asc; //numerical
            } else {
                retval=(a[col] > b[col]) ? asc : -1 * asc;
            }
        }
        return retval;
    });
    for(var rowidx = 1; rowidx < rlen; rowidx++) {
        for(var colidx = 0; colidx < arr[rowidx - 1].length; colidx++) { 
            tbody.rows[rowidx].cells[colidx].innerHTML = arr[rowidx - 1][colidx]; 
        }
    }
}
