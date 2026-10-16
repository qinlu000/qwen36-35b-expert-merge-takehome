"""Use the unchanged v2 guard with durable responses before native bash actions."""
from swe_baseline_v2 import SweModelBridge
from swe_logged_relay import LoggedModelRelay


class LoggedSweModelBridge(SweModelBridge):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.relay = LoggedModelRelay(self.relay.socket_path, base_url=self.endpoint + '/v1',
            model=self.model, api_key=self.key, timeout=1800, request_validator=self.validate,
            record_dir=self.logs_dir / 'raw')
