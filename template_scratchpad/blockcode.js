/* blockcode.js */

function addLineNumbers() {
	var codes = $('div.blockcode pre code');

	// Use of .innerHTML instead of firstChild.nodeValue before removes empty lines in IE8 but disallows syntax highlighting
	if (jQuery.support.leadingWhitespace)
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
	$('div.blockcode div.subcolumn').each(function(index, element) {
		$(this).width($(this).parent()/*.width()*/[0].clientWidth / 2);
	});
}

function setLineWidths() {
	var presw;

	$('div.blockcode pre code .line').each(function(index, element) {
		presw = $(this).parent().parent()[0].scrollWidth/*clientWidth*/;
		$(this).width(presw);
	});
}

function setPreHeights() {	
	$('div.blockcode div.subcolumn pre').each(function(index, element) {
		var tallest = $(this).outerHeight();
		$(this).parent().parent().children('.subcolumn').children('pre')/*siblings('.subcolumn')*/.each(function(i, e) {
			if ($(this).height() > tallest) tallest = $(this).outerHeight();
		});

		$(this).height(tallest);
	});
}

