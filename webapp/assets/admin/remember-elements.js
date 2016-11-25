$(document).ready(function() {
    let save = $('input[name="_continue"]');
    let load = $('#load-edit-settings');
    add_state_restore_callbacks(save, load);
});
function add_state_restore_callbacks(save_elem_id, load_elem_id) {
    let V_OFFSET = 20;
    let ss = sessionStorage;
    let fields = $('input[type="text"]').add('textarea');
    fields.on('focus', function() {
        let i = $(this).attr('id');
        ss.setItem('selected-element', i); 
    });
    let save = save_elem_id;
    save.on('click', function() {
        let sel = ss.getItem('selected-element');
        let e = $('#'+sel);
        ss.setItem('selection-start', e.prop('selectionStart'));
        ss.setItem('selection-end', e.prop('selectionEnd'));
        ss.setItem('selection-direction', e.prop('selectionDirection'));
        ss.setItem('selection-vertical-scroll', e.scrollTop());
        ss.setItem('selection-horizontal-scroll', e.scrollLeft());
        ss.setItem('selected-element-height', e.height());
        ss.setItem('selected-element-width', e.width());
    });
    let load = load_elem_id;
    load.on('click', function() {
        /* Get the stored settings from local storage and
           - Restore the size for the element
           - Scroll the page so that the selected element becomes visible
           - Set focus into the selected element
           - Restore the scroll and caret offset values of the element
         */
        let sel = ss.getItem('selected-element');
        let e = $('#'+sel);
        e.height(ss.getItem('selected-element-height'));
        e.width(ss.getItem('selected-element-width'));
        window.scrollTo(0, e.offset().top - V_OFFSET);
        e.focus();
        e.scrollTop(ss.getItem('selection-vertical-scroll'));
        e.scrollLeft(ss.getItem('selection-horizontal-scroll'));
        e.prop('selectionStart', ss.getItem('selection-start'));
        e.prop('selectionEnd', ss.getItem('selection-end'));
        e.prop('selectionDirection', ss.getItem('selection-direction'));
    });
}
