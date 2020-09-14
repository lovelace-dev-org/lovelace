function show_reminders(data) {
    $("#reminder-list-title").show();
    let ul = $("ul.preview-list");
    data.reminders.forEach(function (student) {
        ul.append("<li class='student-bullet'>" +
            student.last_name + " " + student.first_name +
            " (" + student.username +
            student.email + ") - " +
            student.missing_count + "</li>"
        );
    });
    $("textarea").attr("readonly", true);
    $("input[name*=reminder_action").attr("value", "send");
    let submit_button = $("input#reminder-submit").detach();
    submit_button.attr("value", data.submit_text);
    submit_button.attr("disabled", false);
    ul.after(submit_button);
}

function submit_reminders(event) {
    event.preventDefault();

    let form = $(this);
    let url = form.attr('action');
    let cb;
    if ($("input[name*=reminder_action").attr("value") == "send") {
        cb = process_progress;
        $("input#reminder-submit").attr("disabled", true);
    }
    else {
        cb = show_reminders;
    }

    $.ajax({
        type: form.attr('method'),
        url: url,
        data: new FormData(form[0]),
        processData: false,
        contentType: false, 
        dataType: 'json', 
        success: cb,
        error: function (xhr, status, type) {
        }
    });
}
   
function load_reminders(event, a) {
    event.preventDefault();
    
    let link = $(a);

    $.ajax({
        url: link.attr("href"),
        success: show_reminders,
        error: function (xhr, status, type) {
        }
    });
}

function discard_reminders(event, a) {
    event.preventDefault();
    
    let link = $(a);
    let form = $("#reminder-form");
    let csrf = form.children("input[name*='csrfmiddlewaretoken']").attr("value");
    
    $.ajax({
        url: link.attr("href"),
        data: {csrfmiddlewaretoken: csrf},
        dataType: 'json',
        success: function (data, status, xhr) {
            $("a.reminder-action").hide();
            let submit_button = $("input#reminder-submit").detach()
            $("div#reminder-list-title").empty().before(submit_button);
            $("ul.preview-list").empty();
            submit_button.attr("disabled", false);
            submit_button.attr("value", data.submit_text);
        },
        error: function (xhr, status, type) {
        }
    });
}

function poll_progress(url) {
    setTimeout(function () {
        $.ajax({
            url: url,
            success: function (data, text_status, jqxhr) {
                process_progress(data);
            },
            error: function (jqxhr, status, type) {
                process_error(status);
            }
        });
    }, 500);
}

function process_progress(data) {
    if (data.state == "SUCCESS") {
        $("div.task-progress").text(data.metadata.current + " / " + data.metadata.total);
        if (data.metadata.aborted) {
            $("div.task-progress").after(
                "<div class='task-error'>" + data.metadata.aborted + "</div>"
            )
            $("input#reminder-submit").attr("disabled", false);
        }
    }
    else if (data.state == "PROGRESS") {
        $("div.task-progress").text(data.metadata.current + " / " + data.metadata.total);
        poll_progress(data.redirect);
    }
    else if (data.state == "FAILURE") {
        $("div.task-error").text(data.metadata);
    }
    else if (data.state == "PENDING") {
        $("div.task-progress").text("...");
        poll_progress(data.redirect);
    }
}

$(document).ready(function() {
    $("#reminder-form").submit(submit_reminders);
});