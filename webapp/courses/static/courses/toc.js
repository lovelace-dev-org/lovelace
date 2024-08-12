const toc = {

    active_button: null,
    dragged_li: null,

    fetch_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".toc-form").remove()

        if (toc.active_button) {
            toc.active_button.attr("onclick", "toc.fetch_form(event, this);")
        }

        const button = $(caller)
        const url = button.attr("data-url")
        const node_id = button.attr("data-node-id")

        $.ajax({
            type: "GET",
            url,
            success: function (data, status, jqxhr) {
                const form = $(data)
                form.children("input[name=active_node]").val(node_id)
                button.parent().after(form)
                button.attr("onclick", "toc.close_form(event, this);")
                toc.active_button = button
                form.find("input[type!=hidden]").first().focus()
            }
        })
    },

    close_form: function (event, caller) {
        event.preventDefault()
        event.stopPropagation()

        $(".toc-form").remove()
        const button = $(caller)
        button.attr("onclick", "toc.fetch_form(event, this);")
        toc.active_button = null
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

    remove_node: function (event, caller, node_id) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)
        const url = button.attr("data-url")
        const csrf = button.attr("data-csrf")

        $.ajax({
            type: "POST",
            url,
            data: { csrfmiddlewaretoken: csrf },
            success: function (data, status, jqxhr) {
                const li = button.parent()
                const ul = li.next("ul")
                li.after(ul.children())
                ul.remove()
                li.remove()
            },
            error: function (jqxhr, status, type) {
            }
        })
    },

    submit_instance_settings: function (event) {
        event.preventDefault()
        const form = $(this)

        process_success = function (data) {
            location.reload()
        }

        submit_ajax_form(form, process_success)
    },

    start_drag: function (event, node_id) {
        $(".toc-form").remove()

        if (toc.active_button) {
            toc.active_button.attr("onclick", "toc.fetch_form(event, this, " + node_id + ");")
            toc.active_button = null
        }

        $(".toc-drag-target").not("img[id$=" + node_id + "]").removeClass("collapsed")
        event.dataTransfer.setData("node", node_id)
        toc.dragged_li = $(event.target).parent()
        event.dataTransfer.effectAllowed = "move"
    },

    end_drag: function (event) {
        $(".toc-drag-target").addClass("collapsed")
    },

    over_drag_target: function (event) {
        event.preventDefault()
        $(event.target).addClass("highlighted")
        event.dataTransfer.dropEffect = "move"
    },

    leave_drag_target: function (event) {
        event.preventDefault()
        $(event.target).removeClass("highlighted")
    },

    drop_to_target: function (event, target_id) {
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
                active_node: event.dataTransfer.getData("node")
            },
            success: function (data, status, jqxhr) {
                const dragged_ul = toc.dragged_li.next("ul")
                $("body").css("cursor", "default")
                button.removeClass("highlighted")
                if (button.hasClass("drop-after")) {
                    let target = button.parent()
                    while (target.next("ul").length) {
                        target = target.next("ul")
                    }
                    target.after(toc.dragged_li)
                    toc.dragged_li.after(dragged_ul)
                } else if (button.hasClass("drop-before")) {
                    const target = button.parent()
                    target.before(toc.dragged_li)
                    toc.dragged_li.after(dragged_ul)
                } else {
                    const parent_node = button.parent()
                    let ul = parent_node.next("ul")
                    if (ul.length) {
                        ul.prepend(toc.dragged_li)
                        toc.dragged_li.after(dragged_ul)
                    } else {
                        ul = $("<ul></ul>")
                        ul.append(toc.dragged_li)
                        console.log(ul)
                        parent_node.after(ul)
                        toc.dragged_li.after(dragged_ul)
                    }
                }
            },
            error: function (jqxhr, status, type) {
                $("body").css("cursor", "default")
                console.log(status)
            }
        })
    }
}
