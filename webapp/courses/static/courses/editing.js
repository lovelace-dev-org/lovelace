const editing = {

    active_button: null,

    show_widget_panel: function (event, caller) {
        event.preventDefault()

        if (editing.active_button === null) {
            const button = $(caller)
            editing.active_button = button
            button.parent().next().addClass("edit-highlight")

            show_panel(event, caller, 'edit-panel', 'edit-panel', true)
        }
    },

    get_form_url: function (event) {
        event.preventDefault()
        event.stopPropagation()
        const caller = $(this)

        $(".edit-form-widget").remove()

        process_success = function (data) {
            editing.fetch_edit_form(data.form_url, caller)
        }

        submit_ajax_form(caller, process_success)
    },

    get_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()
        const source = $(caller)
        const url = source.attr("data-url")

        $(".edit-form-widget").remove()

        editing.fetch_edit_form(url, source)
    },

    fetch_edit_form: function (address, caller) {
        $.ajax({
            type: "GET",
            url: address,
            success: function (data, status, jqxhr) {
                const form = $(data)
                caller.closest("div").after(form)
            }
        })
    },

    submit_form: function (event) {
        event.preventDefault()
        const form = $(this)

        process_success = function (data) {
            if (data.redirect) {
                location.replace(data.redirect)
            } else if (data.refresh) {
                const container = form.closest(".panel-container")
                const content = container.children("div.panel-content")
                if (content) {
                    refresh_panel(container, content.attr("data-refresh-url"))
                } else {
                    location.reload()
                }
            } else {
                location.reload()
            }
        }

        submit_ajax_form(form, process_success)
    },

    move_item: function (event, caller, direction) {
        event.preventDefault()
        const button = $(caller)
        button.attr(
            "data-csrf",
            button.closest("form").children("input[name='csrfmiddlewaretoken']").val()
        )
        const item_div = button.closest("div")

        process_success = function (data) {
            if (direction == "up") {
                const prev_div = item_div.prev("div")
                item_div.insertBefore(prev_div)
            }
            else {
                const next_div = item_div.next("div")
                item_div.insertAfter(next_div)
            }
        }
        submit_ajax_action(button, process_success)
    },

    delete_item: function (event, caller) {
        event.preventDefault()
        const button = $(caller)
        button.attr(
            "data-csrf",
            button.closest("form").children("input[name='csrfmiddlewaretoken']").val()
        )
        const item_div = button.closest("div")

        process_success = function (data) {
            item_div.remove()
        }
        submit_ajax_action(button, process_success)
    },

    hide_widget_panel: function (event) {
        event.preventDefault()

        editing.active_button.parent().next().removeClass("edit-highlight")
        editing.active_button = null;
        hide_panel(event, 'edit-panel')
    }
}



