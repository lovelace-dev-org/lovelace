const ase = {
    active_button: null,
    dragged_li: null,

    fetch_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".assessment-staff-form").remove()

        if (ase.active_button) {
            ase.active_button.attr("onclick", "ase.fetch_form(event, this);")
        }

        const button = $(caller)
        const url = button.attr("data-url")
        const section = button.attr("data-section")
        const bullet_id = button.attr("data-bullet-id")

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                const form = $(data)
                form.submit(ase.submit_form)
                form.children("input[name=active_bullet]").val(bullet_id)
                form.children("input[name=active_section]").val(section)
                button.parent().after(form)
                button.attr("onclick", "ase.close_form(event, this);")
                ase.active_button = button
            }
        })
    },

    close_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".assessment-staff-form").remove()

        const button = $(caller)
        button.attr("onclick", "ase.fetch_form(event, this);")
        ase.active_button = null
    },

    submit_form: function (event) {
        event.preventDefault()
        const form = $(this)

        process_success = function (data) {
            const panel_div = form.parents(".assessment-panel").first()
            ase.reload_panel(panel_div)
        }

        submit_ajax_form(form, process_success)
    },

    submit_assessment: function (event) {
        event.preventDefault()
        const form = $(this)

        submit_ajax_form(form, function () {})
    },

    reload_panel: function (panel_div) {
        const url = panel_div.attr("data-source-url")

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                panel_div.replaceWith(data)
            }
        })
    },

    delete_section: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        process_success = function (data) {
            const li = button.parent()
            const ul = li.next("ul")
            ul.remove()
            li.remove()
        }

        submit_ajax_action(button, process_success)
    },

    delete_bullet: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        process_success = function (data) {
            const li = button.parent()
            li.remove()
        }

        submit_ajax_action(button, process_success)
    },

    start_drag: function (event, bullet_id) {
        $(".assessment-staff-form").remove()

        if (ase.active_button) {
            ase.active_button.attr("onclick", "ase.fetch_form(event, this, " + bullet_id + ");")
            ase.active_button = null
        }

        $(".drag-target").removeClass("collapsed")
        event.dataTransfer.setData("bullet", bullet_id)
        ase.dragged_li = $(event.target).parent()
        event.dataTransfer.effectAllowed = "move"
    },

    end_drag: function (event) {
        console.log("end")
        $(".drag-target").addClass("collapsed")
    },

    over_drag_target: function (event) {
        console.log("over")
        event.preventDefault()
        $(event.target).addClass("highlighted")
        event.dataTransfer.dropEffect = "move"
    },

    leave_drag_target: function (event) {
        event.preventDefault()
        $(event.target).removeClass("highlighted")
    },

    drop_to_target: function (event) {
        console.log("drop")
        event.preventDefault()
        $("body").css("cursor", "progress")

        const button = $(event.target)
        const url = button.attr("data-url")
        const csrf = button.attr("data-csrf")

        $.ajax({
            type: "POST",
            url,
            data: {
                csrfmiddlewaretoken: csrf,
                active_bullet: event.dataTransfer.getData("bullet")
            },
            success: function (data, status, jqxhr) {
                button.removeClass("highlighted")
                const target = button.parent()
                if (button.hasClass("drop-after")) {
                    target.after(ase.dragged_li)
                } else {
                    target.before(ase.dragged_li)
                }
            },
            error: function (jqxhr, status, type) {
                console.log(status)
            },
            complete: function (jqxhr, status) {
                $("body").css("cursor", "default")
            }
        })
    },

    update_section_score: function (event) {
        const widget = $(this)
        const section = widget.parent().parent().prevAll(".assessment-section").first()
        const bullets = section.nextUntil("tr.assessment-section")
        let total = 0
        bullets.each(function (bullet) {
            const points = $(this).find("input").first().val()
            if (points) {
                total += parseFloat(points)
            }
        })
        const old_section_score = parseFloat(section.children("td").eq(1).html())
        section.children("td").eq(1).html(total)
        const total_td = $("tfoot > tr > td").eq(2)
        const old_total = parseFloat(total_td.html())
        total_td.html(old_total - old_section_score + total)
    },

    update_exercise (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        process_success = function (data) {
            button.after("<div>OK</div>")
        }

        submit_ajax_action(button, process_success)
    }
}
