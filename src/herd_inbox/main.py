"""FastAPI application entry point."""

from fastapi import FastAPI

from herd_inbox.security import csp_middleware

app = FastAPI(
    title="Herd-Inbox",
    description="Email-centric platform for herd communication",
    version="0.1.0",
)

# Wire CSP + security headers on every response (issue #2 acceptance criterion).
app.middleware("http")(csp_middleware)


@app.get("/health")
async def health_check() -> dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - placeholder until inbox view is implemented."""
    return {"message": "Herd-Inbox MVP - Coming Soon"}
