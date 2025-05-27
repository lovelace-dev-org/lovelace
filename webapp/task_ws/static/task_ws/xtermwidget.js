var XTermWidget = class {

    constructor(widget_id, rows) {
        this.xterm = new Terminal({rows: rows})
        this.xterm.open(document.getElementById(widget_id))
        this.xterm.onKey((event) => this.read_key(event))
        this.input_string = ""
        this.interactive = false
        this.controller = null
    }

    read_key(event) {
        if (this.interactive) {
            if (event.key == "\r") {
                this.controller.send_input(this.input_string)
                this.input_string = ""
                this.xterm.write("\n\r")
            } else if (event.domEvent.code == "Backspace") {
                this.xterm.write("\b \b")
                this.input_string = this.input_string.slice(0, -1)
            } else {
                this.xterm.write(event.key)
                this.input_string += event.key
            }
        }
    }

    init(controller) {
        this.xterm.clear()
        this.xterm.write("\r")
        this.xterm.focus()
        this.input_string = ""
        this.interactive = true
        this.controller = controller
    }

    receive(data) {
        this.xterm.write(data.replace("\n", "\n\r"))
    }

    end() {
        this.interactive = false
    }
}
