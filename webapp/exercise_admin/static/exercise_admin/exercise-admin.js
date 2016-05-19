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
    var TITLE_TEXT = "Deletes the relation between the feedback question and the exercise";
    var target_tbody = $("#feedback-question-table tbody");
    $("#add-feedback-table > tbody > tr").each(function(index) {
        if ($(this).find("input.feedback-question-checkbox:checked").length > 0) {
            var question = $(this).find("label.feedback-question-label").text();
            var type = $(this).children("td.type-cell").text();
            var tr = $('<tr>');
            var td_delete = $('<td class="delete-cell">');
            tr.append('<td class="question-cell">' + question + '</td>');
            tr.append('<td class="type-cell">' + type + '</td>');
            td_delete.append('<button class="delete-button" title="' + TITLE_TEXT + '" onclick="delete_feedback_from_table(this);">x</button>');
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
    $('input[type=text].exercise-tag-input').each(function () {
        change_tag_width(this);
        if (this.value === "") {
            remove_tag(this);
        }
    });
});

function highlight_parent_li(input_elem) {
    var input = $(input_elem);
    var parent = input.parent();
    var hilight_class = 'exercise-tag-input-hilighted';
    
    parent.toggleClass(hilight_class, true);
    input.focusout(function() {
        if (input.val() === '') {
            remove_tag(input[0]);
        } else if (!parent.is(':hover')) {
            parent.toggleClass(hilight_class, false);
        }
    });
    parent.hover(function() {
        parent.toggleClass(hilight_class, true);
    }, function() {
        if (!input.is(':focus')) {
            parent.toggleClass(hilight_class, false);
        }
    });
}

function change_tag_width(input_elem) {
    var CHAR_WIDTH = 9;
    var MAX_FITTING_LENGTH = 4;
    var input = $(input_elem);
    var val_len = input.val().length;
    
    if (val_len > MAX_FITTING_LENGTH) {
        input.width((input_elem.value.length * CHAR_WIDTH) + 'px');
    } else {
        input.width(input.css('min-width'));
    }
}

function add_tag() {
    var ul = $('ul.exercise-tags');
    var li = $('<li class="exercise-tag">');
    var tag_n = ul.children().length + 1;

    li.append('<input type="text" id="' + tag_n + '-tag" class="exercise-tag-input" name="exercise_tag_' + tag_n +
              '" value="?" maxlength="32" onfocus="highlight_parent_li(this);" oninput="change_tag_width(this);">');
    li.append('<button type="button" class="delete-button" onclick="$(this).parent().remove();">x</button>');
    ul.append(li);
}

function remove_tag(tag_elem) {
    var tag_values = [];
    var li = $(tag_elem).parent();
    var ul = li.parent();
    var next_lis = li.nextAll();

    next_lis.each(function() {
        tag_values.push($(this).find("input[type=text].exercise-tag-input").val());
    });

    li.remove();
    next_lis.remove();
    $.each(tag_values, function(index, value) {
        add_tag();
        ul.children().last().find("input[type=text].exercise-tag-input").val(value);
    });
}

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

function add_feedback_choice(id_prefix, container_div_id, choices_div_id, choice_val) {
    var TITLE_TEXT = "Deletes an answer choice of a feedback question";

    var choice_container_div = $('#' + container_div_id);
    var choices_div = $('#' + choices_div_id);
    var label_n = choices_div.children().length + 1;
    var choice_div = $('<div id="' + id_prefix + '-div-' + label_n + '" class="feedback-choice-div">');
    var new_label = $('<label class="feedback-choice-label" for="' + id_prefix + '-' + label_n + '">');
    var delete_params = [id_prefix, container_div_id, choices_div_id, label_n].join("', '")
    if (typeof choice_val === "undefined") {
        choice_val = "";
    }
    
    new_label.append('<span class="feedback-choice-span">Choice ' + label_n + ':</span>');
    if (label_n <= 2) {  
        new_label.append('<input type="text" id="' + id_prefix + '-' + label_n + '" class="feedback-choice"' +
                         'name="choice_field_' + label_n + '" value="' + choice_val + '" required>');
    } else {
        new_label.append('<input type="text" id="' + id_prefix + '-' + label_n + '" class="feedback-choice"' +
                         'name="choice_field_' + label_n + '" value="' + choice_val + '">');
        new_label.append('<button type="button" class="delete-button" title="' + TITLE_TEXT +
                         '" onclick="delete_feedback_choice(\'' + delete_params + '\');">x</button>');
    }
    
    choice_div.append(new_label);
    choice_div.append('<div id="' + id_prefix + '-field-' + label_n + '-error" class="admin-error"></div>');
    choices_div.append(choice_div);

    console.log(choices_div);
    var max_height = choices_div.css('max-height');
    if (choice_container_div.height() + 'px' === max_height) {
        choices_div.slimScroll({
            height: max_height
        });
    } else {
        choices_div.slimScroll({
            destroy: true
        });
    }
}

function add_choice_to_selected_feedback() {
    var choices_div_id = $('#feedback-choice-container > div.feedback-choices:visible').attr('id');
    add_feedback_choice('feedback-choice', 'feedback-choice-container', choices_div_id);
}

function delete_feedback_choice(id_prefix, container_div_id, choices_div_id, label_n) {
    var choice_container_div = $('#' + container_div_id);
    var choices_div = $('#' + choices_div_id);
    var choice_div = $('#' + id_prefix + '-div-' + label_n);
    var total_height = 0;
    var max_height = parseFloat(choices_div.css('max-height').replace("px", ""));
    var next_choices = choice_div.nextAll();
    var choice_values = [];

    next_choices.each(function() {
        choice_values.push($(this).find("input[type=text].feedback-choice").val());
    });

    choice_div.remove();
    next_choices.remove();
    $.each(choice_values, function(index, value) {
        add_feedback_choice(id_prefix, container_div_id, choices_div_id);
        choices_div.children().last().find("input[type=text].feedback-choice").val(value);
    });
    
    $("div.feedback-choice-div").each(function() {
        total_height += $(this).height();
    });
    if (total_height < max_height) {
        choices_div.slimScroll({
            destroy: true
        });
        choice_container_div.height(total_height);
        choices_div.height(total_height);
        choice_container_div.css({"height" : "auto"});
        choices_div.css({"height" : "auto"});
    }
}

function handle_feedback_type_selection(select) {
    var CHOICE_ID_PREFIX = 'new-feedback-choice';
    var CONTAINER_DIV_ID = 'new-feedback-choice-container';
    var CHOICES_DIV_ID = 'new-feedback-choices';
    
    var option = select.options[select.selectedIndex];
    var choice_container_div = $('#' + CONTAINER_DIV_ID);
    var choices_div = $('#' + CHOICES_DIV_ID);
    var add_choice_button = $('#add-new-feedback-choice');
    
    if (option.value === "MULTIPLE_CHOICE_FEEDBACK") {
        choice_container_div.css({"display": "block"});
        add_choice_button.css({"display": "inline-block"});
        add_feedback_choice(CHOICE_ID_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID);
        add_feedback_choice(CHOICE_ID_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID);
    } else {
        choice_container_div.hide();
        choices_div.empty();
        add_choice_button.hide();
    }
}

function select_all_feedback_questions(select) {
    $("td.question-cell > input[type=checkbox].feedback-question-checkbox").prop("checked", select);
}

function handle_feedback_edit_click(question_id) {
    var choice_container_div = $("#feedback-choice-container");
    var add_choice_button = $("#add-feedback-choice");
    var choices_div = $("#feedback-choices-" + question_id);
    
    $("#edit-feedback-div").css({"display" : "block"});
    $("#create-feedback-div").hide();
    $("#edit-feedback-question-inputs > div").hide();
    $("#feedback-question-input-div-" + question_id).css({"display" : "block"});
    if (choices_div.length > 0) {
        var all_choices_divs = $("#feedback-choice-container div.feedback-choices");
        var max_height = choices_div.css('max-height');

        choice_container_div.css({"display" : "block"});
        all_choices_divs.slimScroll({
            destroy: true
        });
        all_choices_divs.hide();
        choices_div.css({"display" : "block"});
        if (choice_container_div.height() + 'px' === max_height) {
            choices_div.slimScroll({
                height: max_height
            });
        }
        add_choice_button.css({"display" : "inline-block"});
    } else {
        choice_container_div.hide();
        add_choice_button.hide();
    }
}

function close_edit_feedback_menu() {
    $("#edit-feedback-div").hide();
    $("#create-feedback-div").css({"display" : "block"});
}

function add_feedback_choices_to_popup(question_id, choices) {
    var CHOICES_ID = 'feedback-choice-' + question_id;
    var CONTAINER_DIV_ID = 'feedback-choice-container';
    var CHOICES_DIV_ID = 'feedback-choices-' + question_id;

    var choice_container_div = $('#' + CONTAINER_DIV_ID);
    choice_container_div.append($('<div id="' + CHOICES_DIV_ID + '" class="feedback-choices">'));
    
    $.each(choices, function(index, choice) {
        add_feedback_choice(CHOICES_ID, CONTAINER_DIV_ID, CHOICES_DIV_ID, choice);
    });
}

function add_feedback_question_to_popup(question, id, type, choices) {
    var tr = $('<tr>');
    var td_question = $('<td class="question-cell">');
    var td_type = $('<td class="type-cell">' + type + '</td>');
    var td_edit = $('<td class="edit-cell">');
    var inputs_div = $("#edit-feedback-question-inputs");
    var input_div = $('<div id="feedback-question-input-div-' + id + '">');
    var label = $('<label class="feedback-question-input-label" for="feedback-question-' + id + '">');
    
    td_question.append('<input type="checkbox" id="fb-question-checkbox-' + id + '" class="feedback-question-checkbox">');
    td_question.append('<label for="fb-question-checkbox-' + id + '" class="feedback-question-label">' + question + '</label>');
    td_edit.append('<button type="button" class="edit-button" onclick="handle_feedback_edit_click(' + id + ');"></button>');
    tr.append(td_question);
    tr.append(td_type);
    tr.append(td_edit);
    $("#add-feedback-table > tbody").append(tr);

    label.append('<span class="feedback-question-span">Feedback question:</span>');
    label.append('<input type="text" id="feedback-question-' + id + '" class="feedback-question-input" name="question_field_' +
                 id + '" maxlength="100" value="' + question + '" required>');
    input_div.append(label);
    inputs_div.append(input_div);
    if (choices.length > 0) {
        add_feedback_choices_to_popup(id, choices);
    }
}

function show_add_feedback_question_popup(event, url) {
    event.preventDefault();

    $.get(url, function(data, textStatus, jqXHR) {
        var questions = [];
        $('#feedback-question-table tbody tr').each(function() {
            questions.push($(this).find("td:first").html());   
        });
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

        $("div.popup div.admin-error").hide();
        $("#add-feedback-table > tbody").empty();
        $("#fb-question-checkbox-all").prop("checked", false);
        $("#feedback-choice-container").empty();
        $("#edit-feedback-question-inputs").empty();
        $("#edit-feedback-div").hide();
        $("#create-feedback-div").css({"display" : "block"});
        
        $.each(result, function() {
            var question = this.question;
            if ($.inArray(question, questions) > -1) {
                return;
            }
            add_feedback_question_to_popup(question, this.id, this.type, this.choices);
        });
        $('#new-feedback-choices').empty();
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
    console.log("User requested main form submit.");
    
    var form = $('#main-form');

    // Get the hierarchy of stages and commands for the calculation of implicit
    // ordinal_numbers at the form validation
    var tests = [];
    $('#test-tabs > ol > li').each(function(x) {
        var current_href = $(this).children('a').attr('href');
        if (current_href !== undefined) {
            var current_id = current_href.split('-')[2];
            tests.push(current_id);
        }
    });
    var order_hierarchy = {stages_of_tests: {}, commands_of_stages: {}};
    for (let test_id of tests) {
        var stage_order;
        
        $('#stages-sortable-' + test_id).each(function(x) {
            stage_order = $(this).sortable("toArray", options={attribute: 'data-stage-id'});
            order_hierarchy.stages_of_tests[test_id] = stage_order;
            
            for (let stage_id of stage_order) {
                var command_order;
                $('#commands-sortable-' + test_id + '-' + stage_id).each(function(y) {
                    command_order = $(this).sortable("toArray", options={attribute: 'data-command-id'});
                });
                order_hierarchy.commands_of_stages[stage_id] = command_order;
            }
        });
    }
    console.log(order_hierarchy);
    
    var form_type = form.attr('method');
    var form_url = form.attr('action');

    console.log("Method: " + form_type + ", URL: " + form_url);

    var form_data = new FormData(form[0]);
    form_data.append("order_hierarchy", JSON.stringify(order_hierarchy));

    console.log("Serialized form data:");
    for (var [key, value] of form_data.entries()) { 
        console.log(key, value);
    }

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

var cmd_enum = 1;

function add_command(test_id, stage_id) {
    var new_id = 'new' + cmd_enum;
    var cmd_list = $("#commands-sortable-" + test_id + "-" + stage_id);
    var cmd_ordnum = cmd_list.children().length + 1;
    var stage_ordnum = 666;
    
    // Create the new command to the list
    cmd_list.append(
        $('<li class="ui-state-default" data-command-id="' + new_id + '">' +
              '<span onClick="show_stagecmd_information(event);" id="command-' + new_id + '" class="clickable-commandline"></span>' +
          '</li>')
    );

    // Create the information box to the right side of the list
    var new_cmd_info = $('#command-information-SAMPLE_COMMAND_ID').clone().attr('id', 'command-information-' + new_id);
    new_cmd_info.html(function(index, html) {
        return html.replace(/SAMPLE_COMMAND_ID/g, 'new'+cmd_enum).replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum).
            replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, cmd_ordnum);
    });
    $("#selection-information-container").append(new_cmd_info);
    
    cmd_enum++;
}

function create_feedback_form_success(data, text_status, jqxhr_obj) {
    if (data.error) {
        var sep = "<br>";
        $.each(data.error, function(err_source, err_msg) { 
            if (err_source === "question_field") {
                var error_div = $("#new-feedback-question-error");
            } else if (err_source === "type_field") {
                var error_div = $("#feedback-type-select-error");
            } else if (err_source.startsWith("choice_field")) {
                console.log("#" + err_source.replace("_", "-") + "-error");
                var error_div = $("#" + err_source.replace(new RegExp("_", "g"), "-") + "-error");
            } else {
                var error_div = $("#create-feedback-error");
            }
            error_div.html(err_msg.join(sep));
            error_div.css("display", "block");
        });
    } else if (data.result) {
        add_feedback_question_to_popup(data.result.question, data.result.id, data.result.type, data.result.choices);
        console.log("hep");
        $("div.popup div.admin-error").hide();
        $("#feedback-question-new").val("");
        $('#new-feedback-choices').empty();
        handle_feedback_type_selection($("#feedback-type-select")[0]);
    }
}

function create_feedback_form_error(xhr, status, type) {
    var error_span = $("#create-feedback-error");
    var error_str = "An error occured while sending the form:";
    status = status.charAt(0).toUpperCase() + status.slice(1);
    if (type) {
        error_str += status + ": " + type;
    } else {
        error_str += status;
    }
    error_span.html(error_str);
    error_span.css("display", "block");
}

function submit_create_feedback_form(e) {
    e.preventDefault();
    console.log("User requested create feedback form submit.");

    var form = $('#create-feedback-form');
    var form_type = form.attr('method');
    var form_url = form.attr('action');

    console.log("Method: " + form_type + ", URL: " + form_url);

    var form_data = new FormData(form[0]);

    console.log("Serialized form data:");
    for (var [key, value] of form_data.entries()) { 
        console.log(key, value);
    }

    console.log("Submitting the form...");
    $.ajax({
        type: form_type,
        url: form_url,
        data: form_data,
        processData: false,
        contentType: false,
        dataType: 'json',
        success: create_feedback_form_success,
        error: create_feedback_form_error
    });
}
