function process_one (event, button, action) {
    event.preventDefault()

    const tr = $(button).parent().parent()
    const form = $(".teacher-form")
    const username = tr.children(".username-cell").html()
    const csrf = form.children("input[name*='csrfmiddlewaretoken']").attr("value")

    $.ajax({
        type: form.attr("method"),
        url: form.attr("action"),
        data: { username, action, csrfmiddlewaretoken: csrf },
        dataType: "json",
        success: process_success_one,
        error: function (xhr, status, type) {
            console.log(xhr)
            const popup = $("#status-msg-popup")
            popup.children("div").html(status)
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
        }
    })
}

function process_many (event) {
    event.preventDefault()

    const form = $(".teacher-form")

    $.ajax({
        type: form.attr("method"),
        url: form.attr("action"),
        data: form.serialize(),
        dataType: "json",
        success: process_success_many,
        error: function (xhr, status, type) {
            console.log(xhr)
            const popup = $("#status-msg-popup")
            popup.children("div").html(status)
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
        }
    })
}

function change_state (username, new_state) {
    const tr = $("table.enrollments-table").children("tbody").children("#" + username + "-tr")
    const state_cell = tr.children(".state-cell")
    const controls_cell = tr.children(".controls-cell")

    state_cell.html(new_state)

    if (new_state === "ACCEPTED") {
        controls_cell.html(
            "<button class=\"enrollment-expel-button\" "
            + "onclick=\"process_one(event, this, 'expelled')\">expel</button></td>"
        )
    } else if (new_state === "WAITING") {
        controls_cell.html(
            "<button class=\"enrollment-accept-button\" "
            + "onclick=\"process_one(event, this, 'accepted')\">accept</button>"
            + "<button class=\"enrollment-deny-button\" "
            + "onclick=\"process_one(event, this, 'denied')\">deny</button>"
        )
    } else {
        controls_cell.html(
            "<button class=\"enrollment-accept-button\" "
            + "onclick=\"process_one(event, this, 'accepted')\">accept</button>"
        )
    }
}

function process_success_one (response, status, jqxhr_obj) {
    const popup = $("#status-msg-popup")
    popup.children("div").html(response.msg)
    popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })

    change_state(response.user, response.new_state)
}

function process_success_many (response, status, jqxhr_obj) {
    console.log(response)

    const popup = $("#status-msg-popup")
    let log = ""
    if (response["users-affected"].length > 0) {
        log += "<h3>" + response["affected-title"] + "</h3>"

        response["users-affected"].forEach(function (username) {
            log += "<div>" + username + "</div>"
            change_state(username, response.new_state)
        })
    }

    if (response["users-skipped"].length > 0) {
        log += "<h3>" + response["skipped-title"] + "</h3>"

        response["users-skipped"].forEach(function (username) {
            log += "<div>" + username + "</div>"
        })
    }

    popup.children("div").html(log)
    popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
}

// http://blog.niklasottosson.com/?p=1914
function sort_enrollments (event, field, order) {
    event.preventDefault()

    const rows = $("table.enrollments-table tbody tr").get()

    rows.sort(function (a, b) {
        const A = $(a).children("td").eq(field).text().toUpperCase()
        const B = $(b).children("td").eq(field).text().toUpperCase()

        if (A < B) {
            return -1 * order
        } else if (A > B) {
            return 1 * order
        } else {
            return 0
        }
    })

    rows.forEach(function (row) {
        $("table.enrollments-table").children("tbody").append(row)
    })
}

function expand_task_list (page_bullet) {
    const bullet = $(page_bullet)
    bullet.next("ul").show()
    bullet.attr("onclick", "collapse_task_list(this)")
    bullet.removeClass("tasks-collapsed")
    bullet.addClass("tasks-expanded")
}

function collapse_task_list (page_bullet) {
    const bullet = $(page_bullet)
    bullet.next("ul").hide()
    bullet.attr("onclick", "expand_task_list(this)")
    bullet.removeClass("tasks-expanded")
    bullet.addClass("tasks-collapsed")
}

$(document).ready(function () {
    $(".teacher-form").submit(process_many)
})

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
    }, 100)
}

function process_csv_progress (data) {
    if (data.state === "SUCCESS") {
        $("div.csv-progress").text(data.metadata.current + " / " + data.metadata.total)
        $("div.csv-download").html("<a class='file-url' href='" +
            data.redirect + "' download></a>"
        )
    } else if (data.state === "PROGRESS") {
        $("div.csv-progress").text(data.metadata.current + " / " + data.metadata.total)
        poll_csv_progress(data.redirect)
    } else if (data.state === "FAILURE") {
        $("div.csv-error").text(data.metadata)
    } else if (data.state === "PENDING") {
        $("div.csv-progress").text("...")
        poll_csv_progress(data.redirect)
    }
}

function submit_reminders (event) {
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
        success: function (data, text_status, jqxhr_obj) {
            $("#reminder-list-title").show()
            const ul = $("ul.preview-list")
            data.reminders.forEach(function (student) {
                ul.append("<li class='student-bullet'>" +
                    student.last_name + " " + student.first_name +
                    " (" + student.username + ")" +
                    " - " + student.email + "</li>"
                )
            })
            $("textarea").attr("disabled", true)
            $("input.action-hint").attr("value", "send")
            const submit_button = $("input#reminder-submit").detach()
            submit_button.attr("value", data.submit_text)

            ul.after(submit_button)
        },
        error: function (xhr, status, type) {
        }
    })
}

$(document).ready(function () {
    $("#reminder-form").submit(submit_reminders)
})
