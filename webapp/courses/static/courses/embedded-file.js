function add_line_numbers() {
    var codes = $('div.embedded-code > pre > code');

    if (codes.length)
    {	
        // A regexp /\r\n|\r|\n/ might have to be used instead of "\n" in split()
        codes.each(function(index, element) {
            $(this).html($(this).html().split("\n").map(function(line) {
                return '<span class="line">' + line + '</span>';
            }).join("\n"));
        });
    }   
}

function set_line_widths() {
    var presw;
    var lines = $('div.embedded-code > pre > code > .line');
    
    if (lines) {
        lines.each(function(index, element) {
            presw = $(this).parent().parent()[0].scrollWidth;
            $(this).width(presw);
        });
    }
}
