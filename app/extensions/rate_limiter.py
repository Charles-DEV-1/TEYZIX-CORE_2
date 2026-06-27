from time import monotonic

from flask import request

from app.utils.response import error_response


class SimpleRateLimiter:
    def __init__(self):
        self.requests = {}

    def reset(self):
        self.requests.clear()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = monotonic()
        window_start, count = self.requests.get(key, (now, 0))

        if now - window_start >= window_seconds:
            window_start = now
            count = 0

        count += 1
        self.requests[key] = (window_start, count)

        retry_after = max(1, int(window_seconds - (now - window_start)))
        return count <= limit, retry_after


rate_limiter = SimpleRateLimiter()


def init_rate_limiter(app):
    rate_limiter.reset()

    @app.before_request
    def check_rate_limit():
        if not app.config.get("RATE_LIMIT_ENABLED", True):
            return None

        limit = int(app.config.get("RATE_LIMIT_REQUESTS", 100))
        window_seconds = int(app.config.get("RATE_LIMIT_WINDOW_SECONDS", 60))
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
        key = f"{client_ip}:{request.endpoint or request.path}"

        allowed, retry_after = rate_limiter.is_allowed(key, limit, window_seconds)
        if allowed:
            return None

        response, status_code = error_response("Too many requests. Please try again later.", 429)
        response.headers["Retry-After"] = str(retry_after)
        return response, status_code
