/* If the exercise page content is empty when the script loads, add a title
   automatically. */
var content_untouched = false;
var content_input;
var page_title_elem;
var breadcrumb_elem;

function close_popup(popup) {
    popup.css({"opacity":"0", "pointer-events":"none"});
}

function close_popup_and_add_questions(questions) {
    var TITLE_TEXT = "Deletes the relation between the feedback question and the exercise";
    var target_tbody = $("#feedback-question-table tbody");
    $("#add-feedback-table > tbody input.feedback-question-checkbox:checked").each(function(index) {
        var id = $(this).attr("data-question-id");
        var question = $("#feedback-question-" + id).val();
        var type = "";
        var in_table = false;
        var not_saved = true;
        
        $.each(questions, function(index, db_question) {
            console.log(questions);
            if (db_question.question === question) {
                id = "" + db_question.id;
                type = db_question.readable_type;
                not_saved = false;
                return false;
            }
        });
        if (not_saved) {
            return;
        }

        var tr = $('<tr data-question-id="' + id + '">');
        target_tbody.find("tr").each(function() {
            if ($(this).attr("data-question-id") === id) {
                tr = $(this);
                in_table = true;
                return false;
            }
        });
        if (in_table) {
            tr.children("td.question-cell").html(question);
        } else {
            var td_delete = $('<td class="delete-cell">');
            tr.append('<td class="question-cell">' + question + '</td>');
            tr.append('<td class="type-cell">' + type + '</td>');
            td_delete.append('<button class="delete-button" title="' + TITLE_TEXT + '" onclick="delete_table_row(this);">x</button>');
            tr.append(td_delete);
            target_tbody.append(tr);
        }
    });
    close_popup($("#edit-feedback-popup"));
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
    $('div.feedback-choices').slimScroll({
        height: '150px'
    });
    $('#edit-feedback-popup, #edit-instance-files-popup').click(function() {
        close_popup($(this));
    });
    $('section.included-files div.popup').click(function() {
        cancel_included_file_popup($(this), $(this).attr("data-file-id"));
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
    // Reset the translation selector
    $('#language-selector > option').each(function() {
        if (this.defaultSelected) {
            this.selected = true;
            return false;
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

var tag_enum = 1;

function add_tag() {
    var ul = $('ul.exercise-tags');
    var li = $('<li class="exercise-tag">');

    var new_tag = $('<input type="text" id="exercise-tag-new-' + tag_enum + '" class="exercise-tag-input" name="exercise_tag_' + tag_enum +
                    '" value="?" maxlength="32" onfocus="highlight_parent_li(this);" oninput="change_tag_width(this);">');
    var new_button = $('<button type="button" class="delete-button" onclick="remove_tag(this);">x</button>');
    li.append(new_tag);
    li.append(new_button);
    ul.append(li);
    tag_enum++;
}

function remove_tag(tag_elem) {
    var li = $(tag_elem).parent();
    li.remove();
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

var fb_choice_enum = 1;

function add_feedback_choice(id_prefix, name_prefix, container_div_id, choices_div_id, named, choice_val) {
    var TITLE_TEXT = "Deletes an answer choice of a feedback question";

    var choice_container_div = $('#' + container_div_id);
    var choices_div = $('#' + choices_div_id);
    var label_n = choices_div.children().length + 1;
    var choice_div = $('<div id="' + id_prefix + '-div-' + fb_choice_enum + '" class="feedback-choice-div">');
    var new_label = $('<label class="feedback-choice-label" for="' + id_prefix + '-' + fb_choice_enum + '">');
    var input = $('<input type="text" id="' + id_prefix + '-' + fb_choice_enum + '" class="feedback-choice">');

    new_label.append('<span class="feedback-choice-span">Choice ' + label_n + ':</span>');
    if (typeof choice_val !== "undefined") {
        input.val(choice_val);
    }
    if (named) {  
        input.attr("name", name_prefix + "_{" + fb_choice_enum + "}");
    } else if (label_n <= 2) {
        input.attr("oninput", "update_create_feedback_button_state();");
    }
    new_label.append(input);
    if (label_n > 2) {
        var delete_params = [id_prefix, fb_choice_enum].join("', '")
        new_label.append('<button type="button" class="delete-button" title="' + TITLE_TEXT +
                         '" onclick="delete_feedback_choice(\'' + delete_params + '\');">x</button>');
    }
    
    choice_div.append(new_label);
    choice_div.append('<div id="' + id_prefix + "-" + fb_choice_enum + '-error" class="admin-error"></div>');
    choices_div.append(choice_div);
    fb_choice_enum++;
}

function add_choice_to_selected_feedback() {
    var choices_div = $("#feedback-choice-container > div.feedback-choices:visible");
    var choices_div_id = choices_div.attr("id");
    var question_id = choices_div.attr("data-feedback-question-id");
    var choice_count = choices_div.children().length;
    add_feedback_choice("feedback-choice-" + question_id, "choice_field_[" + question_id + "]", "feedback-choice-container", choices_div_id, true);
}

function delete_feedback_choice(id_prefix, choice_enum) {
    $('#' + id_prefix + '-div-' + choice_enum).remove();
}

function handle_feedback_type_selection(select) {
    var CHOICE_ID_PREFIX = 'new-feedback-choice';
    var CHOICE_NAME_PREFIX = 'choice_field';
    var CONTAINER_DIV_ID = 'new-feedback-choice-container';
    var CHOICES_DIV_ID = 'new-feedback-choices';
    
    var option = select.options[select.selectedIndex];
    var choice_container_div = $('#' + CONTAINER_DIV_ID);
    var choices_div = $('#' + CHOICES_DIV_ID);
    var add_choice_button = $('#add-new-feedback-choice');
    
    if (option.value === "MULTIPLE_CHOICE_FEEDBACK") {
        choice_container_div.css({"display": "block"});
        add_choice_button.css({"display": "inline-block"});
        add_feedback_choice(CHOICE_ID_PREFIX, CHOICE_NAME_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID, false);
        add_feedback_choice(CHOICE_ID_PREFIX, CHOICE_NAME_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID, false);
    } else {
        choice_container_div.hide();
        choices_div.empty();
        add_choice_button.hide();
    }
}

function select_all_feedback_questions(select) {
    $("td.question-cell > input[type=checkbox].feedback-question-checkbox").prop("checked", select);
}

function show_feedback_question_edit_menu(question_id) {
    var MENU_TITLE = "Edit feedback question: "

    var feedback_choices_div = $("#feedback-choices");
    var add_choice_button = $("#add-feedback-choice");
    var choices_div = $("#feedback-choices-" + question_id);

    $("#edit-feedback-question-inputs > div").hide();
    $("#feedback-question-input-div-" + question_id).css({"display" : "block"});
    $("#edit-feedback-div").css({"display" : "block"});
    $("#create-feedback-div").hide();
    $("#edit-feedback-div-title").text(MENU_TITLE + $("#feedback-question-" + question_id + "-label").text());
    
    if (choices_div.length > 0) {
        var all_choices_divs = $("#feedback-choice-container div.feedback-choices");
        feedback_choices_div.css({"display" : "block"});
        all_choices_divs.hide();
        choices_div.css({"display" : "block"});
        add_choice_button.css({"display" : "inline-block"});
    } else {
        feedback_choices_div.hide();
        add_choice_button.hide();
    }
}

function close_edit_feedback_menu() {
    $("#edit-feedback-div").hide();
    $("#create-feedback-div").css({"display" : "block"});
}

function add_feedback_choices_to_popup(question_id, choices) {
    var CHOICE_ID_PREFIX = 'feedback-choice-' + question_id;
    var CHOICE_NAME_PREFIX = 'choice_field_[' + question_id + ']';
    var CONTAINER_DIV_ID = 'feedback-choice-container';
    var CHOICES_DIV_ID = 'feedback-choices-' + question_id;
    
    var choice_container_div = $('#' + CONTAINER_DIV_ID);
    var choices_div = $('<div id="' + CHOICES_DIV_ID + '" class="feedback-choices" data-feedback-question-id="' + question_id + '">');
    choice_container_div.append(choices_div);

    if (choices.length > 0) {
        $.each(choices, function(index, choice) {
            add_feedback_choice(CHOICE_ID_PREFIX, CHOICE_NAME_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID, true, choice);
        });
    } else {
        add_feedback_choice(CHOICE_ID_PREFIX, CHOICE_NAME_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID, true);
        add_feedback_choice(CHOICE_ID_PREFIX, CHOICE_NAME_PREFIX, CONTAINER_DIV_ID, CHOICES_DIV_ID, true);
    }
}

function add_feedback_question_to_popup(question, id, type, readable_type, choices, checked) {
    var tr = $('<tr>');
    var td_question = $('<td class="question-cell">');
    var td_type = $('<td class="type-cell">' + readable_type + '</td>');
    var td_edit = $('<td class="edit-cell">');
    var inputs_div = $("#edit-feedback-question-inputs");
    var input_div = $('<div id="feedback-question-input-div-' + id + '">');
    var label = $('<label class="feedback-question-input-label" for="feedback-question-' + id + '">');
    var checkbox = $('<input type="checkbox" id="fb-question-checkbox-' + id +
                     '" class="feedback-question-checkbox" data-question-id="' + id + '">');
    if (checked) {
        checkbox.prop("checked", true);
    }
    
    td_question.append(checkbox);
    td_question.append('<label id="feedback-question-' + id + '-label" for="fb-question-checkbox-' + id +
                       '" class="feedback-question-label">' + question + '</label>');
    td_edit.append('<button type="button" class="edit-button" onclick="show_feedback_question_edit_menu(\'' + id + '\');"></button>');
    tr.append(td_question);
    tr.append(td_type);
    tr.append(td_edit);
    $("#add-feedback-table > tbody").append(tr);

    label.append('<span class="feedback-question-span">Feedback question:</span>');
    label.append('<input type="text" id="feedback-question-' + id + '" class="feedback-question-input" name="question_field_[' +
                 id + ']" maxlength="100" value="' + question + '">');
    input_div.append(label);
    input_div.append($('<div id="feedback-question-' + id + '-error" class="admin-error">'));
    input_div.append('<input type="text" id="feedback-type-' + id + '" name="type_field_[' + id + ']" value="' + type + '" hidden readonly>');
    inputs_div.append(input_div);
    if (type === "MULTIPLE_CHOICE_FEEDBACK") {
        add_feedback_choices_to_popup(id, choices);
    }
}

function create_new_feedback_question_entry() {
    var question = $("#feedback-question-new").val();
    var type = $("#feedback-type-select").val();
    var readable_type = type.toLowerCase().replace(/_/g, " ");
    var choices = [];
    var choices_div = $("#new-feedback-choices");
    var choice_container_div = $("#new-feedback-choice-container");

    $("div.popup div.admin-error").hide();
    
    var duplicates = false;
    $("#create-feedback-div input[type=text].feedback-choice").each(function(index) {
        if (this.value != "" && choices.indexOf(this.value) > -1) {
            var choice_error_div = $("#new-feedback-choice-" + index + "-error");
            choice_error_div.text("Duplicate choice!");
            choice_error_div.css({"display" : "block"});
            duplicates = true;
        }
        choices.push(this.value);
    });

    var new_count = 0;
    var already_exists = false;
    $("#add-feedback-div label.feedback-question-label").each(function() {
        if ($(this).text() === question) {
            already_exists = true;
            return false;
        }
        if (this.id.indexOf("new") > -1) {
            new_count++;
        }
    });
    if (already_exists) {
        var feedback_error_div = $("#new-feedback-question-error");
        feedback_error_div.text("This feedback question already exists");
        feedback_error_div.css({"display" : "block"});
        return;
    }
    if (duplicates) {
        return;
    }
    
    $("#feedback-question-new").val("");
    choices_div.empty();
    handle_feedback_type_selection($("#feedback-type-select")[0]);
    add_feedback_question_to_popup(question, "new-" + (new_count + 1), type, readable_type, choices, true);
}

function update_create_feedback_button_state() {
    var button = $("#create-feedback-button");
    var question_val = $("#feedback-question-new").val();
    var choice1 = $("#new-feedback-choice-1");
    var choice2 = $("#new-feedback-choice-2");
    if (question_val === "" ||
        (choice1.length > 0 && choice1.val() === "") ||
        (choice2.length > 0 && choice2.val() === "")) {
        button.prop("disabled", true);
    } else {
        button.prop("disabled", false);
    }
}

function show_edit_feedback_questions_popup(event, url) {
    event.preventDefault();

    $.get(url, function(data, textStatus, jqXHR) {
        var questions = [];
        $('#feedback-question-table tbody tr').each(function() {
            questions.push($(this).find("td:first").html());   
        });
        var popup = $("#edit-feedback-popup");
        var error_span = $("#edit-feedback-popup-error");
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
                add_feedback_question_to_popup(question, this.id, this.type, this.readable_type, this.choices, true);
            } else {
                add_feedback_question_to_popup(question, this.id, this.type, this.readable_type, this.choices, false);
            }
        });
        $('#new-feedback-choices').empty();
        handle_feedback_type_selection($("#feedback-type-select")[0]);
        popup.css({"opacity": "1", "pointer-events": "auto"});
    });
}

function delete_table_row(button) {
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

function add_hint() {
    var hint_n = $("#hint-table tbody tr").length + 1;
    var tries_to_unlock = $('<input type="number" step="1" class="hint-tries-to-unlock-input" name="hint_tries_[new-' + hint_n +
                            ']" value="0">');
    var hint_content = $('<input type="text" class="hint-content-input" name="hint_content_[new-' + hint_n + ']" value="">');
    var td_tries_to_unlock = $('<td>');
    var td_hint_content = $('<td>');
    var tr = $('<tr>');
    td_tries_to_unlock.append(tries_to_unlock);
    td_hint_content.append(hint_content);
    tr.append(td_tries_to_unlock);
    tr.append(td_hint_content);
    $("#hint-table tbody").append(tr);
}

function update_included_file_ok_button_state(file_id) {
    var button = $("#included-file-ok-button-" + file_id);
    if ($("#included-file-" + file_id).val().length > 0 &&
        $("#included-file-default-name-" + file_id).val().length > 0 &&
        $("#included-file-name-" + file_id).val().length > 0 &&
        $("#included-file-chmod-" + file_id).val().length > 0 &&
        $("#included-file-description-" + file_id).val().length > 0) {
        button.prop("disabled", false);
    } else {
        button.prop("disabled", true);
    }
}

function show_edit_included_file_popup(file_id, purpose, chown, chgrp) {
    var popup = $("#edit-included-file-" + file_id);
    update_included_file_ok_button_state(file_id);
    $("#included-file-purpose-" + file_id).val(purpose);
    $("#included-file-chown-" + file_id).val(chown);
    $("#included-file-chgrp-" + file_id).val(chgrp);
    $("#file-chmod-error-" + file_id).hide();
    popup.css({"opacity": "1", "pointer-events": "auto"});
}

function confirm_included_file_popup(file_id) {
    var name = $("#included-file-name-" + file_id).val();
    var description = $("#included-file-description-" + file_id).val();
    var chmod = $("#included-file-chmod-" + file_id).val();
    var found = chmod.match(/^((r|-)(w|-)(x|-)){3}$/);

    if (found === null || found[0] != chmod) {
        var chmod_error_div = $("#file-chmod-error-" + file_id);
        chmod_error_div.text("File access mode was of incorrect format! Give 9 character, each either r, w, x or -!");
        chmod_error_div.css({"display": "block"});
        return;
    }

    if ($("#included-files-table tbody").find("#included-file-tr-" + file_id).length > 0) {
        var td_name = $("#included-file-td-name-" + file_id);
        var td_purpose = $("#included-file-td-purpose-" + file_id);
        var td_description = $("#included-file-td-description-" + file_id);
        
        td_name.html(name);
        td_purpose.html($("#included-file-purpose-" + file_id + " option:selected").text());
        td_description.html(description);
    } else {
        var default_name = $("#included-file-default-name-" + file_id).val();
        var purpose = $("#included-file-purpose-" + file_id).val();
        var purpose_display = $("#included-file-purpose-" + file_id + " option:selected").text();
        var chown = $("#included-file-chown-" + file_id).val();
        var chgrp = $("#included-file-chgrp-" + file_id).val();
        
        var tr = $("#included-file-tr-SAMPLE_ID").clone().attr('id', 'included-file-tr-' + file_id);
        tr.html(function(index, html) {
            return html.replace(/SAMPLE_ID/g, file_id).replace(/SAMPLE_NAME/g, name).replace(/SAMPLE_DESCRIPTION/g, description).
                replace(/SAMPLE_PURPOSE/g, purpose).replace(/SAMPLE_GET_PURPOSE_DISPLAY/g, purpose_display).
                replace(/SAMPLE_CHOWN_SETTINGS/g, chown).replace(/SAMPLE_CHGRP_SETTINGS/g, chgrp);
        });
        $("#edit-included-file-title-" + file_id).text("Edit included file: " + name);
        $("#included-files-table tbody").append(tr);
    }
    close_popup($("#edit-included-file-" + file_id));
}

function cancel_included_file_popup(popup, file_id) {
    if ($("#included-files-table tbody").find("#included-file-tr-" + file_id).length > 0) {
        close_popup(popup);
    } else {
        popup.remove();
    }
}

include_file_enum = 1;

function create_included_file_popup() {
    var id = "new-" + include_file_enum;
    var popup = $("#edit-included-file-SAMPLE_ID").clone().attr('id', 'edit-included-file-' + id);
    popup.html(function(index, html) {
        return html.replace(/SAMPLE_ID/g, id).replace(/SAMPLE_POPUP_TITLE/g, "Add included file").
            replace(/SAMPLE_DEFAULT_NAME/g, "").replace(/SAMPLE_DESCRIPTION/g, "").
            replace(/SAMPLE_NAME/g, "").replace(/SAMPLE_CHMOD_SETTINGS/g, "rw-rw-rw-");
    });
    popup.attr("data-file-id", id);
    $("#include-file-popups").append(popup);
    update_included_file_ok_button_state(id);
    $("#edit-included-file-" + id).click(function() {
        cancel_included_file_popup(popup, popup.attr("data-file-id"));
    });
    $("#edit-included-file-" + id + " > div").click(function(event) {
        event.stopPropagation();
    });
    popup.css({"opacity": "1", "pointer-events": "auto"});
    include_file_enum++;
}

instance_file_enum = 1;

function show_instance_file_edit_menu(file_id) {
    $("div.edit-instance-file").hide();
    $("div.link-instance-file").hide();
    $("#link-instance-file-divs").hide();
    $("#edit-instance-file-" + file_id).css({"display" : "block"});
    $("#edit-instance-file-divs").css({"display" : "block"});
}

function show_instance_file_edit_link_menu(file_id) {
    $("div.link-instance-file").hide();
    $("div.edit-instance-file").hide();
    $("#edit-instance-file-divs").hide();
    $("#link-instance-file-" + file_id).css({"display" : "block"});
    $("#link-instance-file-divs").css({"display" : "block"});
}

function close_instance_file_menu(file_id) {
    $("div.link-instance-file").hide();
    $("div.edit-instance-file").hide();
    $("#link-instance-file-divs").hide();
    $("#edit-instance-file-new-" + (instance_file_enum - 1)).css({"display" : "block"});
    $("#edit-instance-file-divs").css({"display" : "block"});
}

function update_instance_file_done_button_state(file_id) {
    var button = $("#done-button-" + file_id);
    if (button.attr("data-button-mode") === "done") {
        return;
    }
    
    if ($("#instance-file-" + file_id).val().length > 0 &&
        $("#instance-file-default-name-" + file_id).val().length > 0 &&
        $("#instance-file-description-" + file_id).val().length > 0) {
        button.prop("disabled", false);
    } else {
        button.prop("disabled", true);
    }
}

function update_link_done_button_state(file_id) {
    var button = $("#link-done-button-" + file_id);
    if (button.attr("data-button-mode") === "done") {
        return;
    }
    
    if ($("#instance-file-name-" + file_id).val().length > 0 &&
        $("#instance-file-chmod-" + file_id).val().length > 0) {
        button.prop("disabled", false);
    } else {
        button.prop("disabled", true);
    }
}

function add_create_instance_file_div() {
    var file_id = "new-" + instance_file_enum;
    var create_div = $("#edit-instance-file-SAMPLE_ID_CREATE").clone().attr('id', 'edit-instance-file-' + file_id);
    create_div.html(function(index, html) {
        return html.replace(/SAMPLE_ID_CREATE/g, file_id).replace(/SAMPLE_DEFAULT_NAME/g, "").
            replace(/SAMPLE_DESCRIPTION/g, "");
    });
    create_div.css({"display" : "block"});
    $("#edit-instance-file-divs").append(create_div);
    instance_file_enum++;
}

function add_instance_file_to_popup(file_id, default_name, description, link, checked) {
    if (checked) {
        var sample_id1 = "SAMPLE_ID_LINKED";
        var sample_id2 = "SAMPLE_ID";
        var chmod = link.chmod_settings;
        var name = link.name
        var edit_link_div = $("#link-instance-file-" + sample_id1).clone().attr('id', 'link-instance-file-' + file_id);
        edit_link_div.find("#instance-file-purpose-" + sample_id1).val(link.purpose);
        edit_link_div.find("#instance-file-chown-" + sample_id1).val(link.chown_settings);
        edit_link_div.find("#instance-file-chgrp-" + sample_id1).val(link.chgrp_settings);
    } else {
        var sample_id1 = "SAMPLE_ID";
        var sample_id2 = "SAMPLE_ID_CREATE";
        var name = "";
        var chmod = "rw-rw-rw-";
        var edit_link_div = $("#link-instance-file-" + sample_id1).clone().attr('id', 'link-instance-file-' + file_id);
    }
    
    edit_link_div.html(function(index, html) {
        return html.replace(new RegExp(sample_id1, 'g'), file_id).replace(/SAMPLE_NAME/g, name).
            replace(/SAMPLE_CHMOD_SETTINGS/g, chmod);
    });
    $("#link-instance-file-divs").append(edit_link_div);
    
    var tr = $("#instance-file-popup-tr-" + sample_id1).clone().attr('id', 'instance-file-popup-tr-' + file_id);
    tr.html(function(index, html) {
        return html.replace(new RegExp(sample_id1, 'g'), file_id).replace(/SAMPLE_DEFAULT_NAME/g, default_name).
            replace(/SAMPLE_DESCRIPTION/g, description);
    });
    $("#add-instance-file-table > tbody").append(tr);

    var edit_div = $("#edit-instance-file-" + sample_id2).clone().attr('id', 'edit-instance-file-' + file_id);
    edit_div.html(function(index, html) {
        return html.replace(new RegExp(sample_id2, 'g'), file_id).replace(/SAMPLE_DEFAULT_NAME/g, default_name).
            replace(/SAMPLE_DESCRIPTION/g, description);
    });
    $("#edit-instance-file-divs").append(edit_div); 
}

function show_edit_instance_files_popup(event, url) {
    event.preventDefault();

    $.get(url, function(data, textStatus, jqXHR) {
        var file_ids = [];
        $('#instance-files-table tbody tr').each(function() {
            file_ids.push($(this).attr("data-file-id"));   
        });
        var popup = $("#edit-instance-files-popup");
        var error_span = $("#edit-instance-files-popup-error");
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
        $("#instance-file-table > tbody").empty();
        $("#edit-instance-file-divs").empty();
        $("#edit-instance-file-divs").css({"display" : "block"});
        $("#link-instance-file-divs").empty();
        $("#link-instance-file-divs").hide();
        add_create_instance_file_div();
        
        $.each(result, function() {
            var file_id = "" + this.id;
            if ($.inArray(file_id, file_ids) > -1) {
                add_instance_file_to_popup(file_id, this.default_name, this.description, this.link, true);
            } else {
                add_instance_file_to_popup(file_id, this.default_name, this.description, this.link, false);
            }
        });
        popup.css({"opacity": "1", "pointer-events": "auto"});
    });
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

    // Get the linked feedback questions
    var question_ids = $('#feedback-question-table > table > tbody > tr').map(function() {
        return this.getAttribute('data-question-id');
    }).get().join(',');
    console.log("Question ids: ");
    console.log(question_ids);
    
    var form_type = form.attr('method');
    var form_url = form.attr('action');

    console.log("Method: " + form_type + ", URL: " + form_url);

    var form_data = new FormData(form[0]);
    form_data.append('order_hierarchy', JSON.stringify(order_hierarchy));
    form_data.append('exercise_feedback_questions', question_ids);

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

var test_enum = 1;

function add_test() {
    var new_id = 'newt' + test_enum;
    var new_name = "New test";
    var new_stage_id = 'news' + stage_enum;
    var new_cmd_id = 'newc' + cmd_enum;

    var test_tablist = $("#test-tabs > ol:first-child");
    // TODO: The new test tab item should be included in the template section and cloned.
    var new_test_tab_item = $('<li><a href="#test-tabs-' + new_id + '" id="test-' + new_id + '">' + new_name + '</a></li>');
    new_test_tab_item.insertBefore("li.test-tab-button-container");

    // Create the new test tab
    var new_test_tab = $("#test-tabs-SAMPLE_TEST_ID").clone().attr('id', 'test-tabs-' + new_id);
    new_test_tab.html(function(index, html) {
        return html.replace(/SAMPLE_TEST_ID/g, new_id).replace(/SAMPLE_STAGE_ID/g, new_stage_id).
            replace(/SAMPLE_COMMAND_ID/g, new_cmd_id).replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, '1').
            replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, '1');
    });
    $("#test-tabs").append(new_test_tab);

    $("#test-tabs").tabs('refresh');
    $("#stages-sortable-" + new_id).sortable();
    $("#stages-sortable-" + new_id).disableSelection();
    $("#commands-sortable-" + new_id + "-" + new_stage_id).sortable();
    $("#commands-sortable-" + new_id + "-" + new_stage_id).disableSelection();
    
    test_enum++;
    stage_enum++;
    cmd_enum++;
}

var stage_enum = 1;

function add_stage(test_id) {
    var new_id = 'news' + stage_enum;
    var stage_list = $("#stages-sortable-" + test_id);
    var stage_ordnum = stage_list.children().length + 1;
    var cmd_ordnum = 1;
    
    // Create the new stage and a command to the list
    //<li class="ui-state-default" data-stage-id="SAMPLE_STAGE_ID">
    var new_cmd_id = 'newc' + cmd_enum;
    var new_stage_list_item = $('li[data-stage-id="SAMPLE_STAGE_ID"]').clone().attr('data-stage-id', new_id);
    new_stage_list_item.html(function(index, html) {
        return html.replace(/SAMPLE_TEST_ID/g, test_id).replace(/SAMPLE_STAGE_ID/g, new_id).
            replace(/SAMPLE_COMMAND_ID/g, new_cmd_id);
    });
    stage_list.append(new_stage_list_item);

    var new_cmd_list = $("#commands-sortable-" + test_id + "-" + new_id);

    // Create the information box to the right side of the list for the new command
    var new_cmd_info = $('#command-information-SAMPLE_COMMAND_ID').clone().attr('id', 'command-information-' + new_cmd_id);
    new_cmd_info.html(function(index, html) {
        return html.replace(/SAMPLE_COMMAND_ID/g, new_cmd_id).replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum).
            replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, cmd_ordnum);
    });
    $("#selection-information-container-" + test_id).append(new_cmd_info);

    // Create the information box to the right side of the list for the new stage
    var new_stage_info = $('#stage-information-SAMPLE_STAGE_ID').clone().attr('id', 'stage-information-' + new_id);
    new_stage_info.html(function(index, html) {
        return html.replace(/SAMPLE_STAGE_ID/g, new_id).replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum);
    });
    $("#selection-information-container-" + test_id).append(new_stage_info);

    new_cmd_list.sortable();
    new_cmd_list.disableSelection();
    cmd_enum++;

    stage_list.sortable("refresh");
    stage_enum++;
}

var cmd_enum = 1;

function add_command(test_id, stage_id) {
    var new_id = 'newc' + cmd_enum;
    var cmd_list = $("#commands-sortable-" + test_id + "-" + stage_id);
    var cmd_ordnum = cmd_list.children().length + 1;
    var stage_list = $("#stages-sortable-" + test_id);
    var stage_ordnum = stage_list.children("li[data-stage-id=" + stage_id + "]").index() + 1;
    
    // Create the new command to the list
    var new_cmd_list_item = $('li[data-command-id="SAMPLE_COMMAND_ID"]').clone().attr('data-command-id', new_id);
    new_cmd_list_item.html(function(index, html) {
        return html.replace(/SAMPLE_COMMAND_ID/g, new_id);
    });
    cmd_list.append(new_cmd_list_item);

    // Create the information box to the right side of the list
    var new_cmd_info = $('#command-information-SAMPLE_COMMAND_ID').clone().attr('id', 'command-information-' + new_id);
    new_cmd_info.html(function(index, html) {
        return html.replace(/SAMPLE_COMMAND_ID/g, new_id).replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum).
            replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, cmd_ordnum);
    });
    $("#selection-information-container-" + test_id).append(new_cmd_info);

    stage_list.sortable("refresh");
    cmd_list.sortable("refresh");
    cmd_enum++;
}

function edit_feedback_form_success(data, text_status, jqxhr_obj) {
    var ID_PATTERN = /\[(.*?)\]/;
    var CHOICE_ENUM_PATTERN = /\{(.*?)\}/;
    if (data.error) {
        var sep = "<br>";
        $.each(data.error, function(err_source, err_msg) {
            if (err_source === "__all__") {
                var error_div = $("#feedback-error");
            } else {
                var question_id = err_source.match(ID_PATTERN)[1];
                if (err_source.startsWith("question_field")) {
                    var error_div = $("#feedback-question-" + question_id + "-error");
                } else if (err_source.startsWith("type_field")) {
                    var error_div = $("#feedback-error");
                } else if (err_source.startsWith("choice_field")) {
                    var choice_enum = err_source.match(CHOICE_ENUM_PATTERN)[1];
                    var error_div = $("#feedback-choice-" + question_id + "-" + choice_enum + "-error");
                }
            }
            error_div.html(err_msg.join(sep));
            error_div.css("display", "block");
            show_feedback_question_edit_menu(question_id);
            //TODO: Scroll to the choice that caused the error
        });
    } else if (data.result) {
        console.log("Feedback questions edited successfully!");    
        close_popup_and_add_questions(data.result);
    }
}

function edit_feedback_form_error(xhr, status, type) {
    var error_span = $("#feedback-error");
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

function submit_edit_feedback_form(e) {
    e.preventDefault();
    console.log("User requested create feedback form submit.");

    $("div.popup div.admin-error").hide();

    var form = $('#edit-feedback-form');
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
        success: edit_feedback_form_success,
        error: edit_feedback_form_error
    });
}

function change_current_language(e) {
    e.preventDefault();

    var new_code = e.target.value;

    // Change the visible code in the language picker
    $('#language-info-code').text(new_code);

    // Change the visible input elements to the correponding language coded ones
    var translated_elements = $('.translated');
    translated_elements.removeClass('translated-visible');
    translated_elements.filter('[data-language-code=' + new_code + ']').addClass('translated-visible');

    // TODO: Swap the visible input elements into the corresponding language coded ones
}
