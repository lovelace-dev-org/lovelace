var toc = {
    
    active_button: null,
    dragged_li: null,
    
    fetch_form: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();
        
        $(".toc-form").remove();
        
        if (toc.active_button) {
            toc.active_button.attr("onclick", "toc.fetch_form(event, this);");
        }

        let button = $(caller);
        let url = button.attr("data-url");
        let node_id = button.attr("data-node-id");
        
        $.ajax({
            type: "GET",
            url: url,
            success: function(data, status, jqxhr) {
                let form = $(data);
                form.submit(toc.submit_form);
                form.children("input[name=active_node]").val(node_id);
                button.parent().after(form);
                button.attr("onclick", "toc.close_form(event, this);");
                toc.active_button = button;
            }
        });
    },
    
    close_form: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();
        
        $(".toc-form").remove();
        let button = $(caller);
        button.attr("onclick", "toc.fetch_form(event, this);");
        toc.active_button = null;
    },
    
    submit_form: function(event) {
        event.preventDefault();
        let form = $(this);
        
        process_success = function(data) {
            if (data.redirect) {
                location.replace(data.redirect);
            }
            else {
                location.reload();
            }
        }
        
        submit_ajax_form(form, process_success);
    },
    
    remove_node: function(event, caller, node_id) {
        event.preventDefault();
        event.stopPropagation();
        
        let button = $(caller);
        let url = button.attr("data-url");        
        let csrf = button.attr("data-csrf");
        
        $.ajax({
            type: "POST",
            url: url,
            data: {csrfmiddlewaretoken: csrf},
            success: function(data, status, jqxhr) {
                let li = button.parent()
                let ul = li.next("ul");
                li.after(ul.children());
                ul.remove();
                li.remove();
            },
            error: function (jqxhr, status, type) {
            }
        });
    },
    
    submit_instance_settings: function(event) {
        event.preventDefault();
        let form = $(this);
        
        process_success = function(data) {
            location.reload();
        }
        
        submit_ajax_form(form, process_success);
    },
        
    
    start_drag: function(event, node_id) {
        $(".toc-form").remove();
        
        if (toc.active_button) {
            toc.active_button.attr("onclick", "toc.fetch_form(event, this, " + node_id + ");");
            toc.active_button = null;
        }
                
        $(".toc-drag-target").removeClass("collapsed");
        event.dataTransfer.setData("node", node_id);
        console.log($(event.target).parent());
        toc.dragged_li = $(event.target).parent();
        event.dataTransfer.effectAllowed = "move";
    },
    
    end_drag: function(event) {
        $(".toc-drag-target").addClass("collapsed");
    },
    
    over_drag_target: function(event) {        
        
        event.preventDefault();
        $(event.target).addClass("highlighted");
        event.dataTransfer.dropEffect = "move";
    },

    leave_drag_target: function(event) {        
        
        event.preventDefault();
        $(event.target).removeClass("highlighted");
    },
    
    drop_to_target: function(event, target_id) {
        event.preventDefault();
        $("body").css("cursor", "progress");
        
        let button = $(event.target);
        let url = button.attr("data-url");
        let csrf = button.attr("data-csrf");

        $.ajax({
            type: "POST",
            url: url,
            data: {
                csrfmiddlewaretoken: csrf,
                active_node: event.dataTransfer.getData("node")
            },
            success: function(data, status, jqxhr) {
                let dragged_ul = toc.dragged_li.next("ul");
                $("body").css("cursor", "default");
                button.removeClass("highlighted");
                if (button.hasClass("drop-after")) {
                    let target = button.parent();
                    while (target.next("ul").length) {
                        target = target.next("ul");
                    }                    
                    target.after(toc.dragged_li);
                    toc.dragged_li.after(dragged_ul);
                }
                else if (button.hasClass("drop-before")) {
                    let target = button.parent();
                    target.before(toc.dragged_li);
                    toc.dragged_li.after(dragged_ul);
                }                
                else {
                    let parent_node = button.parent();
                    let ul = parent_node.next("ul");
                    if (ul.length) {
                        ul.prepend(toc.dragged_li);
                        toc.dragged_li.after(dragged_ul);
                    }
                    else {
                        ul = $("<ul></ul>");
                        ul.append(toc.dragged_li);
                        console.log(ul);
                        parent_node.after(ul);
                        toc.dragged_li.after(dragged_ul);
                    }
                }
            },
            error: function (jqxhr, status, type) {
                $("body").css("cursor", "default");
                console.log(status);
            }
        });
    }
}

