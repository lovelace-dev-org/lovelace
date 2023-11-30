const exam = {

    fetch_form: function (event, caller) {

        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        const url = button.attr("data-url")
        $(".form-tr").remove()
        $(".exam-management-form").remove()

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                const form = $(data)
                form.submit(exam.submit_form)
                if (button.attr("data-in-table")) {
                    const form_tr = $("<tr class='form-tr'><td colspan='6'></td></tr>")
                    form_tr.children("td").append(form)
                    button.parent().parent().after(form_tr)
                }
                else {
                    button.after(form);
                }
                form.find("input[type!=hidden]").first().focus()
                button.attr("onclick", "exam.close_form(event, this)")
            },
        })
    },

    close_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".form-tr").remove()
        $(".exam-management-form").remove()
        const button = $(caller)
        button.attr("onclick", "exam.fetch_form(event, this)")
    },

    submit_form: function (event) {
        event.preventDefault()
        const form = $(this)

        process_success = function (data) {
            if (data.redirect) {
                location.replace(data.redirect)
            } else {
                location.reload()
            }
        }
        submit_ajax_form(form, process_success)
    },

    start_exam: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        const url = button.attr("data-url")

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                if (data.error) {
                    const errorbox = button.parent().parent().find("div.error")
                    errorbox.css("display", "block")
                    errorbox.html(data.error)
                }
                const form_fields = $(data.rendered_form)
                const form = button.parent().parent().find(".question > form")
                const form_submit = button.parent().parent().find(
                    ".question > form > input[type='submit']"
                )
                form_submit.before(form_fields)
                form.submit(exam.submit_exam)
                form.dirty({preventLeaving: true})
                form.keypress(function(event) {
                    if (event.which == '13') {
                        event.preventDefault()
                    }
                })
                button.prop("disabled", true)
                exam.set_scroll_targets()
            },
        })
    },

    preview_attempt: function (event, caller) {
        event.preventDefault()
        const button = $(caller)
        const url = button.attr("data-url")
        const popup = $(".attempt-preview")

        $.get(url, function (data, textStatus, jqXHR) {
            popup.html(data)
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
        })
    },

    toggle_answer_certainty: function (event, caller) {
        const heading = $(caller)
        const container = heading.parent()
        const question = container.attr("data-question-number")
        if (heading.hasClass("multiexam-question-certain")) {
            heading.removeClass("multiexam-question-certain")
            heading.addClass("multiexam-question-uncertain")
            $("#exam-shortcut-" + question).removeClass("exam-shortcut-certain")
            $("#exam-shortcut-" + question).addClass("exam-shortcut-uncertain")
            heading.siblings(".multiexam-answer-container").children("input[type='hidden']").val("1")
        }
        else if (heading.hasClass("multiexam-question-uncertain")) {
            heading.removeClass("multiexam-question-uncertain")
            heading.addClass("multiexam-question-certain")
            $("#exam-shortcut-" + question).removeClass("exam-shortcut-uncertain")
            $("#exam-shortcut-" + question).addClass("exam-shortcut-certain")
            heading.siblings(".multiexam-answer-container").children("input[type='hidden']").val("2")
        }
    },

    mark_answered: function (event, caller) {
        const input = $(caller)
        const container = input.parent().parent().parent()
        const question = container.attr("data-question-number")
        const heading = container.children(".multiexam-question-unanswered")
        if (heading.length == 1) {
            heading.removeClass("multiexam-question-unanswered")
            heading.addClass("multiexam-question-uncertain")
            const shortcut = $("#exam-shortcut-" + question)
            shortcut.removeClass("exam-shortcut-unanswered")
            shortcut.addClass("exam-shortcut-uncertain")
            input.parent().parent().children("input[type='hidden']").val("1")
            $("progress.multiexam-progress").val($("progress.multiexam-progress").val() + 1)
        }
    },

    set_scroll_targets: function () {
        $("div.multiexam-summary-container").find(".interactive").each(function () {
            let shortcut = $(this)
            let target = $("#exam-question-" + shortcut.attr("data-shortcut-number"))
            shortcut.attr("data-shortcut-target-pos", target.position().top)
        })
    },

    scroll_to_question: function (caller) {
        const shortcut = $(caller)
        const target_pos = shortcut.attr("data-shortcut-target-pos")
        const pad = $(".multiexam-summary-container").height()
        $(".multiexam-exam-form").animate({
            scrollTop: target_pos - pad
        })
    }
}

$(document).ready(function () {
    $(".popup").click(function () {
        $(this).css({ opacity: "0", "pointer-events": "none" })
    })
    $(".popup > div").click(function (event) {
        event.stopPropagation()
    })
})
