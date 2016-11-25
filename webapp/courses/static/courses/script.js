function isElementInViewport (el) {
    //special bonus for those using jQuery
    if (el instanceof jQuery) {
        el = el[0];
    }

    var rect = el.getBoundingClientRect();
    // TODO: Use the height of the header here
    var result = (rect.top >= 0 &&
                  rect.bottom <= $(window).height());
    return result;
}

function isElementBelowViewport (el) {
    if (el instanceof jQuery) {
        el = el[0];
    }

    var rect = el.getBoundingClientRect();
    var result = (rect.bottom > $(window).height());
    return result;
}

var handler = function() {
    var headings = $(".content-heading");
    var topmost_found = false;
    var old, previous;
    headings.each(function(index) {
        var id = $(this).find("span.anchor-offset").first().attr("id");
        var link_in_toc = $("#toc li a[href='#" + id + "']").parent();
        if (isElementInViewport(this) && topmost_found == false) {
            $(link_in_toc).attr("class", "toc-visible");
            topmost_found = true;
        } else {
            if ($(link_in_toc).attr("class") === "toc-visible") {
                old = $(link_in_toc);
                if (isElementBelowViewport(this)) {
                    old = previous || old;
                }
            }
            $(link_in_toc).attr("class", "");
        }
        previous = $(link_in_toc);
    });
    if (topmost_found == false && typeof old !== "undefined") {
        old.attr("class", "toc-visible");
    }
    $("div.term-description").hide();
    let w = $(window).width(); // Small screen trickery below
    if (w >= 1896) {
        $('div.toc-box').attr('style', '');
        $('div#termbank').attr('style', '');
    } else if (w <= 1160 + 300) {
        let toc = $('div.toc-box');
        let tb = $('div#termbank');
        if (toc.find('button').hasClass('retract-box')) {
            toc.offset({left: (w - 300 < 1160) ? (w - 300) : (1160)});
        }
        if (tb.find('button').hasClass('retract-box')) {
            tb.offset({left: (w - 300 < 1160) ? (w - 300) : (1160)});
        }
    }
};

function expand_box(b) {
    let box = $(b.parentElement);
    let button = $(b);
    button.toggleClass("retract-box");
    button.toggleClass("expand-box");
    button.attr("onclick", "retract_box(this);");
    button.html('▶');
    let w = $(window).width();
    box.offset({left: (w - 300 < 1160) ? (w - 300) : (1160)});
}
function retract_box(b) {
    let box = $(b.parentElement);
    let button = $(b);
    button.toggleClass("retract-box");
    button.toggleClass("expand-box");
    button.attr("onclick", "expand_box(this);");
    button.html('◀');
    box.offset({left: 1160});
}

// Build the table of contents
function build_toc(static_root_url) {
    var toc = $("nav#toc > div.list-div > ol");
    var current_toc_level = 1;
    //var topmost_ol = null;
    var headings = $.map([1, 2, 3, 4, 5, 6], function(i) {
        return "section.content h" + i + ".content-heading";
    }).join(", ");
    $(headings).each(function(index) {
        // TODO: http://stackoverflow.com/questions/123999/how-to-tell-if-a-dom-element-is-visible-in-the-current-viewport
        var new_toc_level = parseInt(this.tagName[1]);

        if ($(this).closest("div.term-description").length > 0) {
            return;
        }

        // TODO: Fix, ol can only contain li
        if (new_toc_level > current_toc_level) {
            for (var i = current_toc_level; i < new_toc_level; i += 1) { // >
                //var new_li = document.createElement("li");
                var new_ol = document.createElement("ol");
                toc.append(new_ol);
                //$(new_li).append(new_ol);
                //$(new_li).attr("class", "ol-container");
                
                toc = $(new_ol);
            }
        } else if (new_toc_level < current_toc_level) { // >
            for (var i = current_toc_level; i > new_toc_level; i -= 1) {
                toc = toc.parent();
            }
        }
        current_toc_level = new_toc_level;
        
        var li = document.createElement("li");
        var text = this.firstChild.nodeValue;
        var id = $(this).find("span.anchor-offset").first().attr("id");
        var anchor = document.createElement("a");
        $(anchor).attr("href", "#" + id)
        $(anchor).text(text);
        
        var h_parent = this.parentNode.parentNode;
        var icon, icon_img;
        if (h_parent.className == "embedded-page") {
            var status = $(h_parent).find("img").first().attr("class");
            if (status == "correct")
                icon = static_root_url + "correct-16.png";
            else if (status == "incorrect")
                icon = static_root_url + "incorrect-16.png";
            else if (status == "unanswered")
                icon = static_root_url + "unanswered-16.png";
            icon_img = $(document.createElement("img"));
            icon_img.attr("src", icon);
        }
        $(li).append(anchor);
        if (icon)
            $(li).append(icon_img);
        
        toc.append(li);
    });
}

function update_progress_bar() {
    var completed_elem = $('#completed-exercises');
    var total_elem = $('#total-exercises');
    var progress_elem = $('#exercises-progress');

    var correct = $('img.correct').length;
    var incorrect = $('img.incorrect').length;
    var unanswered = $('img.unanswered').length;

    var completed = correct;
    var total = correct + incorrect + unanswered;

    completed_elem.html(completed);
    total_elem.html(total);
    progress_elem.attr({"value": completed, "max": total});
}

function activate_test_tab(tab_id, elem) {
    var item = $(elem).parent().siblings('#file-test-' + tab_id);
    var siblings = item.parent().find('.test-evaluation-tab');
    siblings.hide();
    item.show();
}

function accept_cookies() {
    document.cookie = "cookies_accepted=1";
    var cookie_law_message = $('#cookie-law-message');
    cookie_law_message.hide();
}

function show_term_description(span_slct, div_slct) {
    var span = $(span_slct);
    var desc_div = $(div_slct);
    if (desc_div.length == 0) {
        desc_div = $("#term-div-not-found");
    }

    let arrow_height = 9;
    let arrow_width = 10;
    let offset = span.offset();
    let span_height = span.height();

    desc_div.css({"display" : "block", "visibility" : "hidden"});
    
    let desc_div_height = desc_div.height();
    let left_offset = offset.left;
    let top_offset = offset.top + span_height + arrow_height;

    var desc_content_div = desc_div.children("div.term-desc-contents");
    var desc_scrollable_div = desc_div.find("div.term-desc-scrollable");
    
    if (desc_div_height + "px" === desc_content_div.css('max-height')) {
        desc_scrollable_div.slimScroll({
            height: desc_content_div.css('max-height')
        });
    }

    desc_div.removeClass("term-description-left-aligned");
    desc_div.removeClass("term-description-top-aligned");
    if (left_offset - $(window).scrollLeft() >  window.innerWidth / 2) {
        left_offset = left_offset - desc_div.width() - arrow_width + span.width();
        left_offset_MAX = window.innerWidth - desc_div.width() - arrow_width; // TODO: Align prettily
        if (left_offset + desc_div.width() + arrow_width >= window.innerWidth) {
            left_offset = left_offset_MAX;
        }
        desc_div.addClass("term-description-left-aligned");
    }
    let section_visible_height =  window.innerHeight - $("header.top-header").height() - $("nav.breadcrumb").height();
    if (offset.top - $(window).scrollTop() > section_visible_height / 2) {
        top_offset = offset.top - span_height - desc_div_height;
        desc_div.addClass("term-description-top-aligned");
    }
    desc_div.offset({left: left_offset, top: top_offset});
    desc_div.css({"visibility" : "visible"});
}

function show_term_description_during_hover(container_elem, event, div_id) {
    var container = $(container_elem);
    var description_dom_element = $(div_id).detach();
    container.append(description_dom_element);
    show_term_description(container_elem, div_id);
}

function hide_tooltip(div_id) {
    var desc_div = $(div_id);
    if (desc_div.length === 0) {
        desc_div = $("#term-div-not-found");
    }
    desc_div.hide();
}

function filter_termbank_contents(search_str) {
    $("li.term-list-item").each(function() {
        if ($(this).find("span.term").text().toLowerCase().indexOf(search_str.toLowerCase()) > -1 || search_str === "") {
            $(this).css({"display" : "block"});
        } else {
            $(this).hide();
        }
    });
    $("li.terms-by-letter").each(function() {
        if($(this).children("ol").children(":visible").length > 0 || search_str === "") {
            $(this).css({"display" : "block"});
        } else {
            $(this).hide();
        }
    });
}
