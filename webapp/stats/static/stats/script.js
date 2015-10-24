function show_matches(elem) {
    var span = $(elem);
    var matches_div = span.siblings('.matches-list');
    matches_div.show();
}

function hide_matches(elem) {
    var span = $(elem);
    var matches_div = span.siblings('.matches-list');
    matches_div.hide();
}
