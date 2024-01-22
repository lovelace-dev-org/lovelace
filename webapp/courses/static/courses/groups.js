const grp = {
    active_button: null,

    fetch_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".form-tr").remove()

        if (grp.active_button) {
            grp.active_button.attr("onclick", "grp.fetch_form(event, this);")
        }

        const button = $(caller)
        const url = button.attr("data-url")

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                const form = $(data)
                form.submit(grp.submit_form)
                const form_tr = $("<tr class='form-tr'><td colspan='4'></td></tr>")
                form_tr.children("td").append(form)
                button.parent().parent().after(form_tr)
                button.attr("onclick", "grp.close_form(event, this);")
                grp.active_button = button
            }
        })
    },

    close_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".form-tr").remove()

        const button = $(caller)
        button.attr("onclick", "grp.fetch_form(event, this);")
        grp.active_button = null
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

    send_invites: function (event) {
        event.preventDefault()
        const form = $(this)

        process_success = function (data) {
        }

        submit_ajax_form(form, process_success)
    },

    process_invite: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()
        const button = $(caller)
        process_success = function (data) {
            location.reload()
        }

        submit_ajax_action(button, process_success)
    },

    toggle_rename: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        button.parent().siblings().eq(0).children().toggleClass("collapsed")
    },

    submit_rename: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const input = $(caller)

        process_success = function (data) {
            const span = input.siblings("span")
            span.html(input.val())
            span.toggleClass("collapsed")
            input.toggleClass("collapsed")
        }

        submit_ajax_action(input, process_success, { name: input.val() })
    },

    set_supervisor: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const select = $(caller)

        process_success = function (data) {
        }

        submit_ajax_action(select, process_success, { supervisor: select.val() })
    },

    remove_group: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)

        process_success = function (data) {
            const tr = button.parent().parent()
            tr.nextUntil("tr.section-header").remove()
            tr.remove()
        }

        submit_ajax_action(button, process_success)
    },

    remove_member: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)

        process_success = function (data) {
            button.parent().parent().remove()
        }

        submit_ajax_action(button, process_success)
    }
}
