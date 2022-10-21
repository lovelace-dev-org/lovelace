function request_csv(event, a) {
    event.preventDefault();

    let link = $(a);
    $.ajax({
        url: link.attr("href"),
        success: function (data, text_status, jqxhr) {
            link.hide();
            process_csv_progress(data);
        },
        error: function (jqxhr, status, type) {
            process_csv_error(status);
        }
    });
}

function poll_csv_progress(url) {
    setTimeout(function () {
        $.ajax({
            url: url,
            success: function (data, text_status, jqxhr) {
                process_csv_progress(data);
            },
            error: function (jqxhr, status, type) {
                process_csv_error(status);
            }
        });
    }, 500);
}

function process_csv_progress(data) {
    if (data.state == "SUCCESS") {
        $("div.task-progress").text(data.metadata.current + " / " + data.metadata.total);
        $("div.csv-download").html("<a class='file-url' href='" +
            data.redirect + "' download></a>"
        );
    }
    else if (data.state == "PROGRESS") {
        $("div.task-progress").text(data.metadata.current + " / " + data.metadata.total);
        poll_csv_progress(data.redirect);
    }
    else if (data.state == "FAILURE") {
        $("div.csv-error").text(data.metadata);
    }
    else if (data.state == "PENDING") {
        $("div.task-progress").text("...");
        poll_csv_progress(data.redirect);
    }
}

function request_grades(event, a) {
    event.preventDefault();
    $("body").css("cursor", "progress");

    let link = $(a);
    $.ajax({
        url: link.attr("href"),
        success: function (data, text_status, jqxhr) {
            link.hide();
            process_grades(data);
        },
        error: function (jqxhr, status, type) {
            process_error(status);
        },
        complete: function(jqxhr, status) {
            $("body").css("cursor", "default");
        }
    });
}

function process_grades(data) {
    let first = true;
    let idx = 1;
    $(".page-result-placeholder").remove();
    for (const userid in data) {
        result = data[userid]
        row = $("tr#" + userid);
        row.children("td.grade-missing").text(result.missing);
        row.children("td.grade-score").text(result.score);
        row.children("td.grade-grade").text(result.grade);

        let page_results = result["page_results"];

        page_results.forEach(function(page_result) {
            if (first) {
                let th = $("<th class='vertical-th'>" + page_result.page + "</th>");
                th.attr("onclick", "sort_grades(event, this, " + idx + ", 1)");
                $("th#missing-th").before(th);
                idx += 1
            }
            row.children("td.grade-missing").before("<td class='grade-page-score'>" + parseFloat(page_result.points).toFixed(2) + "</td>");
        });

        if (first) {
            $("col.page-results").attr("span", page_results.length);
            $("col.page-results").css({"width": "auto"});
            first = false;
        }
    }
    $("th#missing-th").attr("onclick", "sort_grades(event, this, " + idx + ", 1)");
    $("th#score-th").attr("onclick", "sort_grades(event, this, " + (idx + 1) + ", 1)");
    $("th#grade-th").attr("onclick", "sort_grades(event, this, " + (idx + 2) + ", 1)");
}

// http://blog.niklasottosson.com/?p=1914
function sort_grades(event, caller, field, order) {
    event.preventDefault();

    let rows = $("table.completion-table tbody tr").get();

    rows.sort(function(a, b) {
        let A = $(a).children("td").eq(field).text().toUpperCase();
        let B = $(b).children("td").eq(field).text().toUpperCase();

        if (A < B) {
            return -1 * order;
        }
        else if (A > B) {
            return 1 * order;
        }
        else {
            return 0;
        }
    });

    if (order == 1) {
        $(caller).attr("onclick", "sort_grades(event, this, " + field + ", -1)");
    }
    else {
        $(caller).attr("onclick", "sort_grades(event, this, " + field + ", 1)");
    }

    rows.forEach(function(row) {
        $("table.completion-table").children("tbody").append(row);
    });
}
