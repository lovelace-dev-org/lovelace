from ast import TypeVar
import asyncio
import json
import traceback
from os import truncate
from typing import TypedDict, Literal, Union, NotRequired
import httpx
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
            msg = {
                "operation": "unknown",
                "status": "unauthorized"
            }
            self.timeout_task = None
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


class BaseMessage(TypedDict):
    exitcode: NotRequired[int]
    status: NotRequired[str]


class TimeoutMessage(BaseMessage):
    operation: Literal["unknown"]
    status: Literal["timeout"]


class UnauthorizedMessage(BaseMessage):
    operation: Literal["unknown"]
    status: Literal["unauthorized"]


class FailedMessage(BaseMessage):
    operation: Literal["unknown"]
    status: Literal["failed"]
    reason: NotRequired[str]


class RunConfig(TypedDict):
    stdin: str
    compiler: str
    compiler_args: str


class RunMessage(BaseMessage):
    operation: Literal["run"]
    content: str
    config: NotRequired[RunConfig]


class RunSuccessMessage(BaseMessage):
    """
    Sending this to frontend will make it send a read request immediately after.
    """
    operation: Literal["run"]
    status: Literal["ok"]
    # unsed at the point of writing. used to be outputted on websocket close, but no longer outputted.
    exitcode: None


class BaseOutput(TypedDict):
    code: int
    timedOut: bool
    stdout: list[dict]
    stderr: list[dict]
    truncated: bool
    execTime: int
    processExecutionResultTime: NotRequired[float]
    executableFilename: NotRequired[str]


class CompilationOutput(BaseOutput):
    code: int
    timedOut: bool
    stdout: list[dict]
    stderr: list[dict]
    truncated: bool
    execTime: int
    didExecute: bool
    buildResult: NotRequired[BaseOutput]


class RunResultMessage(BaseMessage):
    """
    Sending this to the frontend will make the frontend display the output in the terminal view.
    """
    operation: Literal["read"]
    state: Literal["done"]
    status: Literal["ok"] | Literal["failed"]
    output: CompilationOutput | str | dict
    # unsed at the point of writing. used to be outputted on websocket close, but no longer outputted.
    exitcode: None


class InputMessage(BaseMessage):
    operation: Literal["input"]
    input: str


def take_keys_of_class(cls, d: dict):
    keys = cls.__annotations__.keys()
    return {k: d[k] for k in keys if k in d}  # type: ignore


def compilation_output_from_run_result(run_result: dict) -> CompilationOutput:
    buildResult = take_keys_of_class(
        BaseOutput, run_result.get("buildResult", {}))
    output = take_keys_of_class(CompilationOutput, run_result)
    output["buildResult"] = buildResult

    return output  # type: ignore


class ReadRequestMessage(TypedDict):
    operation: Literal["read"]


class ReadResponseMessage(BaseMessage):
    operation: Literal["read"]
    status: Literal["ok"]
    output: NotRequired[str | CompilationOutput]
    state: str  # see run_utils.RunState
    # unsed at the point of writing. used to be outputted on websocket close, but no longer outputted.
    exitcode: None


# Messages sent by the frontend to the backend
RequestMessage = Union[RunMessage, InputMessage, ReadRequestMessage]

# Messages sent by the backend to the frontend
ResponseMessage = Union[TimeoutMessage, UnauthorizedMessage,
                        RunSuccessMessage, FailedMessage, ReadResponseMessage, RunResultMessage]


class CompilerExplorerConsumer(AsyncWebsocketConsumer):
    """
    Lifetime of this consumer lasts for a single compilation. The socket is closed by the frontend when compilation succeeds.
    """

    async def send_message(self, message: ResponseMessage):
        await super().send(text_data=json.dumps(message))

    async def connect(self):
        print("User:", self.scope.get("user"))
        self.output = None
        # print("scope", self.scope.keys())

        # for key in self.scope.keys():
        #     print(f"{key}: {self.scope[key]}")
        await self.accept()
        if self.scope.get("user") is None:
            msg: UnauthorizedMessage = {
                "operation": "unknown",
                "status": "unauthorized",
            }
            await self.send_message(msg)
            await self.close(code=3000)
            return

        self.timeout_task = asyncio.get_event_loop().create_task(self.timeout_connection())

    async def timeout_connection(self):
        await asyncio.sleep(settings.WS_TIMEOUT)
        msg: TimeoutMessage = {
            "operation": "unknown",
            "status": "timeout",
        }
        await self.send_message(msg)
        await self.close(code=3008)

    async def disconnect(self, close_code):
        print("Client disconnected")

    async def receive(self, text_data):
        if self.timeout_task is None:
            return

        self.timeout_task.cancel()
        data = json.loads(text_data)
        # print("Received:", data)
        msg = await self.parse_request(data)
        # print("Responding:", msg)
        if msg["operation"] == "run" and msg["status"] == "ok":
            await self.send_message({
                "operation": "run",
                "status": "ok",
                "exitcode": None,
            })
        await self.send_message(msg)

    async def parse_request(self, data: RequestMessage) -> ResponseMessage:
        msg: ResponseMessage = {
            "operation": "unknown",
            "status": "failed",
            "reason": "Unknown operation"
        }
        if data["operation"] == "run":
            content = data["content"]
            config = data.get("config", None)
            if config is None:
                return {
                    "operation": "unknown",
                    "status": "failed",
                    "reason": "Missing config for run operation"
                }
            msg = await self.run(content, config)

        return msg

    # todo add more specific error messages that are sent only for admin/staff users.
    async def run(self, content: str, config: RunConfig) -> Union[RunResultMessage, FailedMessage]:
        try:
            host = settings.COMPILER_EXPLORER_URL
            compiler = config["compiler"]

            print(f"Compiling with '{compiler}' on host '{host}'")

            req_json = {
                "source": content,
                "bypassCache": 0,
                "allowStoreCodeDebug": True,
                "options": {
                    "filters": {
                        "execute": True,
                    },
                    "compilerOptions": {
                        "executorRequest": True,
                        "skipAsm": True,
                    },
                }
            }
            executeParameters = {}
            if "compiler_args" in config:
                req_json["options"]["userArguments"] = config["compiler_args"]
            if "stdin" in config:
                executeParameters["stdin"] = config["stdin"]
            if executeParameters != {}:
                req_json["options"]["executeParameters"] = executeParameters

            # print(json.dumps(req_json, indent=4))
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{host}/api/compiler/{compiler}/compile",
                    json=req_json,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

                output = response.json()
                self.output = output

                # buildResult = output.get("buildResult", {})
                # nonBuildResult = {k: v for k,
                #                   v in output.items() if k != "buildResult"}
                # print("compile results: ", json.dumps(nonBuildResult, indent=4))
                # print("exec results:", json.dumps(buildResult, indent=4))

                return {
                    "operation": "read",
                    "output": compilation_output_from_run_result(output),
                    "state": "done",  # the done will make the frontend end the websocket session
                    "status": "ok",
                    "exitcode": None,
                }
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {
                    "operation": "unknown",
                    "status": "failed",
                    "reason": f"Compiler Explorer: Compiler '{compiler}' not found"
                }
            print("Unexpected response status code from CE API:",
                  exc.response.status_code)
        except httpx.RequestError as exc:
            print(
                f"Exception {exc.__class__.__name__} occurred while requesting {exc.request.url!r}.")
        except Exception as e:
            print("Unknown error during run request:")
            traceback.print_exc()

        return {
            "operation": "unknown",
            "status": "failed",
            "reason": "Error during run request"
        }
      
      
class SQLConsumer(WSBaseConsumer):

    container = "sql-runner"

