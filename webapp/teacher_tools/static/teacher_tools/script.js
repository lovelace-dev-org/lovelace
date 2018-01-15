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
        success: process_success_one,
        error: function(xhr, status, type) {
            console.log(xhr);
            let popup = $("#status-msg-popup");
            popup.children("div").html(status);
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
        }
    });        
}

function process_many(event) {
    event.preventDefault();
    
    var form = $(".teacher-form");
    
    $.ajax({
        type: form.attr('method'),
        url: form.attr('action'),
        data: form.serialize(),
        dataType: 'json',
        success: process_success_many,
        error: function(xhr, status, type) {
            console.log(xhr);
            let popup = $("#status-msg-popup");
            popup.children("div").html(status);
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
        }
    }); 
}
    

function change_state(username, new_state) {
 
    let tr = $("table.enrollments-table").children("tbody").children("#" + username + "-tr");
    let state_cell = tr.children(".state-cell");
    let controls_cell = tr.children(".controls-cell");
    
    state_cell.html(new_state);
    
    if (new_state == "ACCEPTED") {
        controls_cell.html(
            '<button class="enrollment-expel-button" onclick="process_one(event, this, \'expelled\')">expel</button></td>'
        );            
    }
    else if (new_state == "WAITING") {
        controls_cell.html(
            '<button class="enrollment-accept-button" onclick="process_one(event, this, \'accepted\')">accept</button><button class="enrollment-deny-button" onclick="process_one(event, this, \'denied\')">deny</button>'
        );
    }
    else {
        controls_cell.html(
            '<button class="enrollment-accept-button" onclick="process_one(event, this, \'accepted\')">accept</button>'
        );
    }        
}
    
function process_success_one(response, status, jqxhr_obj) {
    let popup = $("#status-msg-popup");
    popup.children("div").html(response.msg);
    popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});    
    
    change_state(response.user, response.new_state);
}

function process_success_many(response, status, jqxhr_obj) {
    console.log(response);
    
    let popup = $("#status-msg-popup");
    let log = "";
    if (response["users-affected"].length > 0) {
        log += "<h3>" + response["affected-title"] + "</h3>";
    
        response["users-affected"].forEach(function(username) {
            log += username + "<br>";
            change_state(username, response.new_state);
        })
    }
    
    if (response["users-skipped"].length > 0) {
        log += "<h3>" + response["skipped-title"] + "</h3>";
    
        response["users-skipped"].forEach(function(username) {
            log += username + "<br>";
        })
    }    
    
    popup.children("div").html(log);
    popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});    
}


// http://blog.niklasottosson.com/?p=1914
function sort_enrollments(event, field, order) {
    event.preventDefault();
    
    let rows = $("table.enrollments-table tbody tr").get();
    
    rows.sort(function(a, b) {
        let A = $(a).children("td").eq(field).text().toUpperCase();
        let B = $(b).children("td").eq(field).text().toUpperCase();
        
        if (A < B) {
            return -1 * order;
        }
        else if (A > B) {
            return 1 * order;
        }
        else {
            return 0;
        }
    });
    
    rows.forEach(function(row) {
        $("table.enrollments-table").children("tbody").append(row);
    });
}


$(document).ready(function() {
    
    $(".teacher-form").submit(process_many);
    
});