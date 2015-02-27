function success_function(data, result_div, error_div, form_parent) {
    var hints_div = form_parent.children("div.hints");
    var comments_div = form_parent.children("div.comments");
    var file_result_div = form_parent.children("div.file-result");

    if (data.result) {
        result_div.html(data.result);
    }
    if (data.errors) {
        error_div.html(data.errors);
        error_div.css("display", "block");
    }
    if (data.hints) {
        hints_div.html(data.hints);
        hints_div.css("display", "block");
    }
    if (data.comments) {
        comments_div.html(data.comments);
        comments_div.css("display", "block");
    }
    if (data.file_tabs) {
        file_result_div.html(data.file_tabs);
        file_result_div.css("display", "block");
    }


    if (data.metadata) {
        var current = data.metadata.current;
        var total = data.metadata.total;
        // TODO: Progress bar
        result_div.html('<div>' + current + '/' + total + '</div>');
    }
    if (data.redirect) {
        var context = result_div.parent();
        poll_progress(data.redirect, context);
    }
    result_div.css("display", "block");
}

function error_function(status, type, error_div, form_parent) {
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
                success_function(data, result_div, error_div, $(this));
            },
            error: function(xhr, status, type) {
                var error_div = $(this).children("div.error");
                error_function(status, type, error_div, $(this));
            }
        });
    }, 500);
}

// TODO: WebSockets – maybe use Tornado as the backend?

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
                    success_function(data, result_div, error_div, form_parent);
                },
                error: function(xhr, status, type) {
                    error_function(status, type, error_div, form_parent);
                }
            });
        });
    });
}

