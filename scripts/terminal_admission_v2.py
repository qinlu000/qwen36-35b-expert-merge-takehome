"""Bounded admissions with a file-controlled natural drain for service handoff."""
import asyncio


async def run_queue(entries, statuses, execute, healthy, breaker, save, concurrency=16, stop_file=None):
    pending=[e for e in entries if statuses[e['key']]['state']=='pending']
    active={}
    watch=asyncio.create_task(breaker.event.wait())
    stopping=lambda: stop_file is not None and stop_file.exists()

    async def watch_health():
        while not breaker.event.is_set():
            await asyncio.sleep(1)
            try:
                await healthy()
            except Exception as exc:
                breaker.trip(f'active_health: {type(exc).__name__}: {exc}')

    health_watch=asyncio.create_task(watch_health())
    peak=0
    try:
        while pending or active:
            while pending and len(active)<concurrency and not breaker.event.is_set() and not stopping():
                try:
                    await healthy()
                except Exception as exc:
                    breaker.trip(f'pre_admission_health: {type(exc).__name__}: {exc}')
                    break
                if breaker.event.is_set() or stopping():break
                entry=pending.pop(0)
                statuses[entry['key']]['state']='admitted';save()
                active[asyncio.create_task(execute(entry))]=entry
                peak=max(peak,len(active))
            if breaker.event.is_set() or not active:break
            done,_=await asyncio.wait([watch,*active],return_when=asyncio.FIRST_COMPLETED)
            if watch in done:break
            for task in done:
                active.pop(task)
                await task
        if breaker.event.is_set():
            for task,entry in active.items():
                if entry['key']!=breaker.owner_key and not task.done():task.cancel()
            await asyncio.gather(*active,return_exceptions=True);save()
        return {'admitted_peak':peak,'halted':breaker.event.is_set(),'reason':breaker.reason,
                'drained':stopping() and not active,'pending_not_admitted':len(pending)}
    except asyncio.CancelledError:
        breaker.trip('controller_cancelled; preserve all admitted attempts')
        raise
    finally:
        watch.cancel();health_watch.cancel()
        await asyncio.gather(watch,health_watch,return_exceptions=True)
        for task in active:
            if not task.done():task.cancel()
        await asyncio.gather(*active,return_exceptions=True)
        save()
