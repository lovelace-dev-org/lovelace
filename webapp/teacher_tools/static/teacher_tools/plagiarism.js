function request_moss (event, a) {
    event.preventDefault()

    const form = $(this)
    const url = form.attr("action")
    $.ajax({
        type: form.attr("method"),
        url,
        data: new FormData(form[0]),
        processData: false,
        contentType: false,
        dataType: "json",
        success: function (data, text_status, jqxhr) {
            process_moss_progress(data)
        },
        error: function (jqxhr, status, type) {
            process_moss_error(status)
        }
    })
}

function poll_moss_progress (url) {
    setTimeout(function () {
        $.ajax({
            url,
            success: function (data, text_status, jqxhr) {
                process_moss_progress(data)
            },
            error: function (jqxhr, status, type) {
                process_moss_error(status)
            }
        })
    }, 10000)
}

function process_moss_progress (data) {
    console.log(data)
    if (data.state === "SUCCESS") {
        $("div#task-progress").text(data.metadata.current + " / " + data.metadata.total)
        $("div#moss-link").html("<a href='" +
            data.metadata.url + "'>" + data.metadata.url + "</a>"
        )
    } else if (data.state === "PROGRESS") {
        $("div#task-progress").text(data.metadata.current + " / " + data.metadata.total)
        poll_moss_progress(data.redirect)
    } else if (data.state === "FAILURE") {
        $("div#moss-error").text(data.metadata)
    } else if (data.state === "PENDING") {
        $("div#task-progress").text("...")
        poll_moss_progress(data.redirect)
    }
}

$(document).ready(function () {
    $("#plagiarism-form").submit(request_moss)
})
