var TurtleWidget = class {

    constructor(widget_id, stdout_id) {
        this.canvas = document.getElementById(widget_id)
        this.stdout = document.getElementById(stdout_id)
        this.canvas.width = this.canvas.offsetWidth
        this.canvas.height = this.canvas.offsetHeight
        this.ctx = this.canvas.getContext("2d")
        this.busy = false
        this.pen = {}
    }

    init(controller) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
        this.stdout.innerHTML = ""
        this.controller = controller
    }

    receive(data) {
        try {
            this.log = JSON.parse(data)
        } catch (error) {
            this.stdout.append(data)
            return
        }
        // center the pen because turtle's origin is in the middle
        this.pen = {
            x: this.canvas.width / 2,
            y: this.canvas.height / 2,
            heading: 0,
            weight: 1,
            color: "black",
            fill: "black",
            progress: 0,
            down: true
        }
        this.busy = true
        this.ctx.beginPath()
        this.ctx.moveTo(this.pen.x, this.pen.y)
        this.step()
    }

    end() {

    }

    step() {
        const instruction = this.log.shift()
        console.log(this.pen)
        if (!instruction) {
            this.busy = false
        } else {
            this.pen.progress = 0
            this[instruction[0]](instruction[1])
        }
    }

    // Instruction handlers
    // V

    beginfill(data) {
        this.step()
    }

    endfill(data) {
        this.ctx.closePath()
        this.ctx.fill()
        this.ctx.beginPath()
        window.requestAnimationFrame(() => this.step())
    }

    color(data) {
        const rgb = data["args"]
        this.pen.color = "rgb(" + rgb[0] + " " + rgb[1] + " " + rgb[2] + ")"
        this.pen.fill = "rgb(" + rgb[0] + " " + rgb[1] + " " + rgb[2] + ")"
        this.ctx.fillStyle = this.pen.fill
        this.ctx.strokeStyle = this.pen.color
        this.ctx.beginPath()
        this.step()
    }

    right(data) {
        this.pen.heading -= data["angle"]
        this.step()
    }

    left(data) {
        this.pen.heading += data["angle"]
        this.step()
    }

    forward(data) {
        const length = data["distance"]
        this.extend_line(Math.abs(length), this.pen.heading + (length < 0 ? 180 : 0))
    }

    setposition(data) {
        if (this.pen.down) {
            const dx = data["x"] - (this.pen.x - this.canvas.width / 2)
            const dy = data["y"] + (this.pen.y - this.canvas.height / 2)
            const length = (dx ** 2 + dy ** 2) ** 0.5
            console.log(dx, dy, length)
            if (length > 0) {
                const heading = Math.atan2(dy, dx) * (180 / Math.PI)
                this.extend_line(length, heading)
            }
        } else {
            this.pen.x = this.canvas.width / 2 + data["x"]
            this.pen.y = this.canvas.height / 2 - data["y"]
            this.ctx.moveTo(this.pen.x, this.pen.y)
            this.step()
        }
    }

    setx(data) {
        if (this.pen.down) {
            const dx = data["x"] - (this.pen.x - this.canvas.width / 2)
            if (dx < 0) {
                this.extend_line(-1 * dx, 180)
            } else if (dx > 0) {
                this.extend_line(dx, 0)
            }
        } else {
            this.pen.x = this.canvas.width / 2 + data["x"]
            this.ctx.moveTo(this.pen.x, this.pen.y)
            this.step()
        }
    }

    sety(data) {
        if (this.pen.down) {
            const dy = data["y"] - (this.pen.y - this.canvas.height / 2)
            if (dy < 0) {
                this.extend_line(-1 * dy, 270)
            } else if (dy > 0) {
                this.extend_line(dy, 90)
            }
        } else {
            this.pen.y = this.canvas.height / 2 - data["y"]
            this.ctx.moveTo(this.pen.x, this.pen.y)
            this.step()
        }
    }

    setheading(data) {
        this.pen.heading = data["to_angle"]
        this.step()
    }

    circle(data) {
        const r = data["radius"]
        const da = data["extent"] ? data["extent"] : 360

        const a_normal = (this.pen.heading - 90) * (Math.PI / 180)
        const cx = Math.cos(a_normal) * -1 * r + this.pen.x
        const cy = Math.sin(a_normal) * r + this.pen.y

        console.log(cx, cy)
        this.extend_arc(cx, cy, r, da)
    }

    penup(data) {
        this.pen.down = false
        this.step()
    }

    pendown(data) {
        this.pen.down = true
        this.step()
    }

    pensize(data) {
        this.pen.width = data["width"]
        this.ctx.lineWidth = this.pen.width
        this.ctx.beginPath()
        this.step()
    }

    // Assist methods
    // V

    update_progress(max) {
        if (this.pen.progress < max) {
            const segment = Math.min(5, (max - this.pen.progress))
            this.pen.progress += segment
            return segment
        }
        else {
            return null
        }
    }

    set_pen(x, y) {
        if (this.pen.down) {
            const new_x = this.canvas.width / 2 + x
            const new_y = this.canvas.height / 2 + y
            const dx = new_x - this.pen.x
            const dy = new_y - this.pen.y
        }
        else {
            this.pen.x = this.canvas.width / 2 + x
            this.pen.y = this.canvas.height / 2 - y
            this.step()
        }
    }

    extend_arc(cx, cy, r, arc_length) {
        const segment = this.update_progress(arc_length)
        if (segment !== null) {
            let new_heading
            if (r > 0) {
                new_heading = this.pen.heading + segment
                this.ctx.arc(
                    cx, cy, Math.abs(r),
                    ((90 - this.pen.heading) % 360) * (Math.PI / 180),
                    ((90 - new_heading) % 360) * (Math.PI / 180),
                    true
                )
            } else {
                new_heading = this.pen.heading - segment
                this.ctx.arc(
                    cx, cy, Math.abs(r),
                    ((270 - this.pen.heading) % 360) * (Math.PI / 180),
                    ((270 - new_heading) % 360) * (Math.PI / 180),
                    false
                )
            }
            this.ctx.stroke()
            this.pen.heading = new_heading
            window.requestAnimationFrame(() => this.extend_arc(cx, cy, r, arc_length))
        } else {
            const a_normal = (this.pen.heading - 90) * (Math.PI / 180)
            this.pen.x = cx - Math.cos(a_normal) * -1 * r
            this.pen.y = cy - Math.sin(a_normal) * r
            window.requestAnimationFrame(() => this.step())
        }
    }

    extend_line(length, heading) {
        const segment = this.update_progress(length)
        if (segment !== null) {
            const radians = heading * (Math.PI / 180)
            const dx = Math.cos(radians) * segment
            const dy = Math.sin(radians) * segment
            this.draw_line(dx, dy)
            window.requestAnimationFrame(() => this.extend_line(length, heading))
        } else {
            window.requestAnimationFrame(() => this.step())
        }
    }

    draw_line(dx, dy) {
        this.pen.x += dx
        // dy is negative because coordinate plane is inversed compared to turtle
        this.pen.y -= dy
        if (this.pen.down) {
            this.ctx.lineTo(this.pen.x, this.pen.y)
            this.ctx.stroke()
        }
        else {
            this.ctx.moveTo(this.pen.x, this.pen.y)
        }
    }


}
