function show_file(e, elem) {
    e.preventDefault();
    var url = elem.href;  
    var popup = $(elem).next(".popup");
    var pre = popup.children("pre");
    
    if (!pre.html()) {
        $.get(url, function(data, textStatus, jqXHR) {
            pre.html(data);
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
        });
    }
    else {
        popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
    }
}

function show_results(e, elem, results_div) {
    e.preventDefault();
    var url = elem.href;
    var r_div = $('#' + results_div);
    var popup = r_div.parent();
    
    if (!r_div.html()) {
        $.get(url, function(data, textStatus, jqXHR) {
            r_div.html(data);
            //r_div.show();
            popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
        });  
    }
    else {
        popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
    }
}

$(document).ready(function() {
    $('.popup').click(function() {
        $(this).css({"opacity":"0", "pointer-events":"none"});
    });
    $('.popup > div').click(function(event) {
        event.stopPropagation();
    });
    $('.popup > pre').click(function(event) {
        event.stopPropagation();
    });
});

function activate_test_tab(tab_id, elem) {
    var item = $(elem).parent().siblings('#file-test-' + tab_id);
    var siblings = item.parent().find('.test-evaluation-tab');
    siblings.hide();
    item.show();
}
