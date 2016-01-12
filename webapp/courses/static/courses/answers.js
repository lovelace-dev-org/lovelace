function show_file(e, elem) {
    e.preventDefault();
  
    var popup = $(elem).siblings(".popup");
    popup.css({"opacity":"1", "pointer-events":"auto"});
    
}
function show_results(e, elem, results_div) {
    e.preventDefault();
    var url = elem.href;
    
    $.get(url, function(data, textStatus, jqXHR) {
        var r_div = $('#' + results_div);
        r_div.html(data);
        //r_div.show();
        var popup = r_div.parent();
        popup.css({"opacity":"1", "pointer-events":"auto"});
    });  
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
