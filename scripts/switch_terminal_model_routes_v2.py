"""Admit ready replacements and mark old model consumers only after natural drain."""
import argparse
from datetime import datetime, timezone, timedelta
import fcntl
import json
from pathlib import Path
import time
import urllib.error
import urllib.request


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def alive(pid, expected):
    process = Path('/proc') / str(pid)
    try:
        return expected in (process / 'cmdline').read_text()
    except FileNotFoundError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    lock = args.state.with_suffix('.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    activated = json.loads(args.state.read_text()).get('new_route_activated', False) if args.state.exists() else False
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while True:
        config = json.loads(args.targets.read_text())
        route_path = Path(config['endpoints_config'])
        routes = json.loads(route_path.read_text())
        checks = []
        new = []
        for target in config['new_targets']:
            endpoint = {key: target[key] for key in ('url', 'allocation_end_time', 'job_id', 'max_num_seqs')}
            try:
                with opener.open(target['url'].rstrip('/') + '/health', timeout=2) as response:
                    status = response.status
            except (urllib.error.URLError, TimeoutError, OSError):
                status = None
            end = datetime.fromisoformat(target['allocation_end_time'].replace('Z', '+00:00'))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone(timedelta(hours=8)))
            remaining = (end - datetime.now(timezone.utc)).total_seconds()
            endpoint['admit'] = status == 200 and remaining >= 35 * 60
            new.append(endpoint)
            checks.append({'job_id': target['job_id'], 'url': target['url'],
                'http_health_status': status, 'remaining_seconds': round(remaining), 'admit': endpoint['admit']})
        if any(endpoint['admit'] for endpoint in new):
            activated = True
        if activated:
            old = [{**endpoint, 'admit': False} for endpoint in config['old_targets']]
            endpoints = old + new
            if routes['endpoints'] != endpoints:
                routes.update(updated_at_utc=datetime.now(timezone.utc).isoformat(), endpoints=endpoints,
                    requested_model_max_num_seqs=20,
                    note='New ready20 services receive future admissions; old admitted tasks keep their original endpoints')
                write_json(route_path, routes)
        old_exited = not alive(config['old_controller_pid'], 'runtime10/scripts/run_terminal_native7.py')
        launch_path = Path(config['new_launch_receipt'])
        launch = json.loads(launch_path.read_text()) if launch_path.exists() else {}
        new_alive = bool(launch.get('pid')) and alive(launch['pid'], 'runtime11/scripts/run_terminal_routing_v2.py')
        checkpoint = json.loads(Path(config['checkpoint']).read_text())
        active = [status for status in checkpoint['statuses'].values() if status['state'] == 'admitted']
        old_urls = {endpoint['url'] for endpoint in config['old_targets']}
        old_active = [status for status in active if status.get('fixed_model_endpoint') in old_urls]
        assigned = all(status.get('fixed_model_endpoint') for status in active)
        finished = activated and old_exited and new_alive and not old_active and assigned
        if finished:
            for endpoint in config['old_targets']:
                marker = Path(endpoint['consumer_finished_marker'])
                marker.parent.mkdir(exist_ok=True, parents=True)
                if not marker.exists():
                    write_json(marker, {'at_utc': datetime.now(timezone.utc).isoformat(),
                        'job_id': endpoint['job_id'], 'endpoint': endpoint['url'],
                        'model_consumer_finished': True, 'benchmark_complete': False,
                        'old_controller_exited': True, 'new_controller_pid': launch['pid'],
                        'new_controller_alive': True, 'old_endpoint_admitted_tasks': 0,
                        'active_trial_count_at_marker': len(active),
                        'evidence': {'checkpoint': config['checkpoint'],
                            'launch_receipt': config['new_launch_receipt'], 'endpoints': str(route_path)}})
        write_json(args.state, {'at_utc': datetime.now(timezone.utc).isoformat(),
            'new_route_activated': activated, 'health_checks': checks,
            'old_controller_exited': old_exited, 'new_controller_pid': launch.get('pid'),
            'new_controller_alive': new_alive, 'active_trials': len(active),
            'old_endpoint_active_trials': len(old_active),
            'old_model_consumer_markers_written': finished,
            'requested_model_max_num_seqs': 20, 'current_routes': routes['endpoints']})
        time.sleep(2)


if __name__ == '__main__':
    main()
