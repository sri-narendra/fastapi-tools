from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import subprocess
import os
import uuid
import json

app = FastAPI()

# CORS: allow GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev, you can restrict later
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run/")
async def run_code(request: Request):
    body = await request.json()
    github_repo = body.get("github_repo")
    backend_path = body.get("backend_path")
    input_data = body.get("input_data", {})

    if not github_repo or not backend_path:
        raise HTTPException(400, "Missing repo or path")

    # Convert to raw URL
    raw_url = github_repo.replace("github.com", "raw.githubusercontent.com").replace("/tree/", "/") + backend_path

    async with httpx.AsyncClient() as client:
        response = await client.get(raw_url)
        if response.status_code != 200:
            raise HTTPException(400, "Could not fetch backend file")

        code = response.text

    file_path = f"/tmp/{uuid.uuid4().hex}.py"
    with open(file_path, "w") as f:
        f.write(code)

    try:
        result = subprocess.run(
            ["python", file_path],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"error": result.stderr.strip()}

        return {"output": result.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
