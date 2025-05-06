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
        controls_cell.children(".add-button").addClass("collapsed")
        controls_cell.children(".delete-button").removeClass("collapsed")
    } else if (new_state === "WAITING") {
        controls_cell.children(".add-button").removeClass("collapsed")
        controls_cell.children(".deny-button").removeClass("collapsed")
    } else {
        controls_cell.children(".add-button").removeClass("collapsed")
        controls_cell.children(".deny-button").addClass("collapsed")
        controls_cell.children(".delete-button").addClass("collapsed")
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
