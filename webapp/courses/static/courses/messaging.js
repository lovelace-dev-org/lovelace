const messaging = {

    remove_message: function(event, caller) {
        event.preventDefault()
        event.stopPropagation()

        const button = $(caller)

        success = function(data) {
            $(caller).parent().nextAll("div").first().remove()
            $(caller).parent().remove()
        }

        submit_ajax_action(button, success)
    }
}
