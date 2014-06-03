function getXHR() {
    var xhr;

    //Browser Support Code
    try {
        // Opera 8.0+, Firefox, Safari
        xhr = new XMLHttpRequest();
    } catch (e) {
        // Internet Explorer Browsers
        try {
            xhr = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
            try{
                xhr = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (e){
                // Something went wrong
                alert("Your browser doesn't support AJAX!");
                return false;
            }
        }
    }
    return xhr;
}

function reserveSlot(e, calendar_id, event_id) {
    e.preventDefault(); // Prevent the form from submitting
    var xhr = getXHR();

    var csrftoken = $('div#calendar_' + calendar_id + ' form#event_' + event_id + ' input[name="csrfmiddlewaretoken"]').val();

    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4 && xhr.status == 200) {
            $('div#calendar_' + calendar_id + ' form#event_' + event_id + ' div.result').html(xhr.responseText);
            $('div#calendar_' + calendar_id + ' form#event_' + event_id + ' :input').attr("disabled", true);
        }
    }

    var data = "csrfmiddlewaretoken=" + csrftoken;
    data += "&reserve=1"
    var datalen = data.length;
    var mimetype = "application/x-www-form-urlencoded";

    xhr.open("POST", "/calendar/" + calendar_id + "/" + event_id + "/", true);
    xhr.setRequestHeader("Content-type", mimetype);
    xhr.setRequestHeader("Content-length", datalen);
    xhr.setRequestHeader("Connection", "close");
    xhr.setRequestHeader("X_REQUESTED_WITH", "XMLHttpRequest");
    xhr.send(data);
    $('div#calendar_' + calendar_id + 'form#event_' + event_id + ' div.result').html("Reservation sent, awaiting for confirmation.");
}

function cancelSlot(e, calendar_id, event_id) {
    e.preventDefault(); // Prevent the form from submitting
    var xhr = getXHR();

    var csrftoken = $('div#calendar_' + calendar_id + ' form#event_' + event_id + ' input[name="csrfmiddlewaretoken"]').val();

    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4 && xhr.status == 200) {
            $('div#calendar_' + calendar_id + ' form#event_' + event_id + ' div.result').html(xhr.responseText);
        }
    }

    var data = "csrfmiddlewaretoken=" + csrftoken;
    data += "&cancel=1"
    var datalen = data.length;
    var mimetype = "application/x-www-form-urlencoded";

    xhr.open("POST", "/calendar/" + calendar_id + "/" + event_id + "/", true);
    xhr.setRequestHeader("Content-type", mimetype);
    xhr.setRequestHeader("Content-length", datalen);
    xhr.setRequestHeader("Connection", "close");
    xhr.setRequestHeader("X_REQUESTED_WITH", "XMLHttpRequest");
    xhr.send(data);
    $('div#calendar_' + calendar_id + 'form#event_' + event_id + ' div.result').html("Cancellation sent, awaiting for confirmation.");
}
