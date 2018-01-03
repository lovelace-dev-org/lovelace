function process_one(event, button, action) {
    event.preventDefault();
    
    var tr = $(button).parent().parent();
    var form = $(".teacher-form");
    var username = tr.children(".username-cell").html();
    var csrf = form.children("input[name*='csrfmiddlewaretoken']").attr("value");
    
    $.ajax({
        type: form.attr('method'),
        url: form.attr('action'),
        data: {username: username, action: action, csrfmiddlewaretoken: csrf},
        dataType: 'json',
        success: function(data, text_status, jqxhr_obj) {
            process_success(data);
        },
        error: function(xhr, status, type) {
            console.log(xhr);
            let popup = $("#status-msg-popup");
            popup.children("div").html(status);
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
        }
    });        
}

function process_success(response) {
    let popup = $("#status-msg-popup");
    popup.children("div").html(response.msg);
    popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});    
    
    let tr = $("table.enrollments-table").children("tbody").children("#" + response.user + "-tr");
    let state_cell = tr.children(".state-cell");
    let controls_cell = tr.children(".controls-cell");
    
    state_cell.html(response.new_state);
    
    if (response.new_state == "ACCEPT") {
        controls_cell.html(
            '<button class="enrollment-expel-button" onclick="process_one(event, this, \'expel\')">expel</button></td>'
        );            
    }
    else if (response.new_state == "WAITING") {
        controls_cell.html(
            '<button class="enrollment-accept-button" onclick="process_one(event, this, \'accept\')">accept</button><button class="enrollment-deny-button" onclick="process_one(event, this, \'deny\')">deny</button>'
        );
    }
    else {
        controls_cell.html(
            '<button class="enrollment-accept-button" onclick="process_one(event, this, \'accept\')">accept</button>'
        );
    }        
}