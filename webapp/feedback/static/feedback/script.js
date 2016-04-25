//http://jsfiddle.net/hungerpain/eK8X5/7/
function show_feedbacks(header_elem, expand_str, collapse_str, expand_img, collapse_img) {
    var header = $(header_elem);
    var span = header.children("span");
    var img = header.children("img");
    console.log(header);
    var feedbacks = header.next();
    console.log(feedbacks);
    
    feedbacks.slideToggle(500, function () {
        span.text(function () {
            return feedbacks.is(":visible") ? collapse_str : expand_str;
        });
        img.attr("src", feedbacks.is(":visible") ? collapse_img : expand_img);
    });
}

function select_choice(elem) {
     $(elem).closest("form").submit();
}

function select_stars(star_elem, star_num) {
    var stars = $(star_elem).parent().children("label");
    for (var i = 0; i < stars.length; i++) {
        var star = $(stars[i]);
        if (i >= star_num - 1) {
            star.addClass("star-filled");
            star.removeClass("star-outline");
        } else {
            star.addClass("star-outline");
            star.removeClass("star-filled");
        }
    }
    select_choice(star_elem);
}

function feedback_success(data, result_div, error_div, form_parent) {
    if (data.result) {
        result_div.html(data.result);
        result_div.css("display", "block");
    } else if (data.error) {
        error_div.html(data.error);
        error_div.css("display", "block");
    }
}

function feedback_error(status, type, error_div, form_parent) {
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

// http://stackoverflow.com/questions/7335780/how-to-post-a-django-form-with-ajax-jquery
// http://stackoverflow.com/questions/9622901/how-to-upload-a-file-using-jquery-ajax-and-formdata
// http://portfolio.planetjon.ca/2014/01/26/submit-file-input-via-ajax-jquery-easy-way/
function add_feedback_form_callbacks() {
    var feedback_forms = $('form.feedback-form');
    feedback_forms.each(function() {
        var form = $(this);

        form.submit(function(event) {
            event.preventDefault();

            var form_parent = form.parent();
            
            var result_div = form_parent.children("div.feedback-received");
            result_div.css("display", "none");
            var error_div = form_parent.children("div.feedback-error");
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
                    feedback_success(data, result_div, error_div, form_parent);
                },
                error: function(xhr, status, type) {
                    feedback_error(status, type, error_div, form_parent);
                }
            });
        });
    });
}
