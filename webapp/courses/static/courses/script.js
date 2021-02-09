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
            else if (status == "credited")
                icon = static_root_url + "credited-16.png";
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
    
    let grouped_tasks = $('div.task-meta[data-eval-group!=""]');
    let group_names = new Set();
    grouped_tasks.each(function () { group_names.add($(this).attr("data-eval-group")) });
    let correct_groups = 0;
    group_names.forEach(function (name) {
        if ($('div.task-meta[data-eval-group="' + name +'"] img.correct').length > 0) {
            correct_groups++;
        }
    });

    var correct_other = $('div.task-meta[data-eval-group=""] img.correct').length;
    var incorrect_other = $('div.task-meta[data-eval-group=""] img.incorrect').length;
    var unanswered_other = $('div.task-meta[data-eval-group=""] img.unanswered').length;

    var completed = correct_other + correct_groups;
    var total = group_names.size + correct_other + incorrect_other + unanswered_other;

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

    // TODO: Rework to allow slimscroll on term tabs
    
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
        if ($(this).find("span.term").text().toLowerCase().indexOf(search_str.toLowerCase()) > -1 ||
            $(this).find("span.term-alias").text().toLowerCase().indexOf(search_str.toLowerCase()) > -1 ||
            search_str === "") {
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

function show_term_tab(elem) {
    let item = $(elem);
    item.siblings().removeClass("term-tab-active");
    item.addClass("term-tab-active");
    // Calculate the ordinal of this element in the parent <ol>
    let index = item.parent().children().index(item);
    item.parent().parent().children('.term-desc-contents').each(function() {
        let PRECEDING_ELEMENTS = 2;
        if ($(this).index() - PRECEDING_ELEMENTS === index) {
            $(this).show();
        } else {
            $(this).hide();
        }
    });
}

function collapse_eval_debug(button) {
    let item = $(button);
    item.children("ul").children("li.evaluation-msg-debug, li.evaluation-msg-info").each(function() {
        $(this).removeClass("evaluation-li-visible");
        $(this).addClass("evaluation-li-hidden");
        $(this).hide();
    });
    item.attr("onclick", "expand_eval_debug(this)");
    item.removeClass("evaluation-run-open");
    item.addClass("evaluation-run-closed");
}
    
function expand_eval_debug(button) {
    let item = $(button);
    item.children("ul").children("li.evaluation-msg-debug, li.evaluation-msg-info").each(function() {
        $(this).removeClass("evaluation-li-hidden");
        $(this).addClass("evaluation-li-visible");
        $(this).show();
    });
    item.attr("onclick", "collapse_eval_debug(this)");
    item.removeClass("evaluation-run-closed");
    item.addClass("evaluation-run-open");
}

function show_popup(e, popup_id) {
    e.preventDefault();
    
    let popup = $("#" + popup_id);
    popup.css({"opacity":"1", "pointer-events":"auto", "overflow": "scroll"});
}    

function show_collapsed() {
    $(".collapsed").removeClass("collapsed");
}

function expand_next_div(caller) {
    $(caller).nextAll("div").first().toggleClass("collapsed");
}

function submit_ajax_form(form, success_extra_cb) {
    let url = form.attr('action');
    $("body").css("cursor", "progress");
    
    $.ajax({
        type: form.attr('method'),
        url: url,
        data: new FormData(form[0]),
        processData: false,
        contentType: false, 
        dataType: 'json', 
        success: function(data, status, jqxhr) {
            let okspan = "<span class='ajax-form-success'>OK</span>";
            form.find("input[type='submit']").after(okspan);
            success_extra_cb(data);
        },
        error: function(jqxhr, status, type) {
            let errors = JSON.parse(JSON.parse(jqxhr.responseText).errors);
            for (const [field, content] of Object.entries(errors)) {
                content.forEach(function (entry) {
                    let espan = "<span class='ajax-form-error'>" + entry.message + "</span>";
                    form.find("input[name='" + field + "']").after(espan);
                });
                
            }
        },
        complete: function(jqxhr, status) {
            $("body").css("cursor", "default");
        }
    });
}

function submit_enrollment(event) {
    event.preventDefault();
    
    let form = $(this);
    let url = form.attr('action');
    
    $.ajax({
        type: form.attr('method'),
        url: url,
        data: new FormData(form[0]),
        processData: false,
        contentType: false, 
        dataType: 'json',        
        success: function(data, text_status, jqxhr_obj) {
            form.parent().children("div.enroll-status-msg").html(data.message);
            let instance = form.children(".instance-hint").attr('value');
            $("#" + instance + "-enroll-button").attr('disabled', true); 
            form.children("input[type=submit]").attr('disabled', true);
        },
        error: function(xhr, status, type) {
            form.parent().children("div.enroll-status-msg").html("There was an error while submitting.");
        }
    });
}

function withdraw_enrollment(event) {
    event.preventDefault();

    let form = $(this);
    let info = form.prev();
    let url = form.attr('action');

    $.ajax({
        type: form.attr('method'),
        url: url,
        data: new FormData(form[0]),
        processData: false,
        contentType: false,
        dataType: 'json',
        success: function(data, status, jqxhr) {
            info.html(data.message);
            form.children("input[type=submit]").attr('disabled', true);
        },
        error: function(jqxhr, status, type) {
            console.log(jqxhr.responseText);
        }
    });
}

function show_panel(event, caller, panel_type, panel_id) {
    event.preventDefault();
    event.stopPropagation();
    
    let panel = $("#" + panel_id);
    let container = panel.children(".panel-container");
    let a = $(caller);
    let url = a.attr("href") + "?" + a.attr("data-querystring");
    
    if (container.html() == "" || panel.attr("data-panel-type") != panel_type) {
        $.ajax({
            type: "GET",
            url: url,
            success: function(data, status, jqxhr) {
                container.html(data);
                panel.attr("data-panel-type", panel_type);
            },
            error: function(jqxhr, status, type) {
                container.html(jqxhr.responseText);
            },
            complete: function(jqxhr, status) {
                panel.addClass("panel--is-visible");
            }
        });
    } 
    else {
        panel.addClass("panel--is-visible");
    }
}

function hide_panel(event, panel_id) {
    event.preventDefault();
    event.stopPropagation();

    let panel = $("#" + panel_id);
    panel.removeClass("panel--is-visible");    
}

function create_attention_arrow(hook, direction, click_action) {
    let container = $("div.arrow-container");
    
    // if an arrow already exists, don't show it again
    if ($("div#" + hook + "-arrow").length == 0) {
        let arrow = $("<div></div>");
        if (direction == "left" || direction == "right") {
            let position = window.innerHeight/2;
            arrow.css({
                "top": position + "px", 
            })
        }
        else {
            let position = window.innerWidth/2;
            arrow.css({
                "left": position + "px",
            })            
        }
        arrow.addClass("attention-arrow");
        arrow.addClass(direction);
        arrow.attr("id", hook + "-arrow");
        arrow.attr("onclick", click_action + "hide_attention_arrow(event, this);");
        container.append(arrow);
        return arrow;
    }    
    return null;
}

function hide_attention_arrow(event, arrow) {
    event.preventDefault();
    event.stopPropagation();

    $(arrow).css({"opacity": "0", "pointer-events": "none"});
}

function toggle_staff_widgets(event, caller) {
    $(".staff-only").toggleClass("collapsed");
    $(".student-only").toggleClass("collapsed");
    $(caller).toggleClass("pressed");
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
    
    $('.enroll-form').submit(submit_enrollment);
    $('.withdraw-form').submit(withdraw_enrollment);
});

