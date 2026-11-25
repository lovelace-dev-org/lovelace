


/**
 * The widget for the compile and execute result of a task.
 * @implements {WSPreviewWidget} 
 */
var CompilerExplorerWidget = class {

    static replace_escapes = (str) => {
        return str
            .replaceAll("\n\r", "\n")
            .replaceAll("\n", "\n\r")
            .replaceAll("\\u001b", "\x1b") // ANSI escape character
    }

    constructor(widget_id, rows, stdin, compiler, compiler_args) {
        this.parentElement = document.getElementById(widget_id)
        this.stdinElement = this.parentElement.querySelector('.xterm-stdin')

        this.xterm = new Terminal({rows: rows})
        const fitAddon = new FitAddon.FitAddon()
        this.xterm.loadAddon(fitAddon)
        this.xterm.open(this.parentElement)
        fitAddon.fit()
        document.querySelector('.xterm-width-cache-measure-container').style.fontVariantLigatures='none';
        document.querySelector('.xterm-rows').style.fontVariantLigatures='none';
        this.controller = null

        /** @type {string} */
        this.stdin = stdin

        /** @type {string} */
        this.compiler = compiler

        /** @type {string} */
        this.compiler_args = compiler_args
    }

    preInit() {
        this.xterm.reset()
        this.xterm.focus()
        this.xterm.write("connecting") 
    }

    init(controller) {
        // this.xterm.reset()
        // this.xterm.focus()
        this.clear_line()
        this.write("connected")
        this.input_string = ""
        this.controller = controller
        this.compiling = true
        this.display_compiling()
    }

    // Receives data only once per compilation. Therefore the terminal is reset before printing the result.
    receive(data, err) {
        this.xterm.reset()
        this.compiling = false

        if (err) {
            this.write_separator("Internal Error")
            this.write(err)
            return
        }
        if (typeof data === "string") {
            this.write_separator("Internal Error")
            this.write(data)
            return
        }

        try {
            this.display_result(data)
        } catch (e) {
            console.error("Error parsing data:", e)
            this.write("\x1b[0;31mError parsing compilation result data\x1b[0m\n")
        }
    }

    end() {
        if (this.compiling) {
            this.compiling = false
            this.xterm.reset()
            this.write("\x1b[0;31mConnection closed before compilation finished\x1b[0m\n")
        }
    }

    write(str) {
        this.xterm.write(CompilerExplorerWidget.replace_escapes(str))
    }

    /**
     * takes compiler explorer output stream as input and writes it to the output
     * @param {{[key: string]: any}[]} arr 
     */
    write_stream(arr) {
        arr.forEach(line => {
            this.write(line.text + "\n");
        })
    }

    write_separator(title="") {
        const term_cols = this.xterm.cols

        if (title === "") {
            this.write("=".repeat(Math.max(0, term_cols || 0)))
            return;
        }

        const sep_length = Math.max(0, term_cols - title.length - 4)
        const sep = "=".repeat(Math.max(0, sep_length || 0))
        this.write("== " + title + " " + sep + "\n")
    }

    clear_line() {
        this.xterm.write("\r" + " ".repeat(this.xterm.cols) + "\r") // clear line, smoother than reset()
    }

    display_compiling() {
        (async () => {
            // this.xterm.reset()
            this.xterm.write("\n")
            while (this.compiling) {
                this.clear_line()
                this.xterm.write("compiling and running")
                for (let i = 0; i < 3; i++) {
                    if (!this.compiling) {
                        break;
                    }
                    this.xterm.write(".")
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }
        })()
    }

    display_result(result) {
        this.controller.editor.getSession().clearAnnotations()

        const annotations = result.buildResult.stderr.filter(line => line.tag !== undefined)
            .map(oldLine => {
                const line = oldLine.tag;
                line.row = line.line - 1
                delete line.line
                line.column = line.column - 1

                switch (line.severity) {
                    case 2: // 2 is definitely warning
                        line.type = "warning"
                        break;
                    case 1: // 1 is definitely info
                        line.type = "info"
                        break;
                    default: // 3 is error but higher values are also possible, so default to error
                        line.type = "error"
                }
                return line
            });

        this.controller.editor.getSession().setAnnotations(annotations)

        if (result.buildResult.execTime !== undefined) {
            this.write_separator("Build - " + (result.buildResult.execTime) + "ms")
        }
        if (result.buildResult.stdout.length !== 0 || result.buildResult.stderr.length !== 0) {
            if (result.buildResult.execTime === undefined)
            this.write_separator("Build")
            this.write_stream(result.buildResult.stdout)
            this.write_stream(result.buildResult.stderr)
        }

        if (result.didExecute === false) { // build failed
            return;
        }
        
        this.write_separator("Output - " + (result.execTime) + "ms")

        this.write_stream(result.stdout)
        this.write_stream(result.stderr)
    }

    getConfig() {
        return {
            "stdin": this.stdinElement.value,
            "compiler": this.compiler,
            "compiler_args": this.compiler_args
        }
    }
}
