/********************************************
* Exercise admin form general functionality *
********************************************/

// TODO: Extendability and usability as a more general form for all lecture and
//       exercise types.
//         - Research ways to separate the exercise specific stuff by using, e.g.
//           registration methods for the code (in document ready and main form
//           submit for instance)
//         - Evaluate possibilities for implementing more general functionality
//           for stuff like popups, adding, deleting etc.

$(document).ready(function () {
    const content_inputs = $("textarea.exercise-content-input")
    page_title_elem = $("title")
    breadcrumb_elem = $("#exercise-name-breadcrumb")
    content_inputs.each(function () {
        const content_html = $(this).html()
        const content_lang = $(this).attr("name").split("_")[2]
        if (content_html === "" || content_html === undefined) {
            content_untouched[content_lang] = true
        }
        content_input[content_lang] = $(this)
    })
    $("div.feedback-table-div").slimScroll({
        height: "225px"
    })
    $("#feedback-choice-list-div-create").slimScroll({
        height: "150px"
    })
    $("div.add-instance-file-table-div").slimScroll({
        height: "225px"
    })
    $("#edit-feedback-popup, #edit-instance-files-popup").click(function () {
        close_popup($(this))
    })
    $("section.included-files div.popup").click(function () {
        close_included_file_popup($(this), $(this).attr("data-file-id"))
    })
    $("#edit-instance-files-popup").click(function () {
        close_instance_file_popup()
    })
    $(".popup > div").click(function (event) {
        event.stopPropagation()
    })
    $("input[type=text].exercise-tag-input").each(function () {
        change_tag_width(this)
        if (this.value === "") {
            remove_tag(this)
        }
    })
    // Reset the translation selector
    $("#language-selector > option").each(function () {
        if (this.defaultSelected) {
            this.selected = true
            return false
        }
    })
    // Update instance file table since link input fields may have been
    // edited before previous page refresh
    update_instance_file_table_with_client_data(false)
    // Display the required files with the currently selected translation
    refresh_required_files_all()
})

function create_id_mapping_from_json_of_new_objects (new_objects_json) {
    const id_mapping = {}
    for (const object_type in new_objects_json) {
        id_mapping[object_type] = {}
        const objects_of_type = new_objects_json[object_type]
        for (const old_id in objects_of_type) {
            id_mapping[object_type][old_id] = objects_of_type[old_id].pk
        }
    }
    return id_mapping
}

function replace_str_in_elem_attrs (elem, old_str, new_str) {
    for (let i = 0; i < elem.attributes.length; i++) {
        const attr = elem.attributes[i]
        if (attr.specified) {
            $(elem).attr(attr.name, attr.value.replace(old_str, new_str))
        }
    }
}

function refresh_id_occurences_in_subtree (old_id, db_id, root) {
    replace_str_in_elem_attrs(root.get(0), old_id, db_id)
    root.find("*").each(function () {
        replace_str_in_elem_attrs(this, old_id, db_id)
    })
}

function refresh_id_occurences_in_subtrees (id_mapping, root_prefixes) {
    for (const old_id in id_mapping) {
        const db_id = id_mapping[old_id]
        for (let i = 0; i < root_prefixes.length; i++) {
            const root = $("#" + root_prefixes[i] + "-" + old_id)
            refresh_id_occurences_in_subtree(old_id, db_id, root)
        }
    }
}

function refresh_hint_ids (id_mapping) {
    refresh_id_occurences_in_subtrees(id_mapping.hints, ["hint"])
}

function refresh_included_file_ids (id_mapping) {
    refresh_id_occurences_in_subtrees(
        id_mapping.included_files, ["edit-included-file", "included-file-tr"]
    )
}

function refresh_test_ids (id_mapping) {
    refresh_id_occurences_in_subtrees(id_mapping.tests, ["test-li", "test-tabs"])
}

function refresh_stage_ids (id_mapping) {
    refresh_id_occurences_in_subtrees(id_mapping.stages, ["stage-li", "stage-information"])
}

function refresh_command_ids (id_mapping) {
    refresh_id_occurences_in_subtrees(id_mapping.commands, ["command-li", "command-information"])
}

function refresh_ids_of_new_objects (new_objects_json) {
    const id_mapping = create_id_mapping_from_json_of_new_objects(new_objects_json)
    refresh_hint_ids(id_mapping)
    refresh_included_file_ids(id_mapping)
    refresh_test_ids(id_mapping)
    refresh_stage_ids(id_mapping)
    refresh_command_ids(id_mapping)
}

function add_links_of_new_included_file (link_divs, new_file_fields) {
    link_divs.each(function () {
        const lang_code = $(this).attr("data-language-code")
        const fileinfo = new_file_fields["fileinfo_" + lang_code]
        if (fileinfo) {
            const url = "/media/" + fileinfo
            const link = $(
                "<a href=\"" + url + "\" class=\"file-url\" data-language-code=\"" +
                lang_code + "\" download>\""
            )
            $(this).append(link)
        }
    })
}

function add_links_of_new_included_files (new_files_json) {
    for (const old_id in new_files_json) {
        const new_file_fields = new_files_json[old_id].fields
        const link_divs_main = $(
            "#included-file-td-link-" + old_id
        ).find("div.included-file-link-div")
        const link_divs_popup = $(
            "#edit-included-file-" + old_id
        ).find("div.included-file-link-div")
        add_links_of_new_included_file(link_divs_main, new_file_fields)
        add_links_of_new_included_file(link_divs_popup, new_file_fields)
    }
}

function submit_main_form (e) {
    e.preventDefault()
    console.log("User requested main form submit.")

    const form = $("#main-form")

    // Get the hierarchy of stages and commands for the calculation of implicit
    // ordinal_numbers at the form validation
    const tests = []
    $("#test-tabs > ol > li").each(function (x) {
        const current_href = $(this).children("a").attr("href")
        if (current_href !== undefined) {
            const current_id = current_href.split("-")[2]
            tests.push(current_id)
        }
    })
    const order_hierarchy = { stages_of_tests: {}, commands_of_stages: {} }
    for (const test_id of tests) {
        let stage_order

        $("#stages-sortable-" + test_id).each(function (x) {
            stage_order = $(this).sortable("toArray", options = { attribute: "data-stage-id" })
            order_hierarchy.stages_of_tests[test_id] = stage_order

            for (const stage_id of stage_order) {
                let command_order
                $("#commands-sortable-" + test_id + "-" + stage_id).each(function (y) {
                    command_order = $(this).sortable("toArray", options = {
                        attribute: "data-command-id"
                    })
                })
                order_hierarchy.commands_of_stages[stage_id] = command_order
            }
        })
    }
    console.log(order_hierarchy)

    // Get the linked feedback questions
    console.log($("#feedback-question-table > tbody > tr"))
    const question_ids = $("#feedback-question-table > tbody > tr").map(function () {
        return this.getAttribute("data-question-id")
    }).get().join(",")
    console.log("Question ids: ")
    console.log(question_ids)

    const form_type = form.attr("method")
    const form_url = form.attr("action")

    console.log("Method: " + form_type + ", URL: " + form_url)

    const form_data = new FormData(form[0])

    // Remove unnecessary instance file link fields and add fields that map new-ids to file ids.
    const link_fields_to_remove = []
    $("div.link-instance-file").each(function () {
        if ($(this).attr("data-linked") !== "true") {
            $(this).find("input.file-name-input").each(function () {
                link_fields_to_remove.push($(this).attr("name"))
            })
            link_fields_to_remove.push($(this).find("select.file-purpose-select").attr("name"))
            link_fields_to_remove.push($(this).find("select.file-chown-select").attr("name"))
            link_fields_to_remove.push($(this).find("select.file-chgrp-select").attr("name"))
            link_fields_to_remove.push($(this).find("input.file-chmod-input").attr("name"))
        }
    })

    form_data.append("order_hierarchy", JSON.stringify(order_hierarchy))
    form_data.append("exercise_feedback_questions", question_ids)
    for (const field_name of link_fields_to_remove) {
        form_data.delete(field_name)
    }

    console.log("Serialized form data:")
    for (const [key, value] of form_data.entries()) {
        console.log(key, value)
    }

    console.log("Submitting the form...")
    $.ajax({
        type: form_type,
        url: form_url,
        data: form_data,
        processData: false,
        contentType: false,
        dataType: "json",
        success: function (data, text_status, jqxhr_obj) {
            if (data.redirect_url !== "" && typeof data.redirect_url !== "undefined") {
                window.location.href = data.redirect_url
            }
            const success_text = "Successfully saved!"
            alert(success_text)
            add_links_of_new_included_files(data.new_objects.included_files)
            refresh_ids_of_new_objects(data.new_objects)
            refresh_required_files_all()
        },
        error: function (xhr, status, type) {
            const error_text = (
                "The following errors happened during processing of the form:\n\n" +
                xhr.responseText
            )
            alert(error_text)
        }
    })
}

function delete_exercise () {
    // TODO: A popup asking whether the user really wants to delete the
    // exercise and all its associated include files, tests, stages,
    // commands, links to feedbacks and links to instance include files.
}

function close_popup (popup) {
    popup.css({ opacity: "0", "pointer-events": "none" })
}

/*********************
* Language selection *
*********************/

function change_current_language (e) {
    e.preventDefault()

    const new_code = e.target.value

    // Change the visible code in the language picker
    $("#language-info-code").text(new_code)

    // Change the visible input elements to the correponding language coded ones
    const translated_elements = $(".translated")
    translated_elements.removeClass("translated-visible")
    translated_elements.filter("[data-language-code=" + new_code + "]")
        .addClass("translated-visible")

    // Display the page title and breadcrumb in the correct language
    const name = $("#exercise-name-" + new_code).val()
    page_title_elem.html(title_prefix + name)
    breadcrumb_elem.html(name)

    // Display the required files with the currently selected translation
    refresh_required_files_all()
}

/***********************************************************
* General information (name, page contents, question etc.) *
***********************************************************/

function exercise_name_changed (e, lang_code) {
    /* If the exercise page content is empty when the script loads, add a title
       automatically. */
    const new_name = e.target.value

    /* TODO: 'Add' instead of 'Edit' when adding a new page */
    page_title_elem.html(title_prefix + new_name)
    breadcrumb_elem.html(new_name)

    // Same for the content input box
    if (content_untouched[lang_code] === true) {
        content_input[lang_code].html("== " + new_name + " ==\n\n")
    }
}

function exercise_page_content_changed (e, lang_code) {
    content_untouched[lang_code] = false
}

function delete_table_row (button) {
    $(button).parent().parent().remove()
}

const content_untouched = {}
const content_input = {}
let page_title_elem
let breadcrumb_elem
const title_prefix = $("title").html().split("|")[0].trim() + " | "

/*******
* Tags *
*******/

function change_tag_width (input_elem) {
    const CHAR_WIDTH = 9
    const MAX_FITTING_LENGTH = 4
    const input = $(input_elem)
    const val_len = input.val().length

    if (val_len > MAX_FITTING_LENGTH) {
        input.width((input_elem.value.length * CHAR_WIDTH) + "px")
    } else {
        input.width(input.css("min-width"))
    }
}

let tag_enum = 1

function add_tag () {
    const ul = $("ul.exercise-tags")
    const li = $("<li class=\"exercise-tag\">")

    const new_tag = $(
        "<input type=\"text\" id=\"exercise-tag-new-" +
        tag_enum +
        "\" class=\"exercise-tag-input\" name=\"exercise_tag_" +
        tag_enum +
        "\" value=\"?\" maxlength=\"32\" onfocus=\"highlight_parent_li(this);\"" +
        "oninput=\"change_tag_width(this);\">"
    )
    const new_button = $(
        "<button type=\"button\" class=\"delete-button\" onclick=\"remove_tag(this);\">x</button>"
    )
    li.append(new_tag)
    li.append(new_button)
    ul.append(li)
    tag_enum++
}

function remove_tag (tag_elem) {
    const li = $(tag_elem).parent()
    li.remove()
}

function highlight_parent_li (input_elem) {
    const input = $(input_elem)
    const parent = input.parent()
    const hilight_class = "exercise-tag-input-hilighted"

    parent.toggleClass(hilight_class, true)
    input.focusout(function () {
        if (input.val() === "") {
            remove_tag(input[0])
        } else if (!parent.is(":hover")) {
            parent.toggleClass(hilight_class, false)
        }
    })
    parent.hover(function () {
        parent.toggleClass(hilight_class, true)
    }, function () {
        if (!input.is(":focus")) {
            parent.toggleClass(hilight_class, false)
        }
    })
}

/********************
* Feedback settings *
********************/

function update_create_feedback_button_state (default_lang) {
    const button = $("#create-feedback-button")
    const question_ok = $("#feedback-question-create-" + default_lang).val() !== ""

    let choices_ok = true
    const choice1_div = $("#feedback-choices-div-create:visible")
        .find("div.feedback-choice-div:first")
    if (choice1_div.length > 0) {
        const choice_1 = choice1_div.find(
            "input[data-language-code=" + default_lang + "].feedback-choice"
        )
        if (choice_1.val() === "") {
            choices_ok = false
        } else {
            const choice2_div = choice1_div.next()
            const choice_2 = choice2_div.find(
                "input[data-language-code=" + default_lang + "].feedback-choice"
            )
            if (choice_2.val() === "") {
                choices_ok = false
            }
        }
    }

    if (!question_ok || !choices_ok) {
        button.prop("disabled", true)
    } else {
        button.prop("disabled", false)
    }
}

let fb_choice_enum = 1

function add_feedback_choice (question_id, choice_answers) {
    const choice_list_div = $("#feedback-choice-list-div-" + question_id)
    const choice_n = choice_list_div.children().length + 1
    const REQUIRED_CHOICES_N = 2
    if (choice_n > REQUIRED_CHOICES_N) {
        var sample_id = "SAMPLE_CHOICE_ID"
    } else {
        var sample_id = "SAMPLE_REQUIRED_CHOICE_ID"
    }

    const choice_div = $("#feedback-choice-div-" + sample_id).clone()
        .attr("id", "feedback-choice-div-" + fb_choice_enum)
    choice_div.html(function (index, html) {
        html = html.replace(new RegExp(sample_id, "g"), fb_choice_enum)
            .replace(/SAMPLE_QUESTION_ID/g, question_id)
            .replace(/SAMPLE_CHOICE_N/g, choice_n)
        if (typeof choice_answers !== "undefined") {
            $.each(choice_answers, function (key, val) {
                html = html.replace(new RegExp("SAMPLE_ANSWER_" + key, "g"), val)
            })
        } else {
            html = html.replace(/SAMPLE_ANSWER_[A-Za-z]{2}/g, "")
        }
        return html
    })

    choice_list_div.append(choice_div)
    fb_choice_enum++
}

function delete_feedback_choice (choice_id) {
    const choice_div = $("#feedback-choice-div-" + choice_id)
    const choice_n = choice_div.index()
    const nextChoices = choice_div.nextAll()

    choice_div.remove()
    nextChoices.each(function (index) {
        const new_choice_n = choice_n + index + 1
        $(this).find("span.feedback-choice-span").text("Choice " + new_choice_n + ":")
    })
}

function handle_feedback_type_selection (select, default_lang) {
    const option = select.options[select.selectedIndex]
    const choices_div = $("#feedback-choices-div-create")
    const add_choice_button = $("#add-new-feedback-choice")

    if (option.value === "MULTIPLE_CHOICE_FEEDBACK") {
        choices_div.css({ display: "block" })
        add_choice_button.css({ display: "inline-block" })
    } else {
        choices_div.hide()
        $("#feedback-choices-div-list-create").empty()
        add_choice_button.hide()
    }
    update_create_feedback_button_state(default_lang)
}

function select_all_feedback_questions (select) {
    $("td.question-cell > input[type=checkbox].feedback-question-checkbox").prop("checked", select)
}

function show_feedback_question_edit_menu (question_id) {
    $("div.edit-feedback-div").hide()
    $("#create-feedback-div").hide()
    $("#edit-feedback-divs").css({ display: "block" })
    $("#edit-feedback-div-" + question_id).css({ display: "block" })
}

function close_edit_feedback_menu () {
    $("#edit-feedback-divs").hide()
    $("#create-feedback-div").css({ display: "block" })
}

function add_feedback_choices_to_popup (question_id, choices) {
    if (choices.length > 0) {
        $.each(choices, function (index, choice) {
            add_feedback_choice(question_id, choice)
        })
    } else {
        add_feedback_choice(question_id)
        add_feedback_choice(question_id)
    }
}

function add_feedback_question_to_popup (id, questions, type, readable_type, choices, checked) {
    let sample_id
    if (checked) {
        sample_id = "SAMPLE_CHECKED_ID"
    } else {
        sample_id = "SAMPLE_ID"
    }

    const tr = $("#feedback-question-popup-tr-" + sample_id).clone()
        .attr("id", "feedback-question-popup-tr" + id)
    tr.html(function (index, html) {
        html = html.replace(new RegExp(sample_id, "g"), id)
            .replace(/SAMPLE_HUMAN_READABLE_TYPE/g, readable_type)
        $.each(questions, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_QUESTION_" + key, "g"), val)
        })
        return html
    })
    $("#add-feedback-table > tbody").append(tr)

    const edit_div = $("#edit-feedback-div-SAMPLE_ID").clone().attr("id", "edit-feedback-div-" + id)
    edit_div.html(function (index, html) {
        html = html.replace(/SAMPLE_ID/g, id).replace(/SAMPLE_TYPE/g, type)
            .replace(/SAMPLE_HUMAN_READABLE_TYPE/g, readable_type)
        $.each(questions, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_QUESTION_" + key, "g"), val)
        })
        return html
    })

    $("#edit-feedback-divs").append(edit_div)

    if (type === "MULTIPLE_CHOICE_FEEDBACK") {
        $("#feedback-choice-list-div-" + id).slimScroll({
            height: "150px"
        })
        add_feedback_choices_to_popup(id, choices)
    } else {
        edit_div.find("#feedback-choices-div-" + id).hide()
        edit_div.find("#add-feedback-choice-" + id).hide()
    }
}

function init_create_feedback_choice_list (default_lang) {
    const choice_list_div = $("#feedback-choice-list-div-create")
    choice_list_div.empty()
    add_feedback_choice("create")
    add_feedback_choice("create")
    choice_list_div.find("input.feedback-choice")
        .attr("oninput", "update_create_feedback_button_state('" + default_lang + "');")
}

let feedback_enum = 1

function create_new_feedback_question_entry (default_lang) {
    const questions = {}
    const question_inputs = $("#create-feedback-div input.feedback-question-input")
    question_inputs.each(function () {
        questions[$(this).attr("data-language-code")] = $(this).val()
    })

    const type = $("#feedback-type-select-create").val()
    const readable_type = type.toLowerCase().replace(/_/g, " ")
    const choice_check = {}
    const choices = []

    $("div.popup div.admin-error").hide()

    let duplicates = false
    $("#create-feedback-div div.feedback-choice-div").each(function () {
        const choice_div = $(this)
        const choice = {}
        choice_div.find("input.feedback-choice").each(function () {
            const lang = $(this).attr("data-language-code")
            const answer = $(this).val()
            if (typeof choice_check[lang] !== "undefined") {
                if (answer !== "" && choice_check[lang].indexOf(answer) > -1) {
                    const choice_error_div = choice_div.find("div.admin-error")
                    choice_error_div.text("Duplicate choice!")
                    choice_error_div.css({ display: "block" })
                    duplicates = true
                }
                choice_check[lang].push(answer)
            } else {
                choice_check[lang] = [answer]
            }
            choice[lang] = answer
        })
        choices.push(choice)
    })

    let already_exists = false
    $("#add-feedback-div label.feedback-question-label").each(function () {
        const lang = $(this).parent().attr("data-language-code")
        const question = $(this).text()
        if (question !== "" && question === questions[lang]) {
            already_exists = true
            return false
        }
    })
    if (already_exists) {
        const feedback_error_div = $("#feedback-question-error-create")
        feedback_error_div.text("This feedback question already exists")
        feedback_error_div.css({ display: "block" })
        return
    }
    if (duplicates) {
        return
    }

    question_inputs.val("")
    init_create_feedback_choice_list(default_lang)

    handle_feedback_type_selection($("#feedback-type-select-create")[0], default_lang)
    add_feedback_question_to_popup(
        "new-" + feedback_enum, questions, type, readable_type, choices, true
    )
    feedback_enum++
}

function show_edit_feedback_questions_popup (event, url, default_lang) {
    event.preventDefault()

    $.get(url, function (data, textStatus, jqXHR) {
        const question_ids = []
        $("#feedback-question-table tbody tr").each(function () {
            question_ids.push($(this).attr("data-question-id"))
        })
        const popup = $("#edit-feedback-popup")
        const error_span = $("#edit-feedback-popup-error")
        const result = data.result
        const error = data.error

        if (error) {
            error_span.text(error)
            error_span.css({ display: "inline-block" })
            return
        } else {
            error_span.empty()
            error_span.hide()
        }

        $("div.popup div.admin-error").hide()
        $("#add-feedback-table > tbody").empty()
        $("#fb-question-checkbox-all").prop("checked", false)
        $("#edit-feedback-divs").empty()
        $("#edit-feedback-divs").hide()
        $("#create-feedback-div").css({ display: "block" })
        init_create_feedback_choice_list(default_lang)

        $.each(result, function () {
            const question_id = "" + this.id
            if ($.inArray(question_id, question_ids) > -1) {
                add_feedback_question_to_popup(
                    this.id, this.questions, this.type, this.readable_type, this.choices, true
                )
            } else {
                add_feedback_question_to_popup(
                    this.id, this.questions, this.type, this.readable_type, this.choices, false
                )
            }
        })
        handle_feedback_type_selection($("#feedback-type-select-create")[0])
        update_create_feedback_button_state(default_lang)
        popup.css({ opacity: "1", "pointer-events": "auto" })
    })
}

function destroy_choice_lists () {
    const choice_lists = $("div.feedback-choice-list")
    choice_lists.slimScroll({
        destroy: true
    })

    // Remove binded events that slimScroll doesn't remove automatically
    // http://stackoverflow.com/questions/26783076/slimscroll-destroy-doesnt-unbind-the-scroll-events
    choice_lists.each(function () {
        events = $._data($(this)[0], "events")
        if (events) {
            $._removeData($(this)[0], "events")
        }
    })
}

function update_tr_in_feedback_table (new_tr_data, tr) {
    const questions = new_tr_data.questions
    const readable_type = new_tr_data.readable_type

    tr.find("td.question-cell span").each(function () {
        const span = $(this)
        span.text(questions[span.attr("data-language-code")])
    })
    tr.find("td.type-cell").text(readable_type)
}

function add_tr_to_feedback_table (tr_data, tbody) {
    const question_id = tr_data.question_id
    const questions = tr_data.questions
    const readable_type = tr_data.readable_type
    const tr = $("#feedback-question-tr-SAMPLE_ID").clone()

    tr.attr("id", "feedback-question-tr-" + question_id)
    tr.attr("data-question-id", question_id)
    tr.html(function (index, html) {
        html = html.replace(/SAMPLE_ID/g, question_id)
            .replace(/SAMPLE_HUMAN_READABLE_TYPE/g, readable_type)
        $.each(questions, function (key, val) {
            sample_str = "SAMPLE_QUESTION_" + key
            html = html.replace(new RegExp(sample_str, "g"), val)
        })
        return html
    })
    tbody.append(tr)
}

function update_feedback_table_selection_and_existing_data (questions, default_lang) {
    const target_tbody = $("#feedback-question-table tbody")
    $("#add-feedback-table > tbody input.feedback-question-checkbox").each(function (index) {
        const checked = $(this).prop("checked")
        const question_id = $(this).attr("data-question-id")
        const question = $("#feedback-question-" + question_id + "-" + default_lang).val()
        let db_id = ""
        let db_readable_type = ""
        let db_questions = {}
        let in_table = false
        let saved = false

        $.each(questions, function (index, db_question) {
            if (db_question.questions[default_lang] === question) {
                db_id = "" + db_question.id
                db_readable_type = db_question.readable_type
                db_questions = db_question.questions
                saved = true
                return false
            }
        })
        if (!saved) {
            return
        }

        let tr = null
        target_tbody.find("tr").each(function () {
            if ($(this).attr("data-question-id") === db_id) {
                tr = $(this)
                in_table = true
                return false
            }
        })

        if (in_table && !checked) {
            tr.remove()
        } else if (in_table) {
            const tr_data = { questions: db_questions, readable_type: db_readable_type }
            update_tr_in_feedback_table(tr_data, tr)
        } else if (checked) {
            const tr_data = {
                question_id: db_id,
                questions: db_questions,
                readable_type: db_readable_type
            }
            add_tr_to_feedback_table(tr_data, target_tbody)
        }
    })
}

function update_feedback_table_selection () {
    const target_tbody = $("#feedback-question-table tbody")
    $("#add-feedback-table > tbody input.feedback-question-checkbox").each(function (index) {
        const checked = $(this).prop("checked")
        const question_id = $(this).attr("data-question-id")
        if (question_id.startsWith("new")) {
            return
        }
        let in_table = false

        let tr = null
        target_tbody.find("tr").each(function () {
            if ($(this).attr("data-question-id") === question_id) {
                tr = $(this)
                in_table = true
                return false
            }
        })

        if (in_table && !checked) {
            tr.remove()
        } else if (!in_table && checked) {
            const question_inputs = $(
                "#edit-feedback-div-" + question_id + " input.feedback-question-input"
            )
            const readable_type = $("#feedback-readable-type-" + question_id).val()
            const questions = {}
            $.each(question_inputs, function () {
                questions[$(this).attr("data-language-code")] = $(this).val()
            })
            const tr_data = { question_id, questions, readable_type }
            add_tr_to_feedback_table(tr_data, target_tbody)
        }
    })
}

function edit_feedback_form_success (data, text_status, jqxhr_obj, default_lang) {
    const ID_PATTERN = /\[(.*?)\]/
    const CHOICE_ENUM_PATTERN = /\((.*?)\)/
    if (data.error) {
        const sep = "<br>"
        $.each(data.error, function (err_source, err_msg) {
            let error_div = $("#feedback-error")
            if (err_source !== "__all__") {
                let question_id = err_source.match(ID_PATTERN)[1]
                if (err_source.startsWith("feedback_question")) {
                    error_div = $("#feedback-question-error-" + question_id)
                } else if (err_source.startsWith("feedback_choice")) {
                    const choice_enum = err_source.match(CHOICE_ENUM_PATTERN)[1]
                    error_div = $("#feedback-choice-error-" + choice_enum)
                }
            }
            error_div.html(err_msg.join(sep))
            error_div.css("display", "block")
            show_feedback_question_edit_menu(question_id)
            // TODO: Scroll to the choice that caused the error
        })
    } else if (data.result) {
        console.log("Feedback questions edited successfully!")
        update_feedback_table_selection_and_existing_data(data.result, default_lang)
        close_popup($("#edit-feedback-popup"))
        destroy_choice_lists()
    }
}

function close_feedback_popup_without_saving () {
    update_feedback_table_selection()
    close_popup($("#edit-feedback-popup"))
    destroy_choice_lists()
}

function edit_feedback_form_error (xhr, status, type) {
    const error_span = $("#feedback-error")
    let error_str = "An error occured while sending the form:"
    status = status.charAt(0).toUpperCase() + status.slice(1)
    if (type) {
        error_str += status + ": " + type
    } else {
        error_str += status
    }
    error_span.html(error_str)
    error_span.css("display", "block")
}

function submit_edit_feedback_form (e, default_lang) {
    e.preventDefault()
    console.log("User requested create feedback form submit.")

    $("div.popup div.admin-error").hide()

    const form = $("#edit-feedback-form")
    const form_type = form.attr("method")
    const form_url = form.attr("action")

    console.log("Method: " + form_type + ", URL: " + form_url)

    const new_question_ids = []
    const linked_question_ids = []
    $("#edit-feedback-popup tbody input[type=checkbox].feedback-question-checkbox")
        .each(function () {
            const id = $(this).attr("data-question-id")
            if (id.startsWith("new")) {
                new_question_ids.push(id)
            }
        })

    const form_data = new FormData(form[0])

    const create_keys = []
    console.log("Serialized form data:")
    for (const [key, value] of form_data.entries()) {
        if (key.indexOf("create") > -1) {
            create_keys.push(key)
        }
    }

    form_data.append("new_questions", new_question_ids.join(","))
    for (const key of create_keys) {
        form_data.delete(key)
    }

    console.log("Submitting the form...")
    $.ajax({
        type: form_type,
        url: form_url,
        data: form_data,
        processData: false,
        contentType: false,
        dataType: "json",
        success: function (data, textStatus, jqXHR) {
            edit_feedback_form_success(data, textStatus, jqXHR, default_lang)
        },
        error: edit_feedback_form_error
    })
}

/********
* Hints *
********/

hint_enum = 1

function add_hint () {
    const hint_id = "new-" + hint_enum
    const tr = $("#hint-SAMPLE_ID").clone().attr("id", "hint-" + hint_id)
    tr.html(function (index, html) {
        html = html.replace(/SAMPLE_ID/g, hint_id)
        return html
    })
    $("#hint-table tbody").append(tr)
    hint_enum++
}

/**************************************
* File upload exercise included files *
**************************************/

function update_included_file_ok_button_state (file_id, default_lang) {
    const suffix = "-" + file_id + "-" + default_lang
    const button = $("#included-file-ok-button-" + file_id)
    if ((button.attr("data-button-mode") !== "add" ||
         $("#included-file" + suffix).val().length > 0) &&
        $("#included-file-default-name" + suffix).val().length > 0 &&
        $("#included-file-name" + suffix).val().length > 0 &&
        $("#included-file-chmod-" + file_id).val().length > 0) {
        button.prop("disabled", false)
    } else {
        button.prop("disabled", true)
    }
}

function update_inc_file_popup_on_def_name_change (default_name_input, file_id, default_lang) {
    const filename = default_name_input.val()
    const lang_code = default_name_input.attr("data-language-code")

    const name_input = $("#included-file-name-" + file_id + "-" + lang_code)
    if (name_input.val() === "") {
        name_input.val(filename)
    }
    update_included_file_ok_button_state(file_id, default_lang)
}

function update_inc_file_popup_on_file_change (file_input, file_id, default_lang) {
    const fileparts = file_input.val().split("\\")
    const filename = fileparts[fileparts.length - 1]
    const lang_code = file_input.attr("data-language-code")

    const default_name_input = $("#included-file-default-name-" + file_id + "-" + lang_code)
    if (default_name_input.val() === "") {
        default_name_input.val(filename)
    }

    update_inc_file_popup_on_def_name_change(default_name_input, file_id, default_lang)
}

function show_edit_included_file_popup (file_id, default_lang) {
    const popup = $("#edit-included-file-" + file_id)
    update_included_file_ok_button_state(file_id, default_lang)
    $("#file-chmod-error-" + file_id).hide()
    popup.css({ opacity: "1", "pointer-events": "auto" })
}

function check_chmod_input_validity (chmod_id, chmod_error_id) {
    const chmod = $(chmod_id).val()
    const found = chmod.match(/^((r|-)(w|-)(x|-)){3}$/)

    if (found === null || found[0] !== chmod) {
        const chmod_error_div = $(chmod_error_id)
        chmod_error_div.text(
            "File access mode was of incorrect format! Give 9 character, each either r, w, x or -!"
        )
        chmod_error_div.css({ display: "block" })
        return false
    } else {
        return true
    }
}

function update_included_file_tr (file_id, popup) {
    popup.find("input.file-name-input").each(function () {
        const name = $(this).val()
        const lang_code = $(this).attr("data-language-code")
        const name_span = $(
            "#included-file-td-name-" + file_id +
            " > span[data-language-code=" + lang_code + "].translated"
        )
        name_span.text(name)
    })
    popup.find("textarea.file-description-area").each(function () {
        const description = $(this).val()
        const lang_code = $(this).attr("data-language-code")
        const description_span = $(
            "#included-file-td-description-" + file_id +
            " > span[data-language-code=" + lang_code + "].translated"
        )
        description_span.text(description)
    })
    const purpose_td = $("#included-file-td-purpose-" + file_id)
    purpose_td.text($("#included-file-purpose-" + file_id + " option:selected").text())
}

function create_new_included_file_tr (file_id) {
    const popup = $("#edit-included-file-" + file_id)
    const purpose_display = $("#included-file-purpose-" + file_id + " option:selected").text()
    const name_inputs = popup.find("input.file-name-input")
    const description_areas = popup.find("textarea.file-description-area")

    const tr = $("#included-file-tr-SAMPLE_ID").clone().attr("id", "included-file-tr-" + file_id)
    tr.html(function (index, html) {
        html = html.replace(/SAMPLE_ID/g, file_id)
            .replace(/SAMPLE_GET_PURPOSE_DISPLAY/g, purpose_display)
        name_inputs.each(function () {
            sample_str = "SAMPLE_NAME_" + $(this).attr("data-language-code")
            val = $(this).val()
            html = html.replace(new RegExp(sample_str, "g"), val)
        })
        description_areas.each(function () {
            sample_str = "SAMPLE_DESCRIPTION_" + $(this).attr("data-language-code")
            val = $(this).val()
            html = html.replace(new RegExp(sample_str, "g"), val)
        })
        return html
    })
    $("#included-files-table tbody").append(tr)
}

function update_edit_included_file_popup_titles (popup) {
    popup.find("div.edit-included-file-title-div > div").each(function () {
        const lang = $(this).attr("data-language-code")
        const new_file_name = popup.find(
            "input[data-language-code=" + lang + "].file-name-input"
        ).val()
        $(this).children("h2").text("Edit included file: " + new_file_name)
    })
}

function confirm_included_file_popup (file_id) {
    if (!check_chmod_input_validity(
        "#included-file-chmod-" + file_id, "#file-chmod-error-" + file_id)
    ) {
        return
    }

    const popup = $("#edit-included-file-" + file_id)
    const existing_file = $(
        "#included-files-table tbody").find("#included-file-tr-" + file_id
    ).length > 0
    if (existing_file) {
        update_included_file_tr(file_id, popup)
    } else {
        create_new_included_file_tr(file_id)
        popup.find("div.edit-included-file-title-div").css({ display: "block" })
        popup.find("div.create-included-file-title-div").hide()
    }
    update_edit_included_file_popup_titles(popup)
    close_popup(popup)
    refresh_required_files_all()
}

function close_included_file_popup (popup, file_id) {
    if ($("#included-files-table tbody").find("#included-file-tr-" + file_id).length > 0) {
        close_popup(popup)
    } else {
        popup.remove()
    }
}

include_file_enum = 1

function create_included_file_popup (default_lang) {
    const id = "new" + include_file_enum
    const popup = $("#edit-included-file-SAMPLE_ID").clone().attr("id", "edit-included-file-" + id)
    popup.html(function (index, html) {
        return html.replace(/SAMPLE_ID/g, id)
    })
    popup.css({ opacity: "1", "pointer-events": "auto" })
    popup.find("div.edit-included-file-title-div").hide()
    popup.attr("data-file-id", id)
    $("#include-file-popups").append(popup)
    update_included_file_ok_button_state(id, default_lang)
    $("#edit-included-file-" + id).click(function () {
        close_included_file_popup(popup, popup.attr("data-file-id"))
    })
    $("#edit-included-file-" + id + " > div").click(function (event) {
        event.stopPropagation()
    })
    include_file_enum++
}

function remove_included_file (button) {
    // Remove the dangling popup
    const popup_id_split = $(button).parent().parent().attr("id").split("-")
    const popup_id = popup_id_split[popup_id_split.length - 1]
    $("#edit-included-file-" + popup_id).remove()

    // Delete the table row
    delete_table_row(button)

    // Refresh the included file options
    refresh_required_files_all()
}

/**************************************
* File upload exercise instance files *
**************************************/

function show_instance_file_edit_menu (file_id) {
    $("div.edit-instance-file").hide()
    $("div.link-instance-file").hide()
    $("#link-instance-file-divs").hide()
    $("#edit-instance-file-" + file_id).css({ display: "block" })
    $("#edit-instance-file-divs").css({ display: "block" })
}

function show_instance_file_edit_link_menu (file_id) {
    $("div.link-instance-file").hide()
    $("div.edit-instance-file").hide()
    $("#edit-instance-file-divs").hide()
    $("#link-instance-file-" + file_id).css({ display: "block" })
    $("#link-instance-file-divs").css({ display: "block" })
}

function close_instance_file_menu (file_id) {
    $("div.link-instance-file").hide()
    $("div.edit-instance-file").hide()
    $("#link-instance-file-divs").hide()
    $("#edit-instance-file-new-" + (instance_file_enum - 1)).css({ display: "block" })
    $("#edit-instance-file-divs").css({ display: "block" })
}

function update_instance_file_done_button_state (file_id, default_lang) {
    const button = $("#done-button-" + file_id)
    if (button.attr("data-button-mode") === "done") {
        return
    }

    const suffix = "-" + file_id + "-" + default_lang
    if ($("#instance-file" + suffix).val().length > 0 &&
        $("#instance-file-default-name" + suffix).val().length > 0) {
        button.prop("disabled", false)
    } else {
        button.prop("disabled", true)
    }
}

function update_link_edit_button_state (file_id, default_lang) {
    const button = $("#link-edit-button-" + file_id)
    if (button.attr("data-button-mode") === "remove") {
        return
    }

    const suffix = "-" + file_id + "-" + default_lang
    if ($("#instance-file-name" + suffix).val().length > 0 &&
        $("#instance-file-chmod-" + file_id).val().length > 0) {
        button.prop("disabled", false)
    } else {
        button.prop("disabled", true)
    }
}

instance_file_enum = 1

function add_create_instance_file_div () {
    const file_id = "new-" + instance_file_enum
    const create_div = $("#edit-instance-file-SAMPLE_CREATE_ID").clone()
        .attr("id", "edit-instance-file-" + file_id)
    create_div.html(function (index, html) {
        return html.replace(/SAMPLE_CREATE_ID/g, file_id)
    })
    create_div.find("div.edit-instance-file-title-div").hide()
    create_div.css({ display: "block" })
    $("#edit-instance-file-divs").append(create_div)
    instance_file_enum++
}

function add_instance_file_link_div (file_id, default_names) {
    const sample_id = "SAMPLE_ID"
    const link_div = $("#link-instance-file-" + sample_id).clone()
        .attr("id", "link-instance-file-" + file_id)
    link_div.attr("data-file-id", file_id)
    link_div.html(function (index, html) {
        html = html.replace(new RegExp(sample_id, "g"), file_id)
            .replace(/SAMPLE_FORM/g, "main-form")
        $.each(default_names, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_DEFAULT_NAME_" + key, "g"), val)
        })
        return html
    })
    $("#edit-file-link-title-div-" + file_id).removeClass("file-link-title-div-hidden")
    $("#create-file-link-title-div-" + file_id).addClass("file-link-title-div-hidden")
    $("#link-instance-file-divs").append(link_div)
}

function add_instance_file_popup_tr (file_id, instances, default_names, descriptions, urls) {
    const link_div = $("#link-instance-file-" + file_id)
    const checked = link_div.attr("data-linked") === "true"
    const names = {}

    let sample_id
    if (checked) {
        sample_id = "SAMPLE_LINKED_ID"
        const name_inputs = link_div.find("input.file-name-input")
        name_inputs.each(function () {
            names[$(this).attr("data-language-code")] = $(this).val()
        })
    } else {
        sample_id = "SAMPLE_ID"
    }

    const tr = $("#instance-file-popup-tr-" + sample_id).clone()
        .attr("id", "instance-file-popup-tr-" + file_id)
    tr.html(function (index, html) {
        html = html.replace(new RegExp(sample_id, "g"), file_id)
        $.each(instances, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_INSTANCE_" + key, "g"), val)
        })
        $.each(default_names, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_DEFAULT_NAME_" + key, "g"), val)
        })
        $.each(descriptions, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_DESCRIPTION_" + key, "g"), val)
        })
        $.each(urls, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_URL_" + key, "g"), val)
            if (val === "") {
                html = html.replace(
                    new RegExp("SAMPLE_URL_CSS_CLASS_" + key, "g"), "file-url-empty"
                )
            } else {
                html = html.replace(
                    new RegExp("SAMPLE_URL_CSS_CLASS_" + key, "g"), "file-url"
                )
            }
        })
        $.each(names, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_NAME_" + key, "g"), val)
        })
        return html
    })
    $("#add-instance-file-table > tbody").append(tr)
}

function add_existing_instance_file_to_popup (
    file_id, instance_id, instance_names, default_names, descriptions, urls
) {
    add_instance_file_popup_tr(file_id, instance_names, default_names, descriptions, urls)

    const edit_div = $("#edit-instance-file-SAMPLE_ID").clone()
        .attr("id", "edit-instance-file-" + file_id)
    edit_div.html(function (index, html) {
        html = html.replace(/SAMPLE_ID/g, file_id).replace(/SAMPLE_FORM/g, "main-form")
        $.each(default_names, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_DEFAULT_NAME_" + key, "g"), val)
        })
        $.each(descriptions, function (key, val) {
            html = html.replace(new RegExp("SAMPLE_DESCRIPTION_" + key, "g"), val)
        })
        return html
    })
    $.each(instance_names, function (key, val) {
        const select = edit_div.find("#instance-file-instance-" + file_id + "-" + key)
        select.val(instance_id)
    })
    $("#edit-instance-file-divs").append(edit_div)
}

function switch_button_mode_to_done (button_id) {
    const button = $(button_id)
    button.attr("title", "Closes edit exercise link menu")
    button.attr("onclick", "close_instance_file_menu();")
    button.attr("data-button-mode", "done")
    button.text("Done editing")
}

function update_instance_file_selects (file_id, select) {
    const instance_selects = $("#edit-instance-file-" + file_id).find("select.file-instance-select")
    const option_val = select.find("option:selected").val()
    instance_selects.val(option_val)
}

function add_new_instance_file_to_popup (file_id) {
    const instances = {}
    const default_names = {}
    const descriptions = {}
    const urls = {}
    const edit_div = $("#edit-instance-file-" + file_id)
    const instance_selects = edit_div.find("select.file-instance-select")
    const default_name_inputs = edit_div.find("input.file-default-name-input")
    const description_areas = edit_div.find("textarea.file-description-area")

    instance_selects.each(function () {
        instances[$(this).attr("data-language-code")] = $(this).find("option:selected").text()
    })

    default_name_inputs.each(function () {
        default_names[$(this).attr("data-language-code")] = $(this).val()
    })

    description_areas.each(function () {
        descriptions[$(this).attr("data-language-code")] = $(this).val()
        urls[$(this).attr("data-language-code")] = ""
    })

    add_instance_file_link_div(file_id, default_names)
    add_instance_file_popup_tr(file_id, instances, default_names, descriptions, urls)
    edit_div.find("div.edit-instance-file-title-div").css({ display: "block" })
    edit_div.find("div.create-instance-file-title-div").hide()
    edit_div.find("div.edit-instance-file-title-div h2").each(function () {
        const lang = $(this).parent().attr("data-language-code")
        $(this).text(
            "Edit instance file: " +
            edit_div.find("input[data-language-code=" + lang + "].file-default-name-input"
            ).val())
    })
    switch_button_mode_to_done("#done-button-" + file_id)
}

function create_new_instance_file_entry (file_id) {
    const translated_visible = $("#edit-instance-file-" + file_id + " translated-visible")
    const default_name = translated_visible.find("input.file-default-name-input").val()
    let already_exists = false

    $("div.popup div.admin-error").hide()
    $("#add-instance-file-table div.translated-visible label.instance-file-label").each(
        function () {
            if ($(this).text() === default_name) {
                already_exists = true
                return false
            }
        }
    )
    const file_error_div = $("#instance-file-error-" + file_id)
    if (already_exists) {
        file_error_div.text("Instance file by this name already exists")
        file_error_div.css({ display: "block" })
        return
    } else {
        file_error_div.hide()
    }

    add_new_instance_file_to_popup(file_id)
    $("div.edit-instance-file").hide()
    add_create_instance_file_div()
}

function switch_link_edit_button_mode (file_id) {
    const button = $("#link-edit-button-" + file_id)
    if (button.attr("data-button-mode") === "remove") {
        button.attr("title", "Includes the file to the linked files of the exercise")
        button.attr("onclick", "add_instance_file_to_exercise('" + file_id + "');")
        button.attr("data-button-mode", "add")
        button.text("Add link")
        button.prop("disabled", true)
    } else if (button.attr("data-button-mode") === "add") {
        button.attr("title", "Removes the file from the linked files of the exercise")
        button.attr("onclick", "remove_instance_file_from_exercise('" + file_id + "');")
        button.attr("data-button-mode", "remove")
        button.text("Remove link")
        button.prop("disabled", false)
    }
}

function add_instance_file_to_exercise (file_id) {
    if (!check_chmod_input_validity(
        "#instance-file-chmod-" + file_id, "#instance-file-chmod-error-" + file_id)
    ) {
        return
    } else {
        $("#instance-file-chmod-error-" + file_id).hide()
    }

    $("#link-instance-file-" + file_id).attr("data-linked", true)
    $("#instance-file-checkbox-" + file_id).prop("checked", true)
    $("#edit-file-link-title-div-" + file_id).removeClass("file-link-title-div-hidden")
    $("#create-file-link-title-div-" + file_id).addClass("file-link-title-div-hidden")
    switch_link_edit_button_mode(file_id)
}

function remove_instance_file_from_exercise (file_id) {
    const link_div = $("#link-instance-file-" + file_id)

    link_div.attr("data-linked", false)
    $("#instance-file-checkbox-" + file_id).prop("checked", false)
    $("#edit-file-link-title-div-" + file_id).addClass("file-link-title-div-hidden")
    $("#create-file-link-title-div-" + file_id).removeClass("file-link-title-div-hidden")

    link_div.find("input.file-name-input").val("")
    link_div.find("select.file-purpose-select").val("INPUT")
    link_div.find("select.file-chown-select").val("OWNED")
    link_div.find("select.file-chgrp-select").val("OWNED")
    link_div.find("input.file-chmod-input").val("rw-rw-rw-")
    switch_link_edit_button_mode(file_id)
}

function show_edit_instance_files_popup (event, url) {
    event.preventDefault()

    $.get(url, function (data, textStatus, jqXHR) {
        const popup = $("#edit-instance-files-popup")
        const error_span = $("#edit-instance-files-popup-error")
        const result = data.result
        const error = data.error

        if (error) {
            error_span.text(error)
            error_span.css({ display: "inline-block" })
            return
        } else {
            error_span.empty()
            error_span.hide()
        }

        $("div.popup div.admin-error").hide()
        $("#add-instance-file-table > tbody").empty()
        $("#edit-instance-file-divs").empty()
        $("#edit-instance-file-divs").css({ display: "block" })
        $("#link-instance-file-divs").hide()
        add_create_instance_file_div()

        $.each(result, function () {
            const file_id = "" + this.id
            add_existing_instance_file_to_popup(file_id, this.instance_id, this.instance_names, this.default_names,
                this.descriptions, this.urls)
        })
        popup.css({ opacity: "1", "pointer-events": "auto" })
    })
}

function update_instance_file_table_with_client_data (update_file_data) {
    const link_divs = $("#edit-instance-files-popup div.link-instance-file")
    const target_tbody = $("#instance-files-table tbody")

    link_divs.each(function () {
        const file_id = $(this).attr("data-file-id")
        let in_table = false
        let tr = null
        const linked = $(this).attr("data-linked") === "true"

        // Check if the file is in the instance file table of the exercise
        target_tbody.find("tr").each(function () {
            if ($(this).attr("data-file-id") === file_id) {
                tr = $(this)
                in_table = true
                return false
            }
        })

        const name_inputs = $(this).find("input.file-name-input")
        const purpose_display = $(this).find("select.file-purpose-select option:selected").text()
        const popup_tr = $("#instance-file-popup-tr-" + file_id)
        const instance_divs = popup_tr.find("td.instance-cell div")
        const description_divs = popup_tr.find("td.description-cell div")

        // If the file is in the table but is not linked, remove it from the table
        if (in_table && !linked) {
            tr.remove()
        // If the file is in the table and it is linked, update its link data displayed in the table
        } else if (in_table) {
            tr.find("td.name-cell span").each(function () {
                $(this).text(name_inputs.filter("input[data-language-code=" + $(this)
                    .attr("data-language-code") + "]").val())
            })
            tr.find("td.purpose-cell").text(purpose_display)
        } else if (linked) { // If the file is not in the table but is linked, add it to the table
            tr = $("#instance-file-tr-" + "SAMPLE_ID").clone()
                .attr("id", "instance-file-tr-" + file_id)
            tr.attr("data-file-id", file_id)
            tr.html(function (index, html) {
                html = html.replace(/SAMPLE_ID/g, file_id)
                    .replace(/SAMPLE_GET_PURPOSE_DISPLAY/g, purpose_display)
                $.each(name_inputs, function () {
                    sample_str = "SAMPLE_NAME_" + $(this).attr("data-language-code")
                    html = html.replace(new RegExp(sample_str, "g"), $(this).val())
                })
                if (update_file_data) {
                    $.each(instance_divs, function () {
                        sample_str = "SAMPLE_INSTANCE_NAME_" + $(this).attr("data-language-code")
                        html = html.replace(new RegExp(sample_str, "g"), $(this).text())
                    })
                    $.each(description_divs, function () {
                        sample_str = "SAMPLE_DESCRIPTION_" + $(this).attr("data-language-code")
                        html = html.replace(new RegExp(sample_str, "g"), $(this).val())
                    })
                }
                return html
            })
            target_tbody.append(tr)
        }
    })
}

function close_popup_and_add_instance_files (instance_files, default_lang) {
    const target_tbody = $("#instance-files-table tbody")
    $("#add-instance-file-table > tbody input.instance-file-checkbox").each(function (index) {
        const file_id = $(this).attr("data-file-id")
        const default_name = $("#instance-file-default-name-" + file_id + "-" + default_lang).val()
        const link_div = $("#link-instance-file-" + file_id)
        let db_id = ""
        let db_instances = []
        const db_description = []
        let saved = false

        // Check if the instance file was saved properly
        $.each(instance_files, function (index, db_file) {
            if (db_file.default_names[default_lang] === default_name) {
                db_id = "" + db_file.id
                db_instances = db_file.instance_names
                db_descriptions = db_file.descriptions
                saved = true
                return false
            }
        })

        // If it wasn't, skip it and remove its link div from the popup
        if (!saved) {
            link_div.remove()
            return
        }

        refresh_id_occurences_in_subtree(file_id, db_id, link_div)

        const checked = $(this).prop("checked")
        const name_inputs = link_div.find("input.file-name-input")
        const purpose_display = link_div.find("select.file-purpose-select option:selected").text()
        let tr = null
        let in_table = false

        // Check if the file is in the instance file table of the exercise
        target_tbody.find("tr").each(function () {
            if ($(this).attr("data-file-id") === db_id) {
                tr = $(this)
                in_table = true
                return false
            }
        })

        // If the file is in the table but not checked in the popup, it must be removed from the table
        if (in_table && !checked) {
            tr.remove()
        // If the file is in the table and checked in the popup, it must be updated in the table
        } else if (in_table) {
            tr.find("td.name-cell span").each(function () {
                $(this).text(name_inputs.find("[data-language-code=" + $(this)
                    .attr("data-language-code") + "]").val())
            })
            tr.find("td.instance-cell span").each(function () {
                $(this).text(db_instances[$(this).attr("data-language-code")])
            })
            tr.find("td.purpose-cell").text(purpose_display)
            tr.find("td.description-cell span").each(function () {
                $(this).text(db_descriptions[$(this).attr("data-language-code")])
            })
        // If the file is not in the table but is checked in the popup, it must be added to the table
        } else if (checked) {
            tr = $("#instance-file-tr-" + "SAMPLE_ID").clone()
                .attr("id", "instance-file-tr-" + db_id)
            tr.attr("data-file-id", db_id)
            tr.html(function (index, html) {
                html = html.replace(/SAMPLE_ID/g, db_id)
                    .replace(/SAMPLE_GET_PURPOSE_DISPLAY/g, purpose_display)
                $.each(db_instances, function (key, val) {
                    sample_str = "SAMPLE_INSTANCE_NAME_" + key
                    html = html.replace(new RegExp(sample_str, "g"), val)
                })
                $.each(name_inputs, function () {
                    sample_str = "SAMPLE_NAME_" + $(this).attr("data-language-code")
                    html = html.replace(new RegExp(sample_str, "g"), $(this).val())
                })
                $.each(db_descriptions, function (key, val) {
                    sample_str = "SAMPLE_DESCRIPTION_" + key
                    html = html.replace(new RegExp(sample_str, "g"), val)
                })
                return html
            })
            target_tbody.append(tr)
        }
    })
    close_popup($("#edit-instance-files-popup"))
    refresh_required_files_all()
}

function close_instance_file_popup () {
    const popup = $("#edit-instance-files-popup")
    const link_divs = popup.find("div.link-instance-file")
    const remove_divs = $()

    link_divs.each(function () {
        const file_id = $(this).attr("data-file-id")
        // If the file was just added to the popup, mark its link div to be removed
        if (file_id.startsWith("new")) {
            remove_divs.add($(this))
        }
    })
    remove_divs.remove()
    update_instance_file_table_with_client_data(true)
    close_popup(popup)
}

function edit_instance_file_form_success (data, text_status, jqxhr_obj, default_lang) {
    const ID_PATTERN = /\[(.*?)\]/
    if (data.error) {
        const sep = "<br>"
        $.each(data.error, function (err_source, err_msg) {
            let error_div = $("#instance-file-error")
            let file_id
            if (err_source !== "__all__") {
                file_id = err_source.match(ID_PATTERN)[1]
                if (err_source.startsWith("instance_file_file")) {
                    error_div = $("#instance-file-file-error-" + file_id)
                } else if (err_source.startsWith("instance_file_default_name")) {
                    error_div = $("#instance-file-default-name-error-" + file_id)
                } else if (err_source.startsWith("instance_file_description")) {
                    error_div = $("#instance-file-description-error-" + file_id)
                }
            }
            error_div.html(err_msg.join(sep))
            error_div.css("display", "block")
            show_instance_file_edit_menu(file_id)
        })
    } else if (data.result) {
        console.log("Instance files edited successfully!")
        close_popup_and_add_instance_files(data.result, default_lang)
    }
}

function edit_instance_file_form_error (xhr, status, type) {
    const error_span = $("#instance-file-error")
    let error_str = "An error occured while sending the form:"
    status = status.charAt(0).toUpperCase() + status.slice(1)
    if (type) {
        error_str += status + ": " + type
    } else {
        error_str += status
    }
    error_span.html(error_str)
    error_span.css("display", "block")
}

function submit_edit_instance_files_form (e, default_lang) {
    e.preventDefault()
    console.log("User requested instance file form submit.")

    $("div.popup div.admin-error").hide()

    const form = $("#edit-instance-files-form")
    const form_type = form.attr("method")
    const form_url = form.attr("action")

    console.log("Method: " + form_type + ", URL: " + form_url)

    const form_data = new FormData(form[0])
    const new_file_ids = []
    $("div.popup input[type=checkbox].instance-file-checkbox").each(function () {
        const id = $(this).attr("data-file-id")
        if (id.startsWith("new")) {
            new_file_ids.push(id)
        }
    })
    console.log("Serialized form data:")

    const create_id = "[new-" + (instance_file_enum - 1) + "]"
    const form_keys = []
    for (const key of form_data.keys()) {
        form_keys.push(key)
    }

    for (const key of form_keys) {
        if (key.indexOf(create_id) > -1) {
            form_data.delete(key)
        }
    };

    for (const [key, value] of form_data.entries()) {
        console.log(key, value)
    }
    form_data.append("new_instance_files", new_file_ids.join(","))

    console.log("Submitting the form...")
    $.ajax({
        type: form_type,
        url: form_url,
        data: form_data,
        processData: false,
        contentType: false,
        dataType: "json",
        success: function (data, textStatus, jqXHR) {
            edit_instance_file_form_success(data, textStatus, jqXHR, default_lang)
        },
        error: edit_instance_file_form_error
    })
}

/**************************************************
* File upload exercise tests, stages and commands *
**************************************************/

// TODO: Generalise the *_name_changed - they're pretty similar
function test_name_changed (e) {
    const input_id = e.target.id
    const split_id = input_id.split("-")
    const new_name = e.target.value

    $("#test-" + split_id[1]).html(new_name)
}

function stage_name_changed (e, lang_choice) {
    const input_id = e.target.id
    const split_id = input_id.split("-")
    const new_name = e.target.value

    $("#stage-" + split_id[1] + "[data-language-code=\"" + lang_choice + "\"]").html(new_name)
}

function command_name_changed (e, lang_choice) {
    const input_id = e.target.id
    const split_id = input_id.split("-")
    const new_name = e.target.value

    $("#command-" + split_id[1] + "[data-language-code=\"" + lang_choice + "\"]").html(new_name)
}

function refresh_required_files_all () {
    // For each test ...
    $("#test-tabs > ol > li").each(function (x) {
        const current_href = $(this).children("a").attr("href")
        if (current_href !== undefined) {
            const current_id = current_href.split("-")[2]
            refresh_required_files(current_id)
        }
    })
}

function refresh_required_files (test_id) {
    const lang = $("#language-info-code").text()
    const ins_optgrp = $(
        "#test-" + test_id + "-required_files > optgroup.filepicker-instance-options"
    )
    const new_ins_options = []
    $("#instance-files-table tbody > tr").map(function () {
        const current_row = $(this)
        const if_id = current_row.attr("data-file-id")
        const if_name = current_row.find(
            "td.name-cell > span[data-language-code=\"" + lang + "\"]"
        ).html()

        const existing_if = ins_optgrp.find("option[value=\"if_" + if_id + "\"]")
        if (existing_if.length === 0) {
            // Add this file option if it doesn't already exist
            const new_opt = $("<option value=\"if_" + if_id + "\">" + if_name + "</option>")
            ins_optgrp.append(new_opt)
        } else if (existing_if.length === 1) {
            // Update the name
            existing_if.html(if_name)
        }

        new_ins_options.push("if_" + if_id)
    })
    ins_optgrp.children("option").each(function () {
        const current = $(this)
        if (new_ins_options.indexOf(current.val()) === -1) {
            current.remove()
        }
    })

    const exe_optgrp = $(
        "#test-" + test_id + "-required_files > optgroup.filepicker-exercise-options"
    )
    const new_exe_options = []
    $("#include-file-popups > div.popup").map(function () {
        const current_div = $(this)
        const ef_id = current_div.attr("data-file-id")
        const ef_name = current_div.find("#included-file-name-" + ef_id + "-" + lang).val()

        // Add this file if it doesn't already exist
        const existing_ef = exe_optgrp.find("option[value=\"ef_" + ef_id + "\"]")
        if (existing_ef.length === 0) {
            const new_opt = $("<option value=\"ef_" + ef_id + "\">" + ef_name + "</option>")
            exe_optgrp.append(new_opt)
        } else if (existing_ef.length === 1) {
            // Update the name
            existing_ef.html(ef_name)
        }

        new_exe_options.push("ef_" + ef_id)
    })
    exe_optgrp.children("option").each(function () {
        const current = $(this)
        if (new_exe_options.indexOf(current.val()) === -1) {
            current.remove()
        }
    })
}

// TODO: Generalise the add_(test|stage|command)? Use the latter functions in the former
let test_enum = 1

function add_test () {
    const new_id = "newt" + test_enum
    const new_name = "New test"
    const new_stage_id = "news" + stage_enum
    const new_cmd_id = "newc" + cmd_enum

    const test_tablist = $("#test-tabs > ol:first-child")
    // TODO: The new test tab item should be included in the template section and cloned.

    const new_test_tab_item = $(
        "<li id=\"test-li-" + new_id + "\">" +
          "<a href=\"#test-tabs-" + new_id + "\" id=\"test-" + new_id + "\">" + new_name + "</a>" +
          "<button class=\"delete-button\" type=\"button\" title=\"Delete this test\"" +
                  "onclick=\"delete_test('" + new_id + "');\">x</button>" +
      "</li>"
    )
    new_test_tab_item.insertBefore("li.test-tab-button-container")

    // Create the new test tab
    const new_test_tab = $("#test-tabs-SAMPLE_TEST_ID").clone().attr("id", "test-tabs-" + new_id)
    new_test_tab.html(function (index, html) {
        return (
            html.replace(/SAMPLE_TEST_ID/g, new_id)
                .replace(/SAMPLE_STAGE_ID/g, new_stage_id)
                .replace(/SAMPLE_COMMAND_ID/g, new_cmd_id)
                .replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, "1")
                .replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, "1")
        )
    })
    $("#test-tabs").append(new_test_tab)

    refresh_required_files(new_id)
    $("#test-tabs").tabs("refresh")
    $("#stages-sortable-" + new_id).sortable()
    $("#stages-sortable-" + new_id).disableSelection()
    $("#commands-sortable-" + new_id + "-" + new_stage_id).sortable()
    $("#commands-sortable-" + new_id + "-" + new_stage_id).disableSelection()

    test_enum++
    stage_enum++
    cmd_enum++
}

let stage_enum = 1

function add_stage (test_id) {
    const new_id = "news" + stage_enum
    const stage_list = $("#stages-sortable-" + test_id)
    const stage_ordnum = stage_list.children().length + 1
    const cmd_ordnum = 1

    // Create the new stage and a command to the list
    // <li class="ui-state-default" data-stage-id="SAMPLE_STAGE_ID">
    const new_cmd_id = "newc" + cmd_enum
    const new_stage_list_item = $("li[data-stage-id=\"SAMPLE_STAGE_ID\"]")
        .clone().attr("data-stage-id", new_id)
    new_stage_list_item.html(function (index, html) {
        return html.replace(/SAMPLE_TEST_ID/g, test_id).replace(/SAMPLE_STAGE_ID/g, new_id)
            .replace(/SAMPLE_COMMAND_ID/g, new_cmd_id)
    })
    stage_list.append(new_stage_list_item)

    const new_cmd_list = $("#commands-sortable-" + test_id + "-" + new_id)

    // Create the information box to the right side of the list for the new command
    const new_cmd_info = $("#command-information-SAMPLE_COMMAND_ID").clone()
        .attr("id", "command-information-" + new_cmd_id)
    new_cmd_info.html(function (index, html) {
        return (
            html.replace(/SAMPLE_COMMAND_ID/g, new_cmd_id)
                .replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum)
                .replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, cmd_ordnum)
        )
    })
    $("#selection-information-container-" + test_id).append(new_cmd_info)

    // Create the information box to the right side of the list for the new stage
    const new_stage_info = $("#stage-information-SAMPLE_STAGE_ID").clone()
        .attr("id", "stage-information-" + new_id)
    new_stage_info.html(function (index, html) {
        return (
            html.replace(/SAMPLE_STAGE_ID/g, new_id)
                .replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum)
        )
    })
    $("#selection-information-container-" + test_id).append(new_stage_info)

    new_cmd_list.sortable()
    new_cmd_list.disableSelection()
    cmd_enum++

    stage_list.sortable("refresh")
    stage_enum++
}

let cmd_enum = 1

function add_command (test_id, stage_id) {
    const new_id = "newc" + cmd_enum
    const cmd_list = $("#commands-sortable-" + test_id + "-" + stage_id)
    const cmd_ordnum = cmd_list.children().length + 1
    const stage_list = $("#stages-sortable-" + test_id)
    const stage_ordnum = stage_list.children("li[data-stage-id=" + stage_id + "]").index() + 1

    // Create the new command to the list
    const new_cmd_list_item = $("li[data-command-id=\"SAMPLE_COMMAND_ID\"]").clone()
        .attr("data-command-id", new_id)
    new_cmd_list_item.html(function (index, html) {
        return html.replace(/SAMPLE_COMMAND_ID/g, new_id)
    })
    cmd_list.append(new_cmd_list_item)

    // Create the information box to the right side of the list
    const new_cmd_info = $("#command-information-SAMPLE_COMMAND_ID").clone()
        .attr("id", "command-information-" + new_id)
    new_cmd_info.html(function (index, html) {
        return (
            html.replace(/SAMPLE_COMMAND_ID/g, new_id)
                .replace(/SAMPLE_STAGE_ORDINAL_NUMBER/g, stage_ordnum)
                .replace(/SAMPLE_COMMAND_ORDINAL_NUMBER/g, cmd_ordnum)
        )
    })
    $("#selection-information-container-" + test_id).append(new_cmd_info)

    stage_list.sortable("refresh")
    cmd_list.sortable("refresh")
    cmd_enum++
}

function show_stagecmd_information (event) {
    const clicked_id = event.target.id
    const split_id = clicked_id.split("-")
    const clicked_type = split_id[0]
    const clicked_number = split_id[1]
    $("div.selection-information").hide()
    $("#" + clicked_type + "-information-" + clicked_number).show()
}

// TODO: Use the latter function in the former when applicable in delete_(test|stage|command)
function delete_test (test_id) {
    // TODO: A popup asking, if the user really wants to delete the test
    //       and its stages and commands.
    // TODO: Must not be able to delete tests that contain stages, that are
    //       dependencies for stages in other tests.

    // Delete the test tab selector and refresh the tabs
    $("#test-" + test_id).parent().remove()
    $("#test-tabs").tabs("refresh")

    // Delete the test tab contents
    $("#test-tabs-" + test_id).remove()
}

function delete_stage (test_id, stage_id) {
    // Same TODO as with test deletion

    // Get the associated commands ids
    const command_ids = $("#commands-sortable-" + test_id + "-" + stage_id + " > li").map(
        function () { return $(this).attr("data-command-id") }
    ).get()

    // Delete the stage from the stage list and refresh the sortable
    $("li[data-stage-id=\"" + stage_id + "\"]").remove()
    $("#stages-sortable-" + test_id).sortable("refresh")

    // Delete the stage info from the right side
    $("#stage-information-" + stage_id).remove()

    // Delete the associated commands' infos from the right side
    for (let i = 0; i < command_ids.length; i++) {
        $("#command-information-" + command_ids[i]).remove()
    }
}

function delete_command (test_id, stage_id, command_id) {
    // Same TODO as with the stage deletion

    // Delete the command from the command list and refresh the sortable
    $("li[data-command-id=\"" + command_id + "\"]").remove()
    $("#commands-sortable-" + test_id + "-" + stage_id).sortable("refresh")

    // Delete the command info from the right side
    $("#command-information-" + command_id).remove()
}

function show_preview (button, lang) {
    event.preventDefault()

    const caller = $(button)
    const textArea = $("textarea[name*='content_" + lang + "']")
    const questionArea = $("textarea[name*='question_" + lang + "']")
    const url = caller.attr("data-url")
    const popup = $("div#preview-popup")
    const csrf = $("form").find("input[name*='csrfmiddlewaretoken']").attr("value")

    $.ajax({
        type: "POST",
        url,
        data: {
            csrfmiddlewaretoken: csrf,
            content: textArea.val(),
            question: questionArea.val(),
            embedded: true,
            form_template: "courses/file-upload-exercise.html"
        },
        dataType: "json",
        success: function (data, text_status, jqxhr_obj) {
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
            popup.children(".content-preview").html(data)
            add_line_numbers()
        },
        error: function (jqxhr_obj, status, type) {
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
            popup.children(".content-preview").html(jqxhr_obj.responseText)
        }
    })
}

$(document).ready(function () {
    $("#preview-popup").click(function () {
        $(this).css({ opacity: "0", "pointer-events": "none" })
    })
    $("#preview-popup > div").click(function (event) {
        event.stopPropagation()
    })
})
