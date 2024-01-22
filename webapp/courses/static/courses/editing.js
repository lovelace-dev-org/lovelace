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
        const form = $(this)

        $(".edit-form-widget").remove()

        process_success = function (data) {
            editing.fetch_edit_form(data.form_url, form)
        }

        submit_ajax_form(form, process_success)
    },

    fetch_edit_form: function (address, caller) {
        $.ajax({
            type: "GET",
            url: address,
            success: function (data, status, jqxhr) {
                const form = $(data)
                caller.after(form)
            }
        })
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


    hide_widget_panel: function (event) {
        event.preventDefault()

        editing.active_button.parent().next().removeClass("edit-highlight")
        editing.active_button = null;
        hide_panel(event, 'edit-panel')
    }
}



