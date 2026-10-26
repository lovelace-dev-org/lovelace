var SQLWidget = class {

    constructor(widget_id) {
        this.widget = document.getElementById(widget_id)
        this.table = document.createElement("table")
        this.info = document.createElement("h2")
        this.widget.appendChild(this.info)
        this.widget.appendChild(this.table)
    }

    init(controller) {
        this.table.remove()
        this.info.textContent = ""
        this.table = document.createElement("table")
        this.widget.appendChild(this.table)
    }

    receive(data) {
        try {
            const parsedData = JSON.parse(data)
            if (Object.hasOwn(parsedData, "sql_error")) {
                this.info.textContent = "Error: " + parsedData.sql_error
                return
            }

            if (parsedData.length == 0) {
                this.info.textContent = "Empty result set"
            }

            parsedData.forEach((row) => {
                let htmlRow = this.table.insertRow(-1)
                row.forEach((col) => {
                    let htmlCol = htmlRow.insertCell(-1)
                    htmlCol.textContent = col
                })
            })
        } catch (e) {
             //Ignore messages from websocket not containing valid json
        }
    }

    end() {

    }
}
