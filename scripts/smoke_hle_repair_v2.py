"""Synthetic outage/cancellation/manifest check; zero real model requests."""
import asyncio
import json
from pathlib import Path
import tempfile

from repair_hle_infrastructure_v2 import bounded_queue, manual_manifest


async def main():
    entries = [{'id': str(i)} for i in range(100)]
    admitted, cancelled, rows = [], [], []
    online = True

    async def healthy():
        return online

    async def blocked(entry):
        admitted.append(entry['id'])
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(entry['id'])
            raise

    async def disconnect():
        nonlocal online
        while len(admitted) < 8:
            await asyncio.sleep(.001)
        online = False

    fault = asyncio.create_task(disconnect())
    state = await bounded_queue(entries, blocked, healthy, rows.append, interval=.01)
    await fault
    assert state['state'] == 'paused_infrastructure'
    assert len(admitted) == len(cancelled) == 8 and state['not_admitted'] == 92
    failed = set(admitted)
    online = True

    async def completed(entry):
        admitted.append(entry['id'])
        await asyncio.sleep(.001)
        # Genuine timeout/model failure is terminal and does not trip the breaker.
        return {'status': 'failed', 'error_type': 'TimeoutError'}

    resume = await bounded_queue([e for e in entries if e['id'] not in failed], completed,
                                 healthy, rows.append, interval=.01)
    assert resume['state'] == 'completed' and len(set(admitted)) == len(admitted) == 100
    online = False
    offline = await bounded_queue(entries, completed, healthy, rows.append, interval=.01)
    assert not offline['admitted']
    with tempfile.TemporaryDirectory(prefix='hle-manifest-synthetic-') as tmp:
        source = Path(tmp)
        (source / 'questions').mkdir()
        for i in range(2500):
            r = {'id': str(i), 'status': 'failed', 'attempts': []}
            if i < 309:
                r.update(status='completed', raw_response={'synthetic': True})
            elif i < 821:
                r['error_type'] = 'TimeoutError'
            else:
                r['error_type'] = 'RemoteProtocolError'
                if i >= 2492:
                    r['attempts'] = [{'path': '/v1/chat/completions'}]
            (source / 'questions' / (str(i) + '.json')).write_text(json.dumps(r))
        manifest = manual_manifest(source)
        assert len(manifest['selected']) == 1679 and len(manifest['retained']) == 821
    print(json.dumps({'passed': True, 'real_model_calls': 0, 'peak_admitted': 8,
        'outage_admitted': 8, 'outage_untouched': 92, 'cancelled': 8,
        'recovered_only_unsubmitted': 92, 'duplicates': 0, 'initial_offline_admitted': 0,
        'manifest_selected': 1679, 'manifest_retained': 821,
        'budget_timeouts_unchanged': True}))


if __name__ == '__main__':
    asyncio.run(main())
