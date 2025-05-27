import os
import subprocess
import sys
import tempfile
import time

async def setup_env(data):
    folder = tempfile.TemporaryDirectory()
    file_path = os.path.join(folder.name, "code.py")
    with open(file_path, "w") as codefile:
        codefile.write(data["content"])

    input_r, input_w = os.pipe()
    out_f = tempfile.NamedTemporaryFile(dir=folder.name)
    return {
        "folder": folder,
        "file_path": file_path,
        "output": out_f,
        "input_r": input_r,
        "input_w": input_w,
        "process": None,
        "read_timeout": 5,
    }

async def start_process(run_env):
    run_env["process"] = subprocess.Popen(
        ("python3", run_env["file_path"]),
        bufsize=0,
        stdin=run_env["input_r"],
        stdout=run_env["output"],
        stderr=run_env["output"],
        encoding="utf-8",
        start_new_session=True,
        cwd=run_env["folder"].name,
        close_fds=True,
        text=True,
    )
    return run_env

async def read_output(run_env, pos):
    output = ""
    attempts = 0
    with open(run_env["output"].name) as out:
        out.seek(pos)
        while not output and attempts * 0.1 < run_env["read_timeout"]:
            output = out.read()
            time.sleep(0.1)
            attempts += 1

        new_pos = out.tell()
    return output, new_pos

async def process_status(run_env):
    return run_env["process"].poll()

async def write_input(run_env, data):
    os.write(run_env["input_w"], data["input"].encode("utf-8") + b"\n")

async def kill_process(run_env):
    run_env["process"].terminate()
    try:
        run_env["process"].wait(timeout=5)
    except subprocess.TimeoutExpired:
        secure_kill(run_env["process"].pid)

async def close_env(run_env):
    run_env["output"].close()
    run_env["folder"].cleanup()

def secure_kill(pid):
    os.system(f"pkill --signal SIGSTOP -s {pid}")
    os.system(f"pkill --signal SIGKILL -s {pid}")

