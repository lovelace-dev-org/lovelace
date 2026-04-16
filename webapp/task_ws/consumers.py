import asyncio
import json
from django.conf import settings
from channels.auth import get_user
from channels.generic.websocket import AsyncWebsocketConsumer
from . import run_utils

class WSBaseConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self.run_env = None
        self.state = run_utils.RunState.NOT_STARTED
        self.position = 0
        if self.scope["user"] is None:
            self.timeout_task = None
            msg = {
                "operation": "unknown",
                "status": "unauthorized"
            }
            await self.send(text_data=json.dumps(msg))
            await self.close(code=3000)
        else:
            self.timeout_task = asyncio.get_event_loop().create_task(self.timeout_connection())

    async def timeout_connection(self):
        await asyncio.sleep(settings.WS_TIMEOUT)
        msg = {
            "operation": "unknown",
            "status": "timeout"
        }
        await self.send(text_data=json.dumps(msg))
        await self.close(code=3008)

    async def disconnect(self, close_code):
        if self.run_env is not None:
            await run_utils.kill_process(self.run_env)
            await run_utils.close_env(self.run_env)

    async def receive(self, text_data):
        if self.timeout_task is None:
            return

        self.timeout_task.cancel()
        data = json.loads(text_data)
        msg = await self.parse_request(data)
        if self.run_env is not None:
            exitcode = await run_utils.process_status(self.run_env)
            msg["exitcode"] = exitcode
        await self.send(text_data=json.dumps(msg))

        if exitcode is not None:
            await run_utils.close_env(self.run_env)
            await self.close(code=1000)
            return

        if self.state == run_utils.RunState.DONE:
            await self.close(code=1000)
            return

        self.timeout_task = asyncio.get_event_loop().create_task(self.timeout_connection())

    async def parse_request(self, data):
        if data["operation"] == "run":
            self.run_env = await run_utils.setup_env(data)
            self.run_env = await run_utils.start_docker(self.run_env, self.container)
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
            output, self.position, self.state = await run_utils.read_output(self.run_env, self.position)
            msg = {
                "operation": "read",
                "status": "ok",
                "output": output,
                "state": self.state,
            }
        else:
            msg = {
                "operation": "unknown",
                "status": "failed"
            }
        if self.state == run_utils.RunState.TIMEOUT:
            await run_utils.kill_process(self.run_env)
            await run_utils.close_env(self.run_env)

        return msg


class InteractivePythonConsumer(WSBaseConsumer):

    container = "python-runner"


class TurtleConsumer(WSBaseConsumer):

    container = "turtle-runner"
