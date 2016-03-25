function isElementInViewport (el) {
    //special bonus for those using jQuery
    if (el instanceof jQuery) {
        el = el[0];
    }

    var rect = el.getBoundingClientRect();
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
        var link_in_toc = $("#toc li a[href=#" + id + "]").parent();
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
};

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

function show_description(span_slct, div_slct, left_offset, top_offset) {
    var span = $(span_slct);
    var desc_div = $(div_slct);
    if (desc_div.length == 0) {
        desc_div = $("#term-div-not-found");
    }

    var pos = span.position();
    desc_div.css({"left" : pos.left + span.width() + left_offset + "px", 
                  "top" : pos.top + top_offset + "px"});
    var desc_content_div = desc_div.children("div.term-desc-contents");
    if (desc_div.height() + "px" === desc_content_div.css('max-height')) {
        desc_div.find("div.term-desc-scrollable").slimScroll({
            height: "600px"
        });
    }
    desc_div.css({"display" : "block"}); //This works in Jquery3 unlike .show()
}

function show_descr_termtag(span_elem, div_id) {
    var left_offset = 5;
    var top_offset = 60;
    var span = $(span_elem);
    var parent = span.parent();
    if (parent.hasClass("exercise-form")) {
        var parent_pos = parent.position();
        top_offset += parent_pos.top + 8;
        left_offset += parent_pos.left;
    }
    
    show_description(span_elem, div_id, left_offset, top_offset);
    var elems_hovered = 1;
    span.add(div_id).hover(function() {
        elems_hovered++;
        show_description(span_elem, div_id, left_offset, top_offset);
    }, function() {
        elems_hovered--;
        if (elems_hovered == 0) {
            hide_description(div_id);
        }
    });
}

function hide_description(div_id) {
    var desc_div = $(div_id);
    if (desc_div.length == 0) {
        desc_div = $("#term-div-not-found");
    }
    desc_div.hide();
}

