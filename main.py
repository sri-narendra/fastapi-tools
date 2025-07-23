from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx, subprocess, os, uuid

app = FastAPI()

# Allow frontend GitHub Pages domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sri-narendra.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run/")
async def run_backend(data: dict):
    github_repo = data.get("github_repo")
    backend_path = data.get("backend_path")
    input_data = data.get("input_data", {})

    if not github_repo or not backend_path:
        raise HTTPException(400, "Missing repo or backend path")

    # Convert to raw URL (with /main/ assumed)
    raw_url = github_repo.replace("github.com", "raw.githubusercontent.com") + backend_path

    # Fetch backend script
    async with httpx.AsyncClient() as client:
        r = await client.get(raw_url)
        if r.status_code != 200:
            raise HTTPException(400, "Could not fetch backend file")
        code = r.text

    # Save to temp file
    file_id = str(uuid.uuid4())
    file_path = f"temp_{file_id}.py"
    with open(file_path, "w") as f:
        f.write(code)

    # Run with subprocess
    try:
        result = subprocess.run(
            ["python3", file_path],
            input=str(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )
        return {"output": result.stdout.strip()}
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {e}")
    finally:
        os.remove(file_path)
