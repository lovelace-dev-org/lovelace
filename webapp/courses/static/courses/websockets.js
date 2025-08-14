const WSWrapper = class {
    constructor(addr, ticket_url) {
        this.addr = addr
        this.socket = null
        this.ticket_url = ticket_url
    }

    connect(controller) {
        $.ajax({
            type: "GET",
            url: this.ticket_url,
            success: (data, status, jqxhr) => {
                console.log(data)
                const ticket = data["ticket"]
                this.open_ws(controller, ticket)
            },
            error: function(xhr, status, type) {
                controller.error("Unauthorized")
            }
        })
    }

    open_ws(controller, ticket) {
        this.socket = new WebSocket(this.addr + "?ticket=" + ticket)
        this.socket.onopen = () => controller.begin()
        const socket = this.socket

        const receive = function (event) {
            const data = JSON.parse(event.data)
            if (data["status"] == "ok") {
                switch (data["operation"]) {
                    case "input":
                    case "run":
                        socket.send(JSON.stringify({
                            "operation": "read"
                        }))
                        break;
                    case "read":
                        controller.receive(data["output"])
                        if (data["state"] == "done" || data["exitcode"] !== null ) {
                            controller.end(data["exitcode"])
                            socket.close()
                            console.log("all done")
                        }
                        else if (data["state"] == "waiting") {
                            socket.send(JSON.stringify({
                                "operation": "read"
                            }))
                        }
                        break;
                    default:
                        controller.error("Websocket returned unknown operation")
                }
            }
            else {
                controller.error("Websocket error")
            }
        }

        const close = function (event) {
            controller.error("Websocket was closed")
        }

        this.socket.onmessage = receive
        this.socket.onclose = close
    }

    send(data) {
        if (this.socket === null) {
            this.error_cb("Websocket is not connected")
        } else {
            this.socket.send(JSON.stringify(data))
        }
    }

    close() {
        this.socket = null
    }
}

const ws_storage = {
    storage: {},

    add_ws: function (key, addr, receive_cb, error_cb) {
       ws_storage.storage[key] = new WSWrapper(addr, receive_cb, error_cb)
    },

    get_ws: function (key) {
        return ws_storage.storage[key]
    }
}
