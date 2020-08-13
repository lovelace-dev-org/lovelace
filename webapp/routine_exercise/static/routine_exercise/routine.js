function get_routine_question(e, url) {
    let button = $(e.target);
    let exercise = button.parent();
    //console.log(exercise);
    //let csrf_token = exercise.find("form > input[name=csrfmiddlewaretoken]");
    let rendered_template = exercise.find("div.routine-template");
    let progress = exercise.find("span.rt-progress-tag");
    rendered_template.html('');
    var hints_div = exercise.children("div.question").children("div.hints");
    var result_div = exercise.children("div.question").children("div.result");
    var msgs_div = exercise.children("div.question").children("div.msgs");
    
    //console.log(hints_div);
    hints_div.find('div.hints-list').html("");
    hints_div.css("display", "none");
    msgs_div.find('div.msgs-list').html("");
    msgs_div.css("display", "none");
    result_div.html("");
    result_div.css("display", "none");

    if (!url) {
        url = button.attr("data-url")
    }

    $.ajax({
        type: 'GET',
        url: url,
        success: function(data, text_status, jqxhr_obj) {
            console.log(data);
            if (data.question) {
                rendered_template.html(data.question);
                progress.html(data.progress);
            }
            if (data.redirect) {
                setTimeout(function() {
                    get_routine_question(e, data.redirect);
                }, 1000);
            }
        },
        error: function(xhr, status, type) {
            console.log(status);
        }
    });

    let input_element = exercise.find("form :input");
    input_element.prop("disabled", false);
    input_element[1].focus();
    $(input_element[1]).val("");
    button.prop("disabled", true);
}

