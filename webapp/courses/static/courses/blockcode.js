/* blockcode.js */

function addLineNumbers() {
    var codes = $('div.blockcode pre code');

    if (jQuery.support.leadingWhitespace && codes)
    {	
        // A regexp /\r\n|\r|\n/ might have to be used instead of "\n" in split()
        codes.each(function(index, element) {
            $(this).html($(this).html().split("\n").map(function(line) {
                return '<span class="line">' + line + '</span>';
            }).join("<br />"));
        });
    }
}

function setColumnWidths() {
    var subcolumns = $('div.blockcode div.subcolumn');
  
    if (subcolumns) {
        subcolumns.each(function(index, element) {
            $(this).width($(this).parent()[0].clientWidth / 2);
        });
    }
}

function setLineWidths() {
    var presw;
    var lines = $('div.blockcode pre code .line');
    
    if (lines) {
        lines.each(function(index, element) {
            presw = $(this).parent().parent()[0].scrollWidth;
            $(this).width(presw);
        });
    }
}

function setPreHeights() {
    var pres = $('div.blockcode div.subcolumn pre');
    
    if (pres) {
        pres.each(function(index, element) {
            var tallest = $(this).outerHeight();
            $(this).parent().parent().children('.subcolumn').children('pre').each(function(i, e) {
                if ($(this).height() > tallest) tallest = $(this).outerHeight();
            });
            
            $(this).height(tallest);
        });
    }
}

