var ase = {
    active_button: null,
    dragged_li: null,

    fetch_form: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();

        $(".assessment-staff-form").remove();
        
        if (ase.active_button) {
            ase.active_button.attr("onclick", "ase.fetch_form(event, this);");
        }
        
        let button = $(caller);
        let url = button.attr("data-url");
        let section = button.attr("data-section");
        let bullet_id = button.attr("data-bullet-id");
        
        $.ajax({
            type: "GET",
            url: url,
            success: function(data, status, jqxhr) {
                let form = $(data);
                form.submit(ase.submit_form);
                form.children("input[name=active_bullet]").val(bullet_id);
                form.children("input[name=active_section]").val(section);
                button.parent().after(form);
                button.attr("onclick", "ase.close_form(event, this);");
                ase.active_button = button;
            }
        });
    },
    
    close_form: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();
        
        $(".assessment-staff-form").remove();
        
        let button = $(caller);
        button.attr("onclick", "ase.fetch_form(event, this);");
        ase.active_button = null;
    },
    
    submit_form: function(event) {
        event.preventDefault();
        let form = $(this);
        
        process_success = function(data) {
            let panel_div = form.parents(".assessment-panel").first();
            ase.reload_panel(panel_div);
        }
        
        submit_ajax_form(form, process_success);
    },
    
    reload_panel: function(panel_div) {
        let url = panel_div.attr("data-source-url");
        
        $.ajax({
            type: "GET",
            url: url,
            success: function(data, status, jqxhr) {
                panel_div.replaceWith(data);
            }
        });
    },
    
    delete_section: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();

        let button = $(caller);
        process_success = function(data) {
            let li = button.parent();
            let ul = li.next("ul");
            ul.remove();
            li.remove();            
        }
        
        submit_ajax_delete(button, process_success)
    },

    delete_bullet: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();

        let button = $(caller);
        process_success = function(data) {
            let li = button.parent();
            li.remove();            
        }
        
        submit_ajax_delete(button, process_success)
    },
    
    start_drag: function(event, bullet_id) {
        $(".assessment-staff-form").remove();
        
        if (ase.active_button) {
            ase.active_button.attr("onclick", "ase.fetch_form(event, this, " + bullet_id + ");");
            ase.active_button = null;
        }

        $(".drag-target").removeClass("collapsed");
        event.dataTransfer.setData("bullet", bullet_id);
        ase.dragged_li = $(event.target).parent();
        event.dataTransfer.effectAllowed = "move";
    },

    end_drag: function(event) {
        console.log("end");
        $(".drag-target").addClass("collapsed");
    },
    
    over_drag_target: function(event) {                
        console.log("over");
        event.preventDefault();
        $(event.target).addClass("highlighted");
        event.dataTransfer.dropEffect = "move";
    },
    
    leave_drag_target: function(event) {                
        event.preventDefault();
        $(event.target).removeClass("highlighted");
    },
    
    drop_to_target: function(event) {
        console.log("drop");
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
                active_bullet: event.dataTransfer.getData("bullet")
            },
            success: function(data, status, jqxhr) {
                button.removeClass("highlighted");
                let target = button.parent();
                if (button.hasClass("drop-after")) {
                    target.after(ase.dragged_li);
                }
                else {
                    target.before(ase.dragged_li);                    
                }
            },
            error: function (jqxhr, status, type) {
                console.log(status);
            },
            complete: function(jqxhr, status) {
                $("body").css("cursor", "default");
            }
        });
    },
}

