"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="Herd-Inbox",
    description="Email-centric platform for herd communication",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - placeholder until inbox view is implemented."""
    return {"message": "Herd-Inbox MVP - Coming Soon"}
