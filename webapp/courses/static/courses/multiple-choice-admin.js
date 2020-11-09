function show_preview(event, a) {
    event.preventDefault();
    
    let caller = $(a)
    let textArea = caller.parent().next("div").children("textarea");
    let lang = textArea.attr("name").slice(-2);
    let questionArea = $("textarea[name*='question_" + lang + "']");
    let choices = $("textarea[name$='answer_" + lang + "']").map(function() {
        return $(this).val();
    }).get();
    let url = caller.attr("href");
    let popup = $("div.popup");
    let csrf = $("form").find("input[name*='csrfmiddlewaretoken']").attr("value");
    
    $.ajax({
        type: "POST",
        url: url,
        data: {
            csrfmiddlewaretoken: csrf,
            content: textArea.val(),
            question: questionArea.val(),
            choices: choices,
            embedded: true,
            form_template: "courses/multiple-choice-exercise.html",
        },
        dataType: "json",
        success: function(data, text_status, jqxhr_obj) {
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
            popup.children(".content-preview").html(data);
            add_line_numbers();
        },
        error: function(jqxhr_obj, status, type) {
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
            popup.children(".content-preview").html(jqxhr_obj.responseText);
        }
    });
}
