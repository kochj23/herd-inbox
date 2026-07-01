"""FastAPI application entry point."""

from fastapi import FastAPI

from .routes.web import router as web_router

app = FastAPI(
    title="Herd-Inbox",
    description="Email-centric platform for herd communication",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


# Server-rendered web layer: GET /, /spaces/{space}, /thread/{id}
app.include_router(web_router)
