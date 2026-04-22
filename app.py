from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="Smart Travel MCP", lifespan=lifespan)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy"})


@app.get("/")
def root():
    return {"message": "Smart Travel MCP running"}


# Mount MCP at root so its internal /mcp path becomes external /mcp
app.mount(
    "/mcp",
    mcp.streamable_http_app(),
)