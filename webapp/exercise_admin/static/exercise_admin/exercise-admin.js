/* If the exercise page content is empty when the script loads, add a title
   automatically. */
var content_untouched = false;
var content_input;
var page_title_elem;
var breadcrumb_elem;

$(document).ready(function() {
    content_input = $('#exercise-page-content');
    page_title_elem = $('title');
    breadcrumb_elem = $('#exercise-name-breadcrumb');
    var content_html = content_input.html();
    if (content_html === '' || content_html === undefined) {
        content_untouched = true;
    }
    $('div#feedback-table-div').slimScroll({
        height: '225px'
    });
    $('.popup').click(function() {
        $(this).css({"opacity":"0", "pointer-events":"none"});
    });
    $('.popup > div').click(function(event) {
        event.stopPropagation();
    });
});

function exercise_name_changed(e) {
    var new_name = e.target.value;

    /* TODO: 'Add' instead of 'Edit' when adding a new page */
    page_title_elem.html('Edit | ' + new_name);
    breadcrumb_elem.html(new_name);

    if (content_untouched === true) {
        content_input.html('== ' + new_name + ' ==\n\n')
    }
}

function exercise_page_content_changed(e) {
    content_untouched = false;
}

function show_add_feedback_question_view(event, url) {
    event.preventDefault();

    $.get(url, function(data, textStatus, jqXHR) {
        var add_fb_question_div = $('div#add-feedback-question-view');
        add_fb_question_div.html(data);
        var popup = add_fb_question_div.parent();
        popup.css({"opacity": "1", "pointer-events": "auto"});
    });
}

function add_multichoice_feedback_answer() {
    var answers_div = $('#multichoice-feedback-answers');
    var label_n = answers_div.children().length + 1;
    answers_div.append('<label class="feedback-answer-label" for="multichoice-feedback-answer-' + label_n + '">');
    var new_label = answers_div.children().last();
    new_label.append('<span class="feedback-answer-span">Answer ' + label_n + ':</span>');
    new_label.append('<input type="text" id="multichoice-feedback-answer-' + label_n + '" class="multichoice-feedback-answer">');
}

function handle_feedback_type_selection(select) {
    var option = select.options[select.selectedIndex];
    var answers_div = $('#multichoice-feedback-answers');
    var add_answer_button = $('#add-feedback-answer');
    var add_item_buttons = $('div.popup button.add-item');
    
    if (option.value === "multichoice") {
        answers_div.css({"display": "block"});
        add_answer_button.css({"display": "inline-block"});
        add_item_buttons.css({"margin-top": "10px"});
        add_multichoice_feedback_answer();
    } else {
        answers_div.hide();
        answers_div.empty();
        add_answer_button.hide();
        add_item_buttons.css({"margin-top": "0px"});
    }
}
