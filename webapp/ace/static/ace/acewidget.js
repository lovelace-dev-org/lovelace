// This object exists for the purpose of sending answer, currently
var acewidget = {

    read_editor_value: function (editor_id) {
        return ace.edit(editor_id).getValue()
    },
}


// This class is used when running with websockets
var AceWidget = class {

    constructor(addr, editor, preview, button_id) {
        this.ws = new WSWrapper(addr)
        this.editor = editor
        this.preview = preview
        this.button = $("button#" + button_id)
        this.button.click((button) => this.connect_ws(button))
        this.running = false
    }

    connect_ws() {
        this.ws.connect(this)
    }

    begin() {
        this.preview.init(this)
        this.button.addClass("ace-button-running")
        this.button.prop("disabled", true)
        this.running = true
        this.ws.send({
            "operation": "run",
            "content": this.editor.getValue(),
        })
    }

    send_input(input) {
        if (this.running) {
            this.ws.send({
                "operation": "input",
                "input": input,
            })
        }
    }

    receive(data) {
        this.preview.receive(data)
    }

    error(msg) {
        this.running = false
    }

    end() {
        this.button.removeClass("ace-button-running")
        this.button.prop("disabled", false)
        this.preview.end()
        this.running = false
    }
}

