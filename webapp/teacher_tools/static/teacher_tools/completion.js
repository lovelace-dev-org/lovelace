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

