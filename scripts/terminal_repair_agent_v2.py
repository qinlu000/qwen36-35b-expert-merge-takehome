"""Keep Terminus behavior; a dead terminal still receives native verification."""
import asyncio

from harbor.agents.installed.base import NonZeroAgentExitCodeError
from terminal_recovery_v2 import RecoveryTerminalBaselineV2


class TerminalRepairAgent(RecoveryTerminalBaselineV2):
    async def run(self, instruction, environment, context):
        reason = 'native_return'
        try:
            await super().run(instruction, environment, context)
        except RuntimeError as exc:
            reason = str(exc)
            if ('tmux send-keys' in reason and 'failed to send' in reason and
                    any(text in reason for text in ('no server running', "can't find session", "can't find pane"))):
                context.metadata = context.metadata or {}
                context.metadata['repair_terminal_session_ended'] = reason
                raise NonZeroAgentExitCodeError(reason) from exc
            raise
        except BaseException as exc:
            reason = f'{type(exc).__name__}: {exc}'
            raise
        finally:
            # This runs before the trial restores verifier networking/uploads
            # tests, including on the original 1800-second solver timeout.
            context.metadata = context.metadata or {}
            snapshot = asyncio.create_task(environment._save_final_state(reason))
            cancelled = None
            try:
                while not snapshot.done():
                    try:
                        await asyncio.shield(snapshot)
                    except asyncio.CancelledError as exc:
                        cancelled = exc
                context.metadata['repair_final_state'] = snapshot.result()
            except Exception as exc:
                context.metadata['repair_final_state_error'] = f'{type(exc).__name__}: {exc}'
                self.logger.warning('Final task state capture failed: %s', exc)
            if cancelled is not None:
                raise cancelled
