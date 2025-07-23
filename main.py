from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import subprocess
import os
import uuid
import json

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run/")
async def run_code(request: Request):
    try:
        body = await request.json()
        github_repo = body.get("github_repo")
        backend_path = body.get("backend_path")
        input_data = body.get("input_data", {})
        
        if not github_repo or not backend_path:
            raise HTTPException(400, "Missing github_repo or backend_path")

        # Convert to raw GitHub URL (fixed version)
        repo_path = github_repo.replace("https://github.com/", "").replace("/tree/", "")
        raw_url = f"https://raw.githubusercontent.com/{repo_path}/main{backend_path}"
        
        print(f"Fetching from: {raw_url}")  # Debug logging

        # Download the script
        async with httpx.AsyncClient() as client:
            response = await client.get(raw_url)
            if response.status_code != 200:
                raise HTTPException(400, f"Failed to fetch script: HTTP {response.status_code}")
            code = response.text

        # Save to temporary file
        temp_file = f"/tmp/{uuid.uuid4().hex}.py"
        with open(temp_file, "w") as f:
            f.write(code)

        # Execute the script
        result = subprocess.run(
            ["python", temp_file],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise HTTPException(500, f"Script error: {result.stderr}")

        return {"output": result.stdout.strip()}

    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
