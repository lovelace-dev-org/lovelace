const WSWrapper = class {
    constructor(addr) {
        this.addr = addr
        this.socket = null
    }

    connect(controller) {
        this.socket = new WebSocket(this.addr)
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
                        if (data["exitcode"] != null) {
                            controller.end(data["exitcode"])
                            socket.close()
                            console.log("all done")
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
