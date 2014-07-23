// TODO: Use the following code
// http://stackoverflow.com/questions/7335780/how-to-post-a-django-form-with-ajax-jquery
function x_validateAnswer(form_id) {
    // TODO: File uploads.
    var answer_form = $('#' + form_id);
    answer_form.submit(function(event) {
        event.preventDefault();
        $.ajax({
            type: answer_form.attr('method'),
            url: answer_form.attr('action'),
            data: answer_form.serialize(),
            success: function(data) {
                $('#' + result_div_id).html(data);
            },
            error: function(data) {
                $('#' + error_div_id).html("XHR Error!");
            }
        }
    }
}

function validateAnswer(e, answer_check_url, task_name) {
    e.preventDefault(); // Prevent the form from submitting
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

    var form = document.getElementById('task_form');
    var csrftoken = form.elements["csrfmiddlewaretoken"].value;

    //var task_name = $('div.question').attr('id');
    var task = $('div#' + task_name);

    var rbchoices = $('div#' + task_name + ' form#task_form input.task_radio'); //document.getElementsByName(''); // Radio
    var cbchoices = $('div#' + task_name + ' form#task_form input.task_check'); // Checkbox
    var answer = $('div#' + task_name + ' form#task_form textarea.task_text'); //document.getElementsByName(''); // Textarea

    var file_element = $('div#' + task_name + ' form#task_form input[name="file"]');
    if (file_element) {
        var filename = file_element.val();
        var collaborators = $('div#' + task_name + ' form#task_form input[name="collaborators"]');
        if (collaborators.val()) {
            collaborators = collaborators.val(); // encodeURIComponent(collaborators.val()).replace(/%20/g, "+");
        } else {
            collaborators = "";
        }
    }

    var data = "csrfmiddlewaretoken=" + csrftoken;
    var data_add = "";

    for(var i=0; i < rbchoices.length; i++) {
        //alert(rbchoices[i].value + rbchoices[i].checked);
        data_add += "&" + rbchoices[i].value + "=" + rbchoices[i].checked;
    }
    for(var i=0; i < cbchoices.length; i++) {
        //alert(cbchoices[i].value + "=" + cbchoices[i].checked);
        data_add += "&" + cbchoices[i].value + "=" + cbchoices[i].checked;
    }
    if (answer.length) {
        if (answer.val()) {
            data_add = "&" + "answer=" + encodeURIComponent(answer.val()).replace(/%20/g, "+");
        } else {
            data_add = "&" + "answer=";
        }
    }
    data += data_add;
    
    // http://stackoverflow.com/questions/4856917/jquery-upload-progress-and-ajax-file-upload/4943774#4943774
    // http://www.html5rocks.com/en/tutorials/file/xhr2/
    // http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4.2
    if (filename) { // For adding a progress bar
        var files = file_element[0].files;
        xhr.file = files[0];
        xhr.addEventListener('progress', function(e1) {
            var done = e1.position || e1.loaded, total = e1.totalSize || e1.total;
            console.log('xhr progress: ' + ((Math.floor(done/total*1000)/10) + '%'));
        }, false);
        if (xhr.upload) {
            xhr.upload.onprogress = function(e1) {
                var done = e1.position || e1.loaded, total = e1.totalSize || e1.total;
                console.log('xhr.upload progress: ' + done + ' / ' + total + ' = ' + (Math.floor(done/total*1000)/10) + '%');
            };
        }
        xhr.onreadystatechange = function(e1) {
            if ( 4 == this.readyState ) {
                console.log(['xhr upload complete', e1]);
            }
        };
    }

    var datalen = data.length;

    // Create a function that will receive data sent from the server
    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4 && xhr.status == 200) {
            $('div#' + task_name + ' div#result').html(xhr.responseText);
        }
    }
    // TODO: Check http://www.html5rocks.com/en/tutorials/file/dndfiles/ to allow drag & dropping files!

    var mimetype = "application/x-www-form-urlencoded";
    var boundary = "-----raJa9x";
    var filemimetype = "multipart/form-data; boundary=" + boundary;
    //var filemimetype = "multipart/form-data";

    xhr.open("POST", answer_check_url + task_name + "/check/", true);
    if (filename) {
        //xhr.setRequestHeader("Content-type", filemimetype);
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
        xhr.setRequestHeader("X_REQUESTED_WITH", "XMLHttpRequest");
        //xhr.setRequestHeader("Connection", "close");

        /* Manually construct the message - works
        data = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"csrfmiddlewaretoken\"\r\n\r\n" + csrftoken + "\r\n";
        data += "--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + filename + "\"\r\n";
        data += "Content-Type: application/octet-stream\r\n\r\n";
        var reader = new FileReader();
        function rT() {
            var x = reader.result;
            data += x;
            data += "--" + boundary + "--\r\n";
            //alert(data);
            xhr.send(data);
        }
        reader.onload = rT;
        reader.readAsBinaryString(files);
        */
        
        /* Use the file sending API - doesn't work
        xhr.send(files);
        */

        // Use FormData to achieve the same as the manual version - works
        var form_data = new FormData();
        form_data.append("csrfmiddlewaretoken", csrftoken);
        form_data.append("collaborators", collaborators);
        for (var filen = 0; filen < files.length; filen++) {
            form_data.append("file" + filen, files[filen]);
        }
        xhr.send(form_data);
        $('div#' + task_name + ' div#result').html("<div class='answersent'>Answer sent. Waiting for evaluation.</div>");
    } else {
        xhr.setRequestHeader("Content-type", mimetype);
        xhr.setRequestHeader("Content-length", datalen);
        xhr.setRequestHeader("Connection", "close");
        xhr.setRequestHeader("X_REQUESTED_WITH", "XMLHttpRequest");
        xhr.send(data);
        $('div#' + task_name + ' div#result').html("<div class='answersent'>Answer sent. Waiting for evaluation.</div>");
    }
}
