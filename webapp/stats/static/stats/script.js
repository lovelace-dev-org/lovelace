function show_matches (elem) {
    const span = $(elem)
    const matches_div = span.siblings(".matches-list")
    matches_div.show()
}

function hide_matches (elem) {
    const span = $(elem)
    const matches_div = span.siblings(".matches-list")
    matches_div.hide()
}

/*
Modified based on the example from
http://html5.litten.com/graphing-data-in-the-html5-canvas-element-part-iv-simple-pie-charts/
*/
function getTotal (myData) {
    let myTotal = 0
    for (let j = 0; j < myData.length; j++) {
        myTotal += (typeof myData[j] === "number") ? myData[j] : 0
    }
    return myTotal
}

function plotData (myData, elemId) {
    let lastend = 0
    const myTotal = getTotal(myData)
    const myColor = ["#87F717", "#FF4500", "#4682B4"]

    const canvas = document.getElementById(elemId)
    const middle_x = canvas.width / 2
    const middle_y = canvas.height / 2

    const ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    for (let i = 0; i < myData.length; i++) {
        ctx.fillStyle = myColor[i]
        ctx.beginPath()
        ctx.moveTo(middle_x, middle_y)
        ctx.arc(
            middle_x, middle_y, middle_y, lastend,
            lastend + Math.PI * 2 * (myData[i] / myTotal), false
        )
        ctx.lineTo(middle_x, middle_y)
        ctx.fill()
        lastend += Math.PI * 2 * (myData[i] / myTotal)
    }
}

function sortTable (tableId, col, asc) {
    const trId = "#" + tableId + " tr"
    const tableCells = []

    // fill the array with values from the table
    $(trId).each(function (rowId, row) {
        if (rowId > 0) {
            tableCells[rowId - 1] = []
            $(this).children("td").each(function (cellId, cell) {
                tableCells[rowId - 1][cellId] = this.outerHTML
            })
        }
    })

    console.log(tableCells)
    // sort the array by the specified column number (col) and order (asc)
    tableCells.sort(function (a, b) {
        let retval = 0
        let valA = $(a[col]).attr("title")
        let valB = $(b[col]).attr("title")

        if (typeof valA === "undefined" || typeof valB === "undefined") {
            valA = $(a[col]).text()
            valB = $(b[col]).text()
        }

        const fA = parseFloat(valA)
        const fB = parseFloat(valB)
        if (valA !== valB) {
            if ((fA === valA) && (fB === valB)) {
                retval = (fA > fB) ? asc : -1 * asc // numerical
            } else {
                retval = (valA > valB) ? asc : -1 * asc
            }
        }
        return retval
    })

    $(trId).each(function (rowId, row) {
        if (rowId > 0) {
            $(this).children("td").each(function (cellId, cell) {
                this.outerHTML = tableCells[rowId - 1][cellId]
            })
        }
    })
}

function request_stats (event, a) {
    event.preventDefault()

    const link = $(a)
    $.ajax({
        url: link.attr("href"),
        success: function (data, text_status, jqxhr) {
            link.hide()
            process_stat_reply(data)
        },
        error: function (jqxhr, status, type) {
            process_stat_error(jqxhr)
        }
    })
}

function process_stat_reply (data) {
    const div = $("div.stat-status")
    div.text(data.msg + " " + data.eta)
}

function process_stat_error (jqxhr) {
    const div = $("div.stat-status")
    div.text(jqxhr.responseText)
    div.addClass("stat-error")
}
