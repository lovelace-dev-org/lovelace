const formtools = {

    fetch_form: function (event, caller) {

        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        const url = button.attr("data-url")
        $(".form-tr").remove()
        $(".management-form").remove()

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                const form = $(data).find("form")
                form.submit(formtools.submit_form)
                if (button.attr("data-in-table")) {
                    const colspan = button.attr("data-colspan")
                    const empty_tr = $("<tr class='form-tr collapse'><td colspan='" + colspan + "'></td></tr>")
                    const form_tr = $("<tr class='form-tr'><td colspan='" + colspan + "'></td></tr>")
                    form_tr.children("td").append(form)
                    button.parent().parent().after(form_tr)
                    //button.parent().parent().after(empty_tr)
                }
                else {
                    button.after(form);
                }
                form.find("input[type!=hidden]").first().trigger("focus")
                button.attr("onclick", "formtools.close_form(event, this)")
            },
            error: function (jqxhr, status, type) {
                const error_div = $("<div class='error management-form'></div>")
                error_div.html(jqxhr.responseText)
                if (button.attr("data-in-table")) {
                    const colspan = button.attr("data-colspan")
                    const empty_tr = $("<tr class='form-tr collapse'><td colspan='" + colspan + "'></td></tr>")
                    const error_tr = $("<tr class='form-tr'><td colspan='" + colspan + "'></td></tr>")
                    error_tr.children("td").append(error_div)
                    button.parent().parent().after(error_tr)
                }
                else {
                    button.after(error_div);
                }
            }
        })
    },

    close_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".form-tr").remove()
        $(".management-form").remove()
        const button = $(caller)
        button.attr("onclick", "formtools.fetch_form(event, this)")
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

    fetch_rows: function (event, caller) {

        event.stopPropagation()
        const widget = $(caller)
        const url = widget.attr("data-change-url")
        const form = widget.closest("form")

        $.ajax({
            type: "GET",
            url,
            data: {
                value: widget.val()
            },
            success: function (data, status, jqxhr) {
                form.find("input[name^='extra-']").closest("table").remove()
                const rows = $(data)
                widget.closest("table").after(rows)
            },
        })
    }
}
