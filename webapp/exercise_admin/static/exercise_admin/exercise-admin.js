/* If the exercise page content is empty when the script loads, add a title
   automatically. */
var content_untouched = false;
var content_input;
var page_title_elem;
var breadcrumb_elem;

function close_popup(popup) {
    popup.css({"opacity":"0", "pointer-events":"none"});
}

function close_popup_and_add_questions() {
    var target_tbody = $("#feedback-question-table tbody");
    $("#add-feedback-table > tbody > tr").each(function(index) {
        if ($(this).find("input.feedback-question-checkbox:checked").length > 0) {
            var question = $(this).find("label.feedback-question-label").text();
            var type = $(this).children("td.type-cell").text();
            var tr = $('<tr>');
            var td_delete = $('<td class="delete-cell">');
            var title_text = "Deletes the relation between the feedback question and the exercise";
            tr.append('<td class="question-cell">' + question + '</td>');
            tr.append('<td class="type-cell">' + type + '</td>');
            td_delete.append('<button class="delete-button" title="' + title_text + '" onclick="delete_feedback_from_table(this);">x</button>');
            tr.append(td_delete);
            target_tbody.append(tr);
        }
    });
    close_popup($("#add-feedback-popup"));
}

$(document).ready(function() {
    content_input = $('#exercise-page-content');
    page_title_elem = $('title');
    breadcrumb_elem = $('#exercise-name-breadcrumb');
    var content_html = content_input.html();
    if (content_html === '' || content_html === undefined) {
        content_untouched = true;
    }
    $('div.feedback-table-div').slimScroll({
        height: '225px'
    });
    $('.popup').click(function() {
        close_popup($(this));
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

function test_name_changed(e) {
    var input_id = e.target.id;
    var split_id = input_id.split("-");
    var new_name = e.target.value;

    $('#test-' + split_id[1]).html(new_name);
}

function stage_name_changed(e) {
    var input_id = e.target.id;
    var split_id = input_id.split("-");
    var new_name = e.target.value;

    $('#stage-' + split_id[1]).html(new_name);
}

function command_name_changed(e) {
    var input_id = e.target.id;
    var split_id = input_id.split("-");
    var new_name = e.target.value;

    $('#command-' + split_id[1]).html(new_name);
}

function add_feedback_choice() {
    var MAX_CHOICES = 99;
    var choices_div = $('#feedback-choices');
    var label_n = choices_div.children().length + 1;
    choices_div.append('<label class="feedback-choice-label" for="feedback-choice-' + label_n + '">');
    var new_label = choices_div.children().last();
    new_label.append('<span class="feedback-choice-span">Choice ' + label_n + ':</span>');
    new_label.append('<input type="text" id="feedback-choice-' + label_n + '" class="feedback-choice">');
    new_label.append('<button class="delete-button" title="Deletes an answer choice of a feedback question">x</button>');
    if (label_n === MAX_CHOICES) {
        $("#add-feedback-choice").attr("disabled", true);
    } else {
        $("#add-feedback-choice").attr("disabled", false);
    }
}

function handle_feedback_type_selection(select) {
    var option = select.options[select.selectedIndex];
    var choices_div = $('#feedback-choices');
    var add_choice_button = $('#add-feedback-choice');
    var add_item_buttons = $('div.popup button.add-item');
    
    if (option.value === "multichoice") {
        choices_div.css({"display": "block"});
        add_choice_button.css({"display": "inline-block"});
        add_item_buttons.css({"margin-top": "10px"});
        add_feedback_choice();
    } else {
        choices_div.hide();
        choices_div.empty();
        add_choice_button.hide();
        add_item_buttons.css({"margin-top": "0px"});
    }
}

function show_add_feedback_question_popup(event, url) {
    event.preventDefault();

    $.get(url, function(data, textStatus, jqXHR) {
        var questions = [];
        $('#feedback-question-table tbody tr').each(function() {
            questions.push($(this).find("td:first").html());   
        });
        var tbody = $("#add-feedback-table > tbody");
        var popup = $("#add-feedback-popup");
        var error_span = $("#add-feedback-popup-error");
        var result = data.result;
        var error = data.error;

        if (error) {
            error_span.text(error);
            error_span.css({"display" : "inline-block"});
            return;
        } else {
            error_span.empty();
            error_span.hide();
        }   
        
        tbody.empty();
        $.each(result, function() {
            var question = this.question;
            if ($.inArray(question, questions) > -1) {
                return;
            }
            var id = this.id;
            var type = this.type;
            var tr = $('<tr>');
            var td_question = $('<td class="question-cell">');
            td_question.append('<input type="checkbox" id="fb-question-checkbox-' + id + '" class="feedback-question-checkbox">');
            td_question.append('<label for="fb-question-checkbox-' + id + '" class="feedback-question-label">' + question + '</label>');
            tr.append(td_question);
            tr.append('<td class="type-cell">' + type + '</td>');
            tbody.append(tr)
        });
        $('#feedback-choices').empty();
        handle_feedback_type_selection($("#feedback-type-select")[0]);
        popup.css({"opacity": "1", "pointer-events": "auto"});
    });
}

function delete_feedback_from_table(button) {
    $(button).parent().parent().remove();
}

function show_stagecmd_information(event) {
    var clicked_id = event.target.id;
    var split_id = clicked_id.split("-");
    var clicked_type = split_id[0];
    var clicked_number = split_id[1];
    $('div.selection-information').hide();
    $('#' + clicked_type + '-information-' + clicked_number).show() 
}

function submit_main_form(e) {
    e.preventDefault();
    console.log("User requested form submit.");
    
    var form = $('#main-form');

    // TODO: Calculate the implicit ordinal_numbers for stages and commands

    
    var form_type = form.attr('method');
    var form_url = form.attr('action');

    console.log("Method: " + form_type + ", URL: " + form_url);
    
    var form_data = new FormData(form[0]);

    console.log("Serialized form data:");
    console.log(form_data);

    console.log("Submitting the form...");
    $.ajax({
        type: form_type,
        url: form_url,
        data: form_data,
        processData: false,
        contentType: false,
        dataType: 'json',
        success: function(data, text_status, jqxhr_obj) {},
        error: function(xhr, status, type) {}
    });
}
