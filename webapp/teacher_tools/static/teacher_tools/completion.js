function request_csv (event, a) {
    event.preventDefault()

    const link = $(a)
    $.ajax({
        url: link.attr("href"),
        success: function (data, text_status, jqxhr) {
            link.hide()
            process_csv_progress(data)
        },
        error: function (jqxhr, status, type) {
            process_csv_error(status)
        }
    })
}

function poll_csv_progress (url) {
    setTimeout(function () {
        $.ajax({
            url,
            success: function (data, text_status, jqxhr) {
                process_csv_progress(data)
            },
            error: function (jqxhr, status, type) {
                process_csv_error(status)
            }
        })
    }, 500)
}

function process_csv_progress (data) {
    if (data.state === "SUCCESS") {
        $("div.task-progress").text(data.metadata.current + " / " + data.metadata.total)
        $("div.csv-download").html("<a class='file-url' href='" +
            data.redirect + "' download></a>"
        )
    } else if (data.state === "PROGRESS") {
        $("div.task-progress").text(data.metadata.current + " / " + data.metadata.total)
        poll_csv_progress(data.redirect)
    } else if (data.state === "FAILURE") {
        $("div.csv-error").text(data.metadata)
    } else if (data.state === "PENDING") {
        $("div.task-progress").text("...")
        poll_csv_progress(data.redirect)
    }
}

function request_grades (event, a) {
    event.preventDefault()
    $("body").css("cursor", "progress")

    const link = $(a)
    $.ajax({
        url: link.attr("href"),
        success: function (data, text_status, jqxhr) {
            link.hide()
            process_grades(data)
        },
        error: function (jqxhr, status, type) {
            process_error(status)
        },
        complete: function (jqxhr, status) {
            $("body").css("cursor", "default")
        }
    })
}

function process_grades (data) {
    let first = true
    let idx = 1
    $(".page-result-placeholder").remove()
    for (const userid in data) {
        result = data[userid]
        row = $("tr#" + userid)
        row.children("td.grade-missing").text(result.missing)
        row.children("td.grade-score").text(result.score)
        row.children("td.grade-grade").text(result.grade)

        const page_results = result.page_results

        page_results.forEach(function (page_result) {
            if (first) {
                const th = $("<th class='vertical-th'>" + page_result.page + "</th>")
                th.attr("onclick", "sort_table(event, this, " + idx + ", 1, true)")
                $("th#missing-th").before(th)
                idx += 1
            }
            const score = parseFloat(page_result.points).toFixed(2)
            const td = $("<td class='grade-page-score'>" + score + "</td>")
            td.attr("data-score", score)
            td.attr("data-missing", page_result.task_count - page_result.done_count)
            row.children("td.grade-missing").before(td)
        })

        if (first) {
            $("col.page-results").attr("span", page_results.length)
            $("col.page-results").css({ width: "auto" })
            first = false
        }
    }
    $("th#missing-th").attr("onclick", "sort_table(event, this, " + idx + ", 1, true)")
    $("th#score-th").attr("onclick", "sort_table(event, this, " + (idx + 1) + ", 1, true)")
    $("th#grade-th").attr("onclick", "sort_table(event, this, " + (idx + 2) + ", 1, false)")
    $("div.table-controls").removeClass("collapsed")
}

function toggle_cell_data (event, caller, mode) {
    event.preventDefault()
    $("td.grade-page-score").each(function (index) {
        td = $(this)
        td.html(td.attr(mode))
    })
}
