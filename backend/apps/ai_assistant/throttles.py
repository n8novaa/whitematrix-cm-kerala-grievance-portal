from rest_framework.throttling import ScopedRateThrottle


class AIAnalysisThrottle(ScopedRateThrottle):
    """Discard corrupt/future cache entries so retry times stay within the rate window."""

    def allow_request(self, request, view):
        self.scope = getattr(view, self.scope_attr, None)
        self.rate = self.get_rate() if self.scope else None
        if self.rate:
            self.num_requests, self.duration = self.parse_rate(self.rate)
            key = self.get_cache_key(request, view)
            history = self.cache.get(key, []) if key else []
            now = self.timer()
            valid_history = [
                timestamp for timestamp in history
                if isinstance(timestamp, (int, float)) and timestamp <= now
            ] if isinstance(history, list) else []
            if valid_history != history:
                if key:
                    self.cache.set(key, valid_history, self.duration)
        return super().allow_request(request, view)

    def wait(self):
        wait = super().wait()
        if wait is None:
            return None
        return min(self.duration, max(0, wait))
