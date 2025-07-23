# main.py
from fastapi import FastAPI, Request, HTTPException
import httpx
import subprocess
import os
import uuid
import json
import asyncio

app = FastAPI()

@app.post("/run/")
async def run_dynamic_code(request: Request):
    payload = await request.json()
    github_repo = payload.get("github_repo")
    backend_path = payload.get("backend_path")
    input_data = payload.get("input_data", {})

    # Validate input
    if not github_repo or not backend_path:
        raise HTTPException(400, detail="Missing 'github_repo' or 'backend_path'")

    # OPTIONAL: Whitelist your repos only
    if not github_repo.startswith("https://github.com/sri-narendra/"):
        raise HTTPException(403, detail="Repo not allowed")

    # Convert to raw URL
    raw_url = github_repo.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/") + backend_path

    # Fetch code
    async with httpx.AsyncClient() as client:
        res = await client.get(raw_url)
        if res.status_code != 200:
            raise HTTPException(500, detail="Failed to fetch backend code")
        code = res.text

    # Save to temporary file
    temp_file = f"/tmp/temp_{uuid.uuid4().hex}.py"
    with open(temp_file, "w") as f:
        f.write(code)

    # Execute
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", temp_file,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        input_str = json.dumps(input_data)
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=input_str.encode()), timeout=10)

        if proc.returncode != 0:
            raise HTTPException(500, detail=stderr.decode())

        return {"output": stdout.decode().strip()}

    except asyncio.TimeoutError:
        raise HTTPException(504, detail="Execution timed out")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
