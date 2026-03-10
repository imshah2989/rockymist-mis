import uvicorn
import os
from main import app

# Add a health check endpoint
@app.get("/health")
def health():
    return {"status": "online", "service": "RockyMist-I FinMIS"}

# Hugging Face Spaces expects a process listening on port 7860.
# We use uvicorn to serve the FastAPI app directly.
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
