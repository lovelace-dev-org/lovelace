/* If the exercise page content is empty when the script loads, add a title
   automatically. */
var content_untouched = false;
$(document).ready(function() {
    var content_input = $('#exercise-page-content');
    var content_html = content_input.html();
    if (content_html === '' || content_html === undefined) {
        content_untouched = true;
    }
});

function exercise_name_changed(e) {
    var page_title_elem = $('title');
    var breadcrumb_elem = $('#exercise-name-breadcrumb');
    var new_name = e.target.value;

    /* TODO: 'Add' instead of 'Edit' when adding a new page */
    page_title_elem.html('Edit | ' + new_name);
    breadcrumb_elem.html(new_name);

    if (content_untouched === true) {
        var content_input = $('#exercise-page-content');
        content_input.html('== ' + new_name + ' ==\n\n')
    }
}

function exercise_page_content_changed(e) {
    content_untouched = false;
}
