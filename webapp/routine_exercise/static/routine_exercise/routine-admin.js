function show_preview (event, a) {
    event.preventDefault()

    const caller = $(a)
    const textArea = caller.parent().next("div").children("textarea")
    const lang = textArea.attr("name").slice(-2)
    const questionArea = $("textarea[name*='question_" + lang + "']")
    const url = caller.attr("href")
    const popup = $("div.popup")
    const csrf = $("form").find("input[name*='csrfmiddlewaretoken']").attr("value")
    let answerWidget = $("select[name='answer_widget']").val();

    $.ajax({
        type: "POST",
        url,
        data: {
            csrfmiddlewaretoken: csrf,
            content: textArea.val(),
            question: questionArea.val(),
            embedded: true,
            answer_widget: answerWidget ? answerWidget : "textfield"
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
