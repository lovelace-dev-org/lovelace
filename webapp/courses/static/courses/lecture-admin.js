function show_preview (event, a) {
    event.preventDefault()

    const caller = $(a)
    const textArea = caller.parent().next("div").children("textarea")
    const url = caller.attr("href")
    const popup = $("div.popup")
    const csrf = $("form").find("input[name*='csrfmiddlewaretoken']").attr("value")

    $.ajax({
        type: "POST",
        url,
        data: { csrfmiddlewaretoken: csrf, content: textArea.val() },
        dataType: "json",
        success: function (data, text_status, jqxhr_obj) {
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
            popup.children(".content-preview").html(data)
        },
        error: function (jqxhr_obj, status, type) {
            popup.css({ opacity: "1", "pointer-events": "auto", overflow: "scroll" })
            popup.children(".content-preview").html(jqxhr_obj.responseText)
        }
    })
}
