function reserve_slot(e, elem) {
    e.preventDefault();

    var form = $(elem).closest('form');
    var reservation_field = form.children('input[name="reserve"]');
    var submit_button = $(elem);
    var reservation_result = $(elem).parent().siblings('.reservation-result');

    if (reservation_field.val() == "1") {
        reservation_result.html("Reservation sent, awaiting for confirmation.");
    } else {
        reservation_result.html("Cancellation sent, awaiting for confirmation.");
    }

    submit_button.attr("disabled", true);

    $.ajax({
        type: form.attr('method'),
        url: form.attr('action'),
        data: form.serialize(),
        success: function(data, text_status, jqxhr_obj) {
            reservation_result.html(data);
            if (reservation_field.val() == "1") {
                submit_button.val("Cancel reservation");
                reservation_field.val("0");
            } else {
                submit_button.val("Reserve a slot");
                reservation_field.val("1");
            }
            submit_button.attr("disabled", false);
        },
        error: function(xhr, status, type) {
            reservation_result.html(type);
        }
    });
}
