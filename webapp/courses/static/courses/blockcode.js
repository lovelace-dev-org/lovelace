/* blockcode.js */

function addLineNumbers() {
    var codes = $('div.blockcode pre code');

    // Use of .innerHTML instead of firstChild.nodeValue before removes empty lines in IE8 but disallows syntax highlighting
    if (jQuery.support.leadingWhitespace && codes)
    {	
        // A regexp /\r\n|\r|\n/ might have to be used instead of "\n" in split()
        codes.each(function(index, element) {
            $(this).html($(this).html().split("\n").map(function(line) {
                return '<span class="line">' + line + '</span>';
            }).join("<br />"));
            /*
            element.innerHTML = element.innerHTML.split("\n").map(function(line) {
                return '<span class="line">' + line + '</span>';
            }).join("<br />");*/
        });
    }
}

function setColumnWidths() {
  var subcolumns = $('div.blockcode div.subcolumn');
  
  if (subcolumns) {
    subcolumns.each(function(index, element) {
      $(this).width($(this).parent()/*.width()*/[0].clientWidth / 2);
    });
  }
}



function setLineWidths() {
  var presw;
  var lines = $('div.blockcode pre code .line');
  
  if (lines) {
    lines.each(function(index, element) {
      presw = $(this).parent().parent()[0].scrollWidth/*clientWidth*/;
      $(this).width(presw);
    });
  }
}

function setPreHeights() {
  var pres = $('div.blockcode div.subcolumn pre');

  if (pres) {
    pres.each(function(index, element) {
      var tallest = $(this).outerHeight();
      $(this).parent().parent().children('.subcolumn').children('pre')/*siblings('.subcolumn')*/.each(function(i, e) {
        if ($(this).height() > tallest) tallest = $(this).outerHeight();
      });
      
      $(this).height(tallest);
    });
  }
}

