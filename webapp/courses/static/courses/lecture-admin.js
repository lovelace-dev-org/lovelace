function show_preview(event, a) {
    event.preventDefault();
    
    let caller = $(a)
    let textArea = caller.parent().next("div").children("textarea");
    let url = caller.attr("href");
    let popup = $("div.popup");
    let csrf = $("form").find("input[name*='csrfmiddlewaretoken']").attr("value");
    
    $.ajax({
        type: "POST",
        url: url,
        data: {csrfmiddlewaretoken: csrf, content: textArea.val()},
        dataType: "json",
        success: function(data, text_status, jqxhr_obj) {
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
            popup.children(".content-preview").html(data);
        },
        error: function(jqxhr_obj, status, type) {
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
            popup.children(".content-preview").html(jqxhr_obj.responseText);
        }
    });
}
