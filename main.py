# main.py (on Render)
from fastapi import FastAPI, HTTPException, Request
import httpx
import subprocess
import os
import uuid
import json

app = FastAPI()

@app.post("/run/")
async def run_backend(request: Request):
    body = await request.json()
    github_repo = body.get("github_repo")
    backend_path = body.get("backend_path")
    input_data = body.get("input_data")

    if not github_repo or not backend_path:
        raise HTTPException(400, "Missing required fields")

    # Convert GitHub repo to raw URL
    raw_url = github_repo.replace("github.com", "raw.githubusercontent.com").replace("/tree/", "/") + backend_path

    # Download code
    async with httpx.AsyncClient() as client:
        res = await client.get(raw_url)
        if res.status_code != 200:
            raise HTTPException(500, f"Could not fetch code from GitHub: {res.text}")
        code = res.text

    # Write to a temp file
    temp_id = str(uuid.uuid4())
    temp_file = f"/tmp/{temp_id}.py"
    with open(temp_file, "w") as f:
        f.write(code)

    # Run it
    try:
        result = subprocess.run(
            ["python", temp_file],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise Exception(result.stderr)
        return {"output": result.stdout.strip()}
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")
    finally:
        os.remove(temp_file)
