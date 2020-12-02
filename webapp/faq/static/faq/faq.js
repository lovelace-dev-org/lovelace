var faq = {

    /* SUBMIT_EDIT_FORM */
    submit_edit_form: function(event) {
        event.preventDefault();
        let form = $(this);
        
        process_success = function(data) {
            form.parent().parent().html(data.content);
            form.children("input[name='hook']").prop("readonly", false);
            form.find("input[name='action']").val("edit");
        }
        
        submit_ajax_form(form, process_success);
    },

    /* SUBMIT_LINK_FORM */
    submit_link_form: function(event) {
        event.preventDefault();
        let form = $(this);

        process_success = function(data) {
            form.parent().parent().html(data.content);
        }

        submit_ajax_form(form, process_success);
    },

    /* UNLINK_QUESTION */
    unlink_question: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();

        let button = $(caller);
        let url = button.attr("data-url");
        let csrf = button.parent().parent().find(
            "input[name*='csrfmiddlewaretoken']"
        ).attr("value");
        
        $.ajax({
            type: "POST",
            url: url,
            data: {csrfmiddlewaretoken: csrf},
            success: function(data, status, jqxhr) {
                button.parent().next().remove();
                button.parent().remove();
            },
            error: function (jqxhr, status, type) {
            }
        });
    },

    /* EDIT_QUESTION */
    edit_question: function(event, caller) {
        event.preventDefault();
        event.stopPropagation();

        let button = $(caller);
        let url = button.attr("data-url");
        let form = button.parent().parent().find(".faq-edit-form");
        
        $.ajax({
            type: "GET",
            url: url,
            success: function(data, status, jqxhr) {
                form.parent().removeClass("collapsed");
                form.find("textarea[name='question']").val(data["question"]);
                form.find("textarea[name='answer']").val(data["answer"]);
                form.find("input[name='hook']").val(data["hook"]);
                form.find("input[name='hook']").prop("readonly", true);
                form.find("input[name='action']").val("edit");
            },
            error: function (jqxhr, status, type) {
            }
        });    
    },

    /* CLEAR_FORM */
    clear_form: function(caller) {
        let form = $(caller).parent();
        
        form.find("textarea[name='question']").val("");
        form.find("textarea[name='answer']").val("");
        form.find("input[name='hook']").val("");
        form.find("input[name='hook']").prop("readonly", false);
        form.find("input[name='action']").val("create");
    },

    /* HANDLE_TRIGGERS */
    handle_triggers: function(panel, handle, triggers) {
        let container = panel.children(".panel-container");
        if (container.html() == "" || panel.attr("data-panel-type") != "faq") {
            let querystring = []
            triggers.forEach(function (hook) {
                querystring.push("preopen=" + hook);
            });
            handle.attr("data-querystring", querystring.join("&"));
        }
        else {
            let faq = container.children(".faq-panel");
            triggers.forEach(function (hook) {
                faq.children("#" + hook + "-answer").removeClass("collapsed");
                faq.children("#" + hook + "-question").attr("onclick", "collapse_next_div(this);").addClass("highlight");                
            }); 
        }
        if (!panel.hasClass("panel--is-visible")) {
            let arrows = [];
            let first = true;
            triggers.forEach(function (hook) {
                arrow = create_attention_arrow(
                    hook, "left", 
                    "show_panel(event, this, 'faq', '" + panel.attr("id") + "');"
                );
                if (arrow) {
                    arrow.attr("href", handle.attr("href"));
                    arrow.attr("data-querystring", handle.attr("data-querystring"));
                    if (!first) {
                        arrow.css({"opacity": "0", "pointer-events": "none"});
                    }
                    else {
                        first = false;
                    }
                }
            });
        }
    }
}