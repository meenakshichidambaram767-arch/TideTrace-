import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-Id")
        if not req_id:
            req_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = req_id

        response = await call_next(request)
        response.headers["X-Request-Id"] = req_id
        return response
