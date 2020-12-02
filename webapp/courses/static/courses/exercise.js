function exercise_success(data, result_div, error_div, form_parent) {
    var hints_div = form_parent.children("div.hints");
    var msgs_div = form_parent.children("div.msgs");
    var comments_div = form_parent.children("div.comments");
    var file_result_div = form_parent.children("div.file-result");

    if (data.result) {
        result_div.html(data.result);
        form_parent.children("form").trigger("reset");
    }
    if (data.evaluation === true || data.evaluation === false) {
        // Get the symbol in meta
        var meta_img = form_parent.parent().find("div.task-meta > img");

        // Get the symbol in ToC
        var exercise_id = form_parent.parent().find("span.anchor-offset").attr("id");
        var toc_symbol = $('nav#toc li a[href="#' + exercise_id + '"]').next();

        var previous_status = meta_img.attr("class");
        if (previous_status !== "correct") {
            // TODO: "evaluation pending" icons
            if (typeof(data.next_instance) !== "undefined" && typeof(data.total_instances) !== "undefined") {
                if (data.next_instance === null) {
                    if (data.total_evaluation === "incorrect") {
                        meta_img.attr({
                            "src": "/static/courses/incorrect-96.png",
                            "class": "incorrect"
                        });
                        toc_symbol.attr({
                            "src": "/static/courses/incorrect-16.png",
                        });
                    } else if (data.total_evaluation === "correct") {
                        meta_img.attr({
                            "src": "/static/courses/correct-96.png",
                            "class": "correct"
                        });
                        toc_symbol.attr({
                            "src": "/static/courses/correct-16.png",
                        });
                        let eval_group = "embedded_page__evaluation_group";
                        if (eval_group != "") {
                            credit_eval_group(eval_group);
                        }
                    }
                }
            } else {
                if (data.evaluation === false) {
                    meta_img.attr({
                        "src": "/static/courses/incorrect-96.png",
                        "class": "incorrect"
                    });
                    toc_symbol.attr({
                        "src": "/static/courses/incorrect-16.png",
                    });
                } else if (data.evaluation === true) {
                    meta_img.attr({
                        "src": "/static/courses/correct-96.png",
                        "class": "correct"
                    });
                    toc_symbol.attr({
                        "src": "/static/courses/correct-16.png",
                    });
                    let eval_group = "embedded_page__evaluation_group";
                    if (eval_group != "") {
                        credit_eval_group(eval_group);
                    }
                }
            }
        }
        
        // Update the progress bar in ToC
        update_progress_bar();
    }
    if (data.errors) {
        /*
        let all_errors = "";
        for (let error of data.errors) {
            let error_text = "<li>" + error + "</li>\n";
            all_errors += error_text;
        }
        all_errors += "\n";
        */
        let all_errors = data.errors;
        error_div.html(all_errors);
        error_div.css("display", "block");
        form_parent.children("form").trigger("reset");
    }
    if (data.answer_count_str) {
        form_parent.parent().find('div.task-meta > div > a.user-answers-link').html(data.answer_count_str);
    }
    if (data.hints && data.evaluation === false) {
        let all_hints = "<ul>\n";
        for (let hint of data.hints) {
            let hint_text = "<li>" + hint + "</li>\n";
            all_hints += hint_text;
        }
        all_hints += "\n";
        hints_div.find('div.hints-list').html(all_hints);
        hints_div.css("display", "block");
    }
    else {
        hints_div.find('div.hints-list').html("");
        hints_div.css("display", "none");
    }
    
    // clean up old highlights
    $('section.content mark.hint-active').attr({'class': 'hint-inactive'}); 
    
    if (data.triggers) {
        /* TODO: For each triggered hint that's not currently on the screen:
           - display a pink clickable arrow on the upper/lower section of screen
             that automatically scrolls the page to the triggered hint when
             clicked on; also disappears after that
           - set the CSS class to an intermediate value with the borders; only
             start the animation when the hint becomes visible
         */
        //console.log(data.triggers);
        for (let hint_id of data.triggers) {
            let hint_text = $('section.content').find('#hint-id-' + hint_id);
            hint_text.attr({'class': 'hint-active'});
        }
        let panel = form_parent.children(".side-panel");
        let handle = form_parent.parent().find("a.faq-panel-link");
        faq.handle_triggers(panel, handle, data.triggers);
    }
    if (data.messages) {
        msgs_div.find('div.msgs-list').html(data.messages);
        msgs_div.css("display", "block");
    }
    if (data.comments) {
        comments_div.html(data.comments);
        comments_div.css("display", "block");
    }
    if (data.file_tabs) {
        file_result_div.html(data.file_tabs);
        file_result_div.css("display", "block");
    }
    if (data.next_instance || data.total_instances) {
        form_parent.parent().find("form.exercise-form :input").prop("disabled", true);
        let interaction_button = form_parent.parent().find('button.rt-interaction');
        interaction_button.prop("disabled", false);
        interaction_button.focus();
        if (data.next_instance === null && data.evaluation === false) {
            interaction_button.html(interaction_button.attr('data-start-over-text'));
        } else if (data.next_instance === null) {
            interaction_button.html(interaction_button.attr('data-start-over-text'));
        } else {
            interaction_button.html(interaction_button.attr('data-next-text'));
        }
    }

    if (data.progress) {
        form_parent.parent().find("span.rt-progress-tag").html(data.progress);
    }

    if (data.metadata) {
        let current = data.metadata.current;
        let total = data.metadata.total;
        if (typeof(current) !== "undefined" && typeof(total) !== "undefined") {
            result_div.html('<progress value="' + current + '" max="' + total +
                            '" title="' + current + '/' + total + '">' + current +
                            '/' + total + '</progress>');
        }
    }
    if (data.redirect) {
        var context = result_div.parent();
        poll_progress(data.redirect, context);
    }
    result_div.css("display", "block");
}

function exercise_error(status, type, error_div, form_parent) {
    var error_str = "An error occured while sending the answer.<br>";
    status = status.charAt(0).toUpperCase() + status.slice(1);
    if (type) {
        error_str += status + ": " + type;
    } else {
        error_str += status;
    }
    error_div.html(error_str);
    error_div.css("display", "block");
}

// http://techoctave.com/c7/posts/60-simple-long-polling-example-with-javascript-and-jquery
function poll_progress(url, context) {
    // TODO: End polling after a timeout
    setTimeout(function() {
        $.ajax({
            url: url,
            context: context,
            success: function(data, text_status, jqxhr_obj) {
                var result_div = $(this).children("div.result");
                var error_div = $(this).children("div.error");
                exercise_success(data, result_div, error_div, $(this));
            },
            error: function(xhr, status, type) {
                var error_div = $(this).children("div.error");
                exercise_error(status, type, error_div, $(this));
            }
        });
    }, 100);
}

// TODO: WebSockets – migrate to Django Channels

// http://stackoverflow.com/questions/7335780/how-to-post-a-django-form-with-ajax-jquery
// http://stackoverflow.com/questions/9622901/how-to-upload-a-file-using-jquery-ajax-and-formdata
// http://portfolio.planetjon.ca/2014/01/26/submit-file-input-via-ajax-jquery-easy-way/
function add_exercise_form_callbacks() {
    var exercise_forms = $('form.exercise-form');
    exercise_forms.each(function() {
        var form = $(this);

        form.submit(function(event) {
            event.preventDefault();

            var form_parent = form.parent();

            var result_div = form_parent.children("div.result");
            result_div.css("display", "none");
            var error_div = form_parent.children("div.error");
            error_div.css("display", "none");
            
            var submit_element = form_parent.find(":submit");
            submit_element.prop("disabled", true);

            // TODO: Use xhr and progressevent to measure upload progress

            $.ajax({
                type: form.attr('method'),
                url: form.attr('action'),
                // data: form.serialize(), // This doesn't work for files with jQuery
                data: new FormData(form[0]), // Use this instead
                processData: false, // And this
                contentType: false, // And this
                dataType: 'json',
                success: function(data, text_status, jqxhr_obj) {
                    submit_element.prop("disabled", false);
                    exercise_success(data, result_div, error_div, form_parent);
                },
                error: function(xhr, status, type) {
                    submit_element.prop("disabled", false);
                    exercise_error(status, type, error_div, form_parent);
                }
            });
        });
    });
}

function start_repeated_template_session(e) {
    let button = $(e.target);
    let exercise = button.parent().parent();
    //console.log(exercise);
    //let csrf_token = exercise.find("form > input[name=csrfmiddlewaretoken]");
    let rendered_template = exercise.find("div.repeated-template");
    let progress = exercise.find("span.rt-progress-tag");
    rendered_template.html('');
    var hints_div = exercise.children("div.question").children("div.hints");
    //console.log(hints_div);
    hints_div.find('div.hints-list').html("");
    hints_div.css("display", "none");

    $.ajax({
        type: 'GET',
        url: button.attr("data-url"),
        success: function(data, text_status, jqxhr_obj) {
            //console.log(data);
            if (data.rendered_template) {
                rendered_template.html(data.rendered_template);
                progress.html(data.progress);
            }
            if (data.redirect) {
                setTimeout(function() {
                    start_repeated_template_session(e);
                }, 1000);
            }
        },
        error: function(xhr, status, type) {
            console.log(status);
        }
    });

    let input_element = exercise.find("form :input");
    input_element.prop("disabled", false);
    input_element[1].focus();
    $(input_element[1]).val("");
    button.prop("disabled", true);
}

function credit_eval_group(eval_group) {
    $("div.task-meta[data-eval-group='" + eval_group + "'] img").each(function () {
        if (!$(this).hasClass("correct")) {
            $(this).attr({
                "src": "/static/courses/credited-96.png",
                "class": "credited"
            });
        }
    });
}