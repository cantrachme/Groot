from fastapi import FastAPI

app = FastAPI(
    title="GROOT AI Engine",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-engine",
    }