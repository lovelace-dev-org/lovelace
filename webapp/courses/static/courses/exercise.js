// http://stackoverflow.com/questions/7335780/how-to-post-a-django-form-with-ajax-jquery
// http://stackoverflow.com/questions/9622901/how-to-upload-a-file-using-jquery-ajax-and-formdata
// http://portfolio.planetjon.ca/2014/01/26/submit-file-input-via-ajax-jquery-easy-way/
function add_exercise_form_callbacks() {
    var exercise_forms = $('form.exercise-form');
    exercise_forms.each(function() {
        var form = $(this);

        form.submit(function(event) {
            event.preventDefault();

            var result_div = form.parent().children("div.result");
            result_div.css("display", "none");
            var error_div = form.parent().children("div.error");
            error_div.css("display", "none");

            $.ajax({
                type: form.attr('method'),
                url: form.attr('action'),
                // data: form.serialize(), // This doesn't work for files with jQuery
                data: new FormData(form[0]), // Use this instead
                processData: false, // And this
                contentType: false, // And this
                success: function(data) {
                    result_div.html(data);
                    result_div.css("display", "block");
                },
                error: function(xhr, status, type) {
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
            });
        });
    });
}
