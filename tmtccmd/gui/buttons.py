import logging
from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtCore import QThreadPool, QRunnable
from PyQt6.QtWidgets import QPushButton

from tmtccmd import HookBase
from tmtccmd.gui.defs import (
    SharedArgs,
    LocalArgs,
    WorkerOperationsCode,
    DISCONNECT_BTTN_STYLE,
    CONNECT_BTTN_STYLE,
    COMMAND_BUTTON_STYLE,
)
from tmtccmd.gui.defs import FrontendState
from tmtccmd.gui.worker import FrontendWorker

_LOGGER = logging.getLogger(__name__)


class ButtonArgs:
    def __init__(
        self,
        state: FrontendState,
        pool: QThreadPool,
        shared: SharedArgs,
    ):
        self.state = state
        self.pool = pool
        self.shared = shared


class ConnectButtonParams:
    def __init__(
        self,
        hook_obj: HookBase,
        connect_cb: Callable[[], None],
        disconnect_cb: Callable[[], None],
        tm_listener_bttn: Optional[QPushButton],
    ):
        self.hook_obj = hook_obj
        self.connect_cb = connect_cb
        self.disconnect_cb = disconnect_cb
        self.tm_listener_bttn = tm_listener_bttn


class ConnectButtonWrapper:
    def __init__(
        self, button: QPushButton, args: ButtonArgs, bttn_params: ConnectButtonParams
    ):
        self.button = button
        self._args = args
        self._bttn_params = bttn_params
        self._connected = False
        self._next_con_state = False
        self._com_if_needs_switch = False
        self.button.clicked.connect(self._button_op)

    def _button_op(self):
        if not self._connected:
            self._connect_button_pressed()
        else:
            self._disconnect_button_pressed()

    def _connect_button_pressed(self):
        _LOGGER.info("Opening COM Interface")
        self._com_if_needs_switch = False
        # Build and assign new communication interface
        if self._args.state.current_com_if != self._args.state.last_com_if:
            self._com_if_needs_switch = True
        self.button.setEnabled(False)
        worker = FrontendWorker.spawn_for_opening_com_if(
            self._com_if_needs_switch,
            self._args.state.current_com_if,
            self._bttn_params.hook_obj,
            self._args.shared,
        )
        self._next_con_state = True
        worker.signals.finished.connect(self._button_op_done)
        # TODO: Connect failure signal as well
        self._args.pool.start(worker)

    def _button_op_done(self):
        if self._next_con_state:
            if self._com_if_needs_switch:
                self._args.state.last_com_if = self._args.state.current_com_if
            self._connect_button_finished()
        else:
            self._disconnect_button_finished()
        self._connected = self._next_con_state

    def _connect_button_finished(self):
        self.button.setStyleSheet(DISCONNECT_BTTN_STYLE)
        self.button.setText("Disconnect")
        self.button.setEnabled(True)
        self._bttn_params.connect_cb()
        if (
            self._args.state.auto_connect_tm_listener
            and self._bttn_params.tm_listener_bttn is not None
        ):
            self._bttn_params.tm_listener_bttn.click()
        _LOGGER.info("Connected")

    def _disconnect_button_pressed(self):
        self.button.setEnabled(False)
        self._next_con_state = False
        worker = FrontendWorker(
            LocalArgs(WorkerOperationsCode.CLOSE_COM_IF, None), self._args.shared
        )
        worker.signals.finished.connect(self._button_op_done)
        self._args.pool.start(worker)

    def _disconnect_button_finished(self):
        self.button.setEnabled(True)
        self.button.setStyleSheet(CONNECT_BTTN_STYLE)
        self.button.setText("Connect")
        self._bttn_params.disconnect_cb()
        _LOGGER.info("Disconnected")


@dataclass
class TmButtonModel:
    style_sheet: str
    text: str
    enabled: bool

    @classmethod
    def disconnected(cls):
        return cls(DISCONNECT_BTTN_STYLE, "Start TM listener", False)

    def set_connected(self):
        self.style_sheet = DISCONNECT_BTTN_STYLE
        self.text = "Stop TM listener"
        self.enabled = True

    def set_disconnected(self):
        self.style_sheet = CONNECT_BTTN_STYLE
        self.text = "Start TM listener"
        self.enabled = False


class TmButtonView:
    def __init__(self, button: QPushButton):
        self.button = button

    def render(self, model: TmButtonModel):
        self.button.setText(model.text)
        self.button.setEnabled(model.enabled)
        self.button.setStyleSheet(model.style_sheet)


class TmButtonController:
    def __init__(
        self,
        view: TmButtonView,
        args: ButtonArgs,
        conn_button: QPushButton,
    ):
        self.view = view
        self.model = TmButtonModel.disconnected()
        self.view.render(self.model)
        self.args = args
        self.worker: Optional[QRunnable] = None
        self._listening = False
        self._next_listener_state = False
        self.view.button.clicked.connect(self.button_op)
        self._conn_button = conn_button

    def render_view(self):
        self.view.render(self.model)

    def is_listening(self):
        return self._listening

    def stop_thread(self):
        if self.worker:
            self.stop_listener()

    def abort_thread(self):
        if self.worker:
            self.worker.signals.abort.emit(None)

    def start_listener(self):
        _LOGGER.info("Starting TM listener")
        self.worker = FrontendWorker(
            LocalArgs(WorkerOperationsCode.LISTEN_FOR_TM, 0.4), self.args.shared
        )
        self._next_listener_state = True
        self._conn_button.setDisabled(True)
        self.args.pool.start(self.worker)
        self.button_op_done()

    def stop_listener(self):
        _LOGGER.info("Stopping TM listener")
        self._next_listener_state = False
        if self.worker is not None:
            self.worker.signals.finished.connect(self.button_op_done)
            self.worker.signals.stop.emit(None)
        self.view.button.setEnabled(False)

    def button_op(self):
        if not self._listening:
            self.start_listener()
        else:
            self.stop_listener()

    def button_op_done(self):
        if self._next_listener_state:
            self.model.set_connected()
            self._listening = True
        else:
            self.model.style_sheet = CONNECT_BTTN_STYLE
            if not self.args.shared.com_if_ref_tracker.is_used():
                self._conn_button.setEnabled(True)
            self.model.text = "Start TM listener"
            self.model.set_disconnected()
            self._listening = False
        self.view.render(self.model)


class SendButtonWrapper:
    def __init__(self, button: QPushButton, args: ButtonArgs, conn_button: QPushButton):
        self.button = button
        self._args = args
        self._conn_button = conn_button
        self.debug_mode = False
        self.button.setText("Send Command")
        self.button.setStyleSheet(COMMAND_BUTTON_STYLE)
        self.button.setEnabled(False)
        self.button.clicked.connect(self._button_op)

    def _button_op(self):
        if self.debug_mode:
            _LOGGER.info("Send command button pressed.")
        self.button.setDisabled(True)
        if self._args.state.current_cmd_path is None:
            return
        worker = FrontendWorker.spawn_for_cmd_path(
            self._args.state.current_cmd_path, self._args.shared
        )
        worker.signals.finished.connect(self._finish_op)
        self._args.pool.start(worker)

    def _finish_op(self):
        self.button.setEnabled(True)
        if not self._args.shared.com_if_ref_tracker.is_used():
            self._conn_button.setEnabled(True)
