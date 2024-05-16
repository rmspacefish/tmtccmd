from __future__ import annotations
import logging
import time
from typing import Optional, Any

from PyQt6.QtCore import QRunnable, pyqtSlot, QObject, pyqtSignal
from tmtccmd.config.hook import HookBase

from tmtccmd.core import TmMode, TcMode, BackendRequest
from tmtccmd.gui.defs import LocalArgs, SharedArgs, WorkerOperationsCode
from tmtccmd.tmtc.procedure import TreeCommandingProcedure

_LOGGER = logging.getLogger(__name__)


class WorkerSignalWrapper(QObject):
    finished = pyqtSignal(object)
    failure = pyqtSignal(object)
    stop = pyqtSignal(object)
    abort = pyqtSignal(object)


class FrontendWorker(QRunnable):
    def __init__(self, local_args: LocalArgs, shared_args: SharedArgs):
        super(QRunnable, self).__init__()
        self._locals = local_args
        self._shared = shared_args
        self.signals = WorkerSignalWrapper()
        self._stop_signal = False
        self._abort_signal = False
        self.signals.stop.connect(self._stop_com_if)
        self.signals.abort.connect(self._abort)

    @classmethod
    def spawn_for_opening_com_if(
        cls,
        com_if_is_switched: bool,
        com_if_key: str,
        hook: HookBase,
        shared_args: SharedArgs,
    ):
        return cls(
            LocalArgs(
                WorkerOperationsCode.OPEN_COM_IF, (com_if_is_switched, com_if_key, hook)
            ),
            shared_args,
        )

    @classmethod
    def spawn_for_cmd_path(
        cls, cmd_path: str, shared_args: SharedArgs
    ) -> FrontendWorker:
        return cls(
            LocalArgs(WorkerOperationsCode.ONE_QUEUE_MODE, cmd_path), shared_args
        )

    def __setup(self, op_code: WorkerOperationsCode) -> bool:
        if op_code == WorkerOperationsCode.OPEN_COM_IF:
            _LOGGER.info("Switching COM Interface")

            assert isinstance(self._locals.op_args, tuple)
            assert isinstance(self._locals.op_args[0], bool)
            assert isinstance(self._locals.op_args[1], str)
            assert isinstance(self._locals.op_args[2], HookBase)
            # TODO: We should really pass a proper object here instead of using magic tuples..
            new_com_if = self._locals.op_args[2].get_communication_interface(
                com_if_key=self._locals.op_args[1]
            )
            set_success = False
            if new_com_if is not None and self._locals.op_args[0]:
                set_success = self._shared.backend.try_set_com_if(new_com_if)
            if not set_success:
                _LOGGER.warning(
                    f"Could not set new communication interface {new_com_if}"
                )
            if self._shared.backend.com_if_active():
                self._finish_with_info("COM Interface is already active")
            else:
                self._shared.backend.open_com_if()
                self._finish_success()
            return False
        if op_code == WorkerOperationsCode.CLOSE_COM_IF:
            if not self._shared.backend.com_if_active():
                self._finish_with_info("COM Interface is not active")
            elif self._shared.com_if_ref_tracker.is_used():
                self._failure_with_info("Can not close COM interface which is used")
            else:
                _LOGGER.info("Closing COM Interface")
                self._shared.backend.close_com_if()
                self._finish_success()
            return False
        if op_code == WorkerOperationsCode.ONE_QUEUE_MODE:
            self._shared.com_if_ref_tracker.add_user()
            assert isinstance(self._locals.op_args, str)
            with self._shared.tc_lock:
                self._shared.backend.current_procedure = TreeCommandingProcedure(
                    self._locals.op_args
                )
                self._shared.backend.tc_mode = TcMode.ONE_QUEUE
        elif op_code == WorkerOperationsCode.LISTEN_FOR_TM:
            self._shared.com_if_ref_tracker.add_user()
            self._shared.backend.tm_mode = TmMode.LISTENER
        return True

    def __one_queue_mode_cycle(self) -> Optional[bool]:
        self._shared.tc_lock.acquire()
        self._shared.backend.tc_operation()
        self._update_backend_mode()
        state = self._shared.backend.state
        if state.request == BackendRequest.TERMINATION_NO_ERROR:
            self._shared.tc_lock.release()
            self._shared.com_if_ref_tracker.remove_user()
            self._finish_success()
            return False
        elif state.request == BackendRequest.DELAY_IDLE:
            time.sleep(1.0)
        elif state.request == BackendRequest.DELAY_CUSTOM:
            self._shared.tc_lock.release()
            if state.next_delay.total_seconds() < 0.5:
                time.sleep(state.next_delay.total_seconds())
            else:
                time.sleep(0.5)
        elif state.request == BackendRequest.CALL_NEXT:
            self._shared.tc_lock.release()

    def __listener_cycle(self) -> Optional[bool]:
        if self._stop_signal or self._abort_signal:
            self._shared.com_if_ref_tracker.remove_user()
            if not self._abort_signal:
                self._finish_success()
            return False
        else:
            # We only should run the TM operation here
            self._shared.backend.tm_operation()
            # Poll TM every 400 ms for now
            time.sleep(self._locals.op_args)

    def __loop(self, op_code: WorkerOperationsCode) -> bool:
        if op_code == WorkerOperationsCode.ONE_QUEUE_MODE:
            should_return = self.__one_queue_mode_cycle()
            if should_return is not None:
                return should_return
        elif op_code == WorkerOperationsCode.LISTEN_FOR_TM:
            should_return = self.__listener_cycle()
            if should_return is not None:
                return should_return
        elif op_code == WorkerOperationsCode.IDLE:
            return False
        else:
            # This must be a programming error
            _LOGGER.error(f"Unknown worker operation code {self._locals.op_code}")
        return True

    @pyqtSlot()
    def run(self):
        op_code = self._locals.op_code
        loop_required = self.__setup(op_code)
        if loop_required:
            while True:
                if not self.__loop(op_code):
                    break

    def _finish_success(self):
        self.signals.finished.emit(None)

    def _finish_with_info(self, info: str):
        self.signals.finished.emit(info)

    def _failure_with_info(self, info: str):
        self.signals.failure.emit(info)

    def _update_backend_mode(self):
        with self._shared.state_lock:
            self._shared.backend.mode_to_req()

    def _stop_com_if(self, _args: Any):
        self._stop_signal = True

    def _abort(self, _args: Any):
        self._abort_signal = True
