// http://stackoverflow.com/questions/7335780/how-to-post-a-django-form-with-ajax-jquery
// http://stackoverflow.com/questions/9622901/how-to-upload-a-file-using-jquery-ajax-and-formdata
// http://portfolio.planetjon.ca/2014/01/26/submit-file-input-via-ajax-jquery-easy-way/
function add_exercise_form_callbacks() {
    var exercise_forms = $('form.exercise-form');
    
    console.log("lisätään callbackit");

    exercise_forms.each(function() {
        var form = $(this);

        form.submit(function(event) {
            event.preventDefault();

            $.ajax({
                type: form.attr('method'),
                url: form.attr('action'),
                // data: form.serialize(), // This doesn't work for files with jQuery
                data: new FormData(form[0]), // Use this instead
                processData: false, // And this
                contentType: false, // And this
                success: function(data) {
                    result_div = form.parent().children("div.result");
                    
                    result_div.html(data);
                },
                error: function(data) {
                    error_div = form.parent().children("div.error");
                    error_div.html("XHR Error!");
                }
            });
        });
    });
}
