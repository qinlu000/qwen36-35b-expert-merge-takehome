"""Read admission routes; an admitted task keeps its original endpoint."""
from datetime import datetime, timezone, timedelta
import json


class TerminalEndpointRoutes:
    def __init__(self, path):
        self.path = path
        self.loads = {}

    def admitting(self):
        endpoints = json.loads(self.path.read_text())['endpoints']
        ready = []
        for endpoint in endpoints:
            url = endpoint['url'].rstrip('/')
            self.loads.setdefault(url, 0)
            end = datetime.fromisoformat(endpoint['allocation_end_time'].replace('Z', '+00:00'))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone(timedelta(hours=8)))
            remaining = (end - datetime.now(timezone.utc)).total_seconds()
            if endpoint['admit'] and remaining >= 35 * 60:
                ready.append(url)
        return ready

    def capacity(self):
        return 30 if self.admitting() else min(30, sum(self.loads.values()))

    def acquire(self):
        ready = self.admitting()
        if not ready:
            return None
        selected = min(ready, key=self.loads.get)
        self.loads[selected] += 1
        return selected

    def release(self, selected):
        self.loads[selected] -= 1

    def health_targets(self):
        return set(self.admitting()) | {url for url, load in self.loads.items() if load}
