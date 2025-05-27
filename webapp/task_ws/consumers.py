import json
from channels.generic.websocket import AsyncWebsocketConsumer
from . import run_utils

class InteractivePythonConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self.run_env = None
        self.position = 0

    async def disconnect(self, close_code):
        print("Client disconnected")
        if self.run_env is not None:
            await run_utils.kill_process(self.run_env)
            await run_utils.close_env(self.run_env)

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("Received:", data)
        if data["operation"] == "run":
            self.run_env = await run_utils.setup_env(data)
            self.run_env = await run_utils.start_process(self.run_env)
            msg = {
                "operation": "run",
                "status": "ok",
            }
        elif data["operation"] == "input":
            await run_utils.write_input(self.run_env, data)
            msg = {
                "operation": "input",
                "status": "ok",
            }
        elif data["operation"] == "read":
            output, self.position = await run_utils.read_output(self.run_env, self.position)
            msg = {
                "operation": "read",
                "status": "ok",
                "output": output,
            }
        else:
            msg = {
                "operation": "unknown",
                "status": "failed"
            }
        if self.run_env is not None:
            exitcode = await run_utils.process_status(self.run_env)
            msg["exitcode"] = exitcode
        print("Responding:", msg)
        await self.send(text_data=json.dumps(msg))

        if exitcode is not None:
            await run_utils.close_env(self.run_env)
