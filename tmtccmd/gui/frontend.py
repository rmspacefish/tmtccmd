"""PyQt front end components for the tmtccmd framework.
@author         R. Mueller, P. Scheurenbrand, D. Nguyen
"""

import os
from collections import deque
import sys
import webbrowser
from multiprocessing import Process
from pathlib import Path
from typing import Any, Tuple

from PyQt6.QtWidgets import (
    QLineEdit,
    QMainWindow,
    QGridLayout,
    QTableWidget,
    QWidget,
    QLabel,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QComboBox,
    QPushButton,
    QTableWidgetItem,
    QMenu,
)
from PyQt6.QtGui import QPixmap, QIcon, QFont, QAction
from PyQt6.QtCore import (
    QTimer,
    Qt,
    QThreadPool,
)

from tmtccmd.core.base import FrontendBase
from tmtccmd.core.ccsds_backend import CcsdsTmtcBackend
from tmtccmd.config import HookBase
from tmtccmd.gui.buttons import (
    ConnectButtonParams,
    ButtonArgs,
    SendButtonWrapper,
    TmButtonController,
    TmButtonView,
    ConnectButtonWrapper,
)
from tmtccmd.gui.cmd_select import CommandPathSelectWidget
from tmtccmd.gui.defs import SharedArgs, CONNECT_BTTN_STYLE, FrontendState
from tmtccmd.logging import get_console_logger
import tmtccmd as mod_root

LOGGER = get_console_logger()


class TmTcFrontend(QMainWindow, FrontendBase):
    def __init__(
        self, hook_obj: HookBase, tmtc_backend: CcsdsTmtcBackend, app_name: str
    ):
        super(TmTcFrontend, self).__init__()
        super(QMainWindow, self).__init__()
        self._app_name = app_name
        self._shared_args = SharedArgs(tmtc_backend)
        tmtc_backend.exit_on_com_if_init_failure = False
        self._hook_obj = hook_obj
        self._com_if_list = []
        self._last_selected_items = deque()
        self._state = FrontendState()
        self._thread_pool = QThreadPool()
        self.logo_path = Path(
            f"{Path(mod_root.__file__).parent.parent}/misc/logo-tiny.png"
        )

    def prepare_start(self, _: Any) -> Process:
        return Process(target=self.start)

    def start(self, qt_app: Any):
        self._start_ui()
        self._enable_periodic_interpreter_run()
        sys.exit(qt_app.exec())

    def _enable_periodic_interpreter_run(self):
        self._interpreter_run_timer = QTimer()
        self._interpreter_run_timer.start(500)  # You may change this if you wish.
        self._interpreter_run_timer.timeout.connect(
            lambda: None
        )  # Let the interpreter run each 500 ms.

    def _start_ui(self):
        self._create_menu_bar()
        win = QWidget(self)
        self.setCentralWidget(win)

        grid = QGridLayout()
        win.setLayout(grid)
        row = 0
        self.setWindowTitle(self._app_name)
        if isinstance(self.logo_path, Path):
            self.setWindowIcon(QIcon(str(self.logo_path)))
        else:
            self.setWindowIcon(QIcon(self.logo_path))

        add_pixmap = False

        if add_pixmap:
            row = self.__set_up_pixmap(grid=grid, row=row)

        row = self.__set_up_config_section(grid=grid, row=row)
        row = self.__add_vertical_separator(grid=grid, row=row)

        tm_listener_button = QPushButton()
        conn_bttn_params = ConnectButtonParams(
            hook_obj=self._hook_obj,
            connect_cb=self.__connected_com_if_cb,
            disconnect_cb=self.__disconnect_com_if_cb,
            tm_listener_bttn=tm_listener_button,
        )
        # com if configuration
        row, self.__connect_button_wrapper = self.__set_up_com_if_section(
            conn_bttn_params=conn_bttn_params, grid=grid, row=row
        )
        row = self.__add_vertical_separator(grid=grid, row=row)

        tmtc_ctrl_label = QLabel("TMTC Control")
        font = QFont()
        font.setBold(True)
        tmtc_ctrl_label.setFont(font)
        grid.addWidget(tmtc_ctrl_label, row, 0, 1, 2)
        row += 1
        row = self._set_up_cmd_path_ui(grid=grid, row=row)

        button_args = ButtonArgs(
            state=self._state, pool=self._thread_pool, shared=self._shared_args
        )
        self.__send_bttn_wrapper = SendButtonWrapper(
            button=QPushButton(),
            args=button_args,
            conn_button=self.__connect_button_wrapper.button,
        )
        grid.addWidget(self.__send_bttn_wrapper.button, row, 0, 1, 2)
        row += 1

        self.__tm_button_ctrl = TmButtonController(
            view=TmButtonView(tm_listener_button),
            args=button_args,
            conn_button=self.__connect_button_wrapper.button,
        )
        grid.addWidget(self.__tm_button_ctrl.view.button, row, 0, 1, 2)
        row += 1
        self.show()
        # self.destroyed.connect(self.__tm_button_wrapper.stop_thread)

    def set_gui_logo(self, logo_total_path: str):
        if os.path.isfile(logo_total_path):
            self.logo_path = logo_total_path
        else:
            LOGGER.warning("Could not set logo, path invalid!")

    def closeEvent(self, event):
        try:
            pass
            if self.__tm_button_ctrl.is_listening():
                LOGGER.warning("TM listener still active. Stopping it first..")
                self.__tm_button_ctrl.stop_thread()
                event.ignore()
            else:
                pass
        except KeyboardInterrupt:
            self.__tm_button_ctrl.abort_thread()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        # Creating menus using a QMenu object
        file_menu = QMenu("&File", self)
        assert menu_bar is not None
        menu_bar.addMenu(file_menu)
        # Creating menus using a title
        help_menu = menu_bar.addMenu("&Help")
        assert help_menu is not None

        help_action = QAction("Help", self)
        help_action.triggered.connect(self.__help_url)
        help_menu.addAction(help_action)

    @staticmethod
    def __help_url():
        webbrowser.open("https://tmtccmd.readthedocs.io/en/latest/")

    def __set_up_config_section(self, grid: QGridLayout, row: int) -> int:
        label = QLabel("Configuration")
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        grid.addWidget(label, row, 0, 1, 2)
        row += 1

        start_listener_on_connect = QCheckBox("Auto-Connect TM listener")
        start_listener_on_connect.setChecked(True)
        start_listener_on_connect.stateChanged.connect(
            lambda: self._tm_auto_connect_changed(start_listener_on_connect)
        )
        grid.addWidget(start_listener_on_connect, row, 0, 1, 1)
        row += 1

        grid.addWidget(QLabel("Inter-Packet Delay Seconds [0 - 500]"), row, 0, 1, 2)
        row += 1

        spin_timeout = QDoubleSpinBox()
        spin_timeout.setValue(0.1)
        # TODO: set sensible min/max values
        spin_timeout.setSingleStep(0.1)
        spin_timeout.setMinimum(0.0)
        spin_timeout.setMaximum(500.0)
        # https://youtrack.jetbrains.com/issue/PY-22908
        # Ignore those warnings for now.
        spin_timeout.valueChanged.connect(self.__number_timeout_changed)
        grid.addWidget(spin_timeout, row, 0, 1, 1)
        row += 1
        return row

    def _tm_auto_connect_changed(self, box: QCheckBox):
        if box.isChecked():
            self._state.auto_connect_tm_listener = True
        else:
            self._state.auto_connect_tm_listener = False

    def __set_up_com_if_section(
        self, conn_bttn_params: ConnectButtonParams, grid: QGridLayout, row: int
    ) -> Tuple[int, ConnectButtonWrapper]:
        font = QFont()
        font.setBold(True)
        label = QLabel("Communication Interface")
        label.setFont(font)
        grid.addWidget(label, row, 0, 1, 1)
        com_if_combo_box = QComboBox()
        all_com_ifs = self._hook_obj.get_com_if_dict()
        index = 0
        # add all possible ComIFs to the comboBox
        for id, com_if_value in all_com_ifs.items():
            com_if_combo_box.addItem(com_if_value[0])
            self._com_if_list.append((id, com_if_value[0]))
            if self._shared_args.backend.com_if_id == id:
                com_if_combo_box.setCurrentIndex(index)
                self._state.current_com_if = id
            index += 1
        com_if_combo_box.currentIndexChanged.connect(self.__com_if_sel_index_changed)
        grid.addWidget(com_if_combo_box, row, 1, 1, 1)
        row += 1

        self.com_if_cfg_button = QPushButton()
        self.com_if_cfg_button.setText("Configure")
        grid.addWidget(self.com_if_cfg_button, row, 0, 1, 2)
        row += 1

        connect_button = QPushButton()
        connect_button.setText("Connect")
        connect_button.setStyleSheet(CONNECT_BTTN_STYLE)
        conn_bttn_wrapper = ConnectButtonWrapper(
            button=connect_button,
            args=ButtonArgs(self._state, self._thread_pool, self._shared_args),
            bttn_params=conn_bttn_params,
        )
        grid.addWidget(connect_button, row, 0, 1, 2)
        row += 1
        return row, conn_bttn_wrapper

    def __disable_conn_bttn(self):
        self.__connect_button_wrapper.button.setDisabled(True)

    def __enable_conn_bttn(self):
        self.__connect_button_wrapper.button.setEnabled(True)

    def __connected_com_if_cb(self):
        self.__send_bttn_wrapper.button.setEnabled(True)
        self.__tm_button_ctrl.model.set_connected()
        self.__tm_button_ctrl.render_view()

    def __disconnect_com_if_cb(self):
        self.__send_bttn_wrapper.button.setDisabled(True)
        self.__tm_button_ctrl.model.set_disconnected()
        self.__tm_button_ctrl.render_view()

    def _set_up_cmd_path_ui(self, grid: QGridLayout, row: int):
        font = QFont()
        font.setBold(True)
        label = QLabel("Communication Select")
        label.setFont(font)
        grid.addWidget(label, row, 0, 1, 1)
        row += 1
        self._open_command_path_select_button = QPushButton("Command Path Select")
        self._open_command_path_select_button.clicked.connect(
            self._open_command_select_widget
        )
        grid.addWidget(self._open_command_path_select_button, row, 0, 1, 2)
        row += 1
        self._cmd_path_text_input = QLineEdit()
        grid.addWidget(self._cmd_path_text_input, row, 0, 1, 2)
        row += 1
        self._confirm_selected_cmd_path_button = QPushButton("Confirm selected path")
        grid.addWidget(self._confirm_selected_cmd_path_button, row, 0, 1, 2)
        row += 1
        self._cmd_path_text = QLabel("Selected command path: ")
        grid.addWidget(self._cmd_path_text, row, 0, 1, 2)
        row += 1
        return row

    def _open_command_select_widget(self):
        self.cmd_select_window = CommandPathSelectWidget(
            self._hook_obj.get_command_definitions(), self._last_selected_items
        )
        self.cmd_select_window.path_selected_sig.connect(self._receive_selected_path)
        self.cmd_select_window.closed.connect(self._on_treeview_closed)
        self.cmd_select_window.show()
        self._open_command_path_select_button.setEnabled(False)

    def _set_cmd_path_label(self, text: str):
        self._cmd_path_text.setText(f"Selected command path: {text}")

    def _confirm_selected_cmd_path(self):
        self._set_cmd_path_label(self._cmd_path_text_input.text())
        self._state.current_cmd_path = self._cmd_path_text_input.text()

    def _on_treeview_closed(self):
        self._open_command_path_select_button.setEnabled(True)

    def _receive_selected_path(self, path: str):
        self._cmd_path_text_input.setText(path)
        self._confirm_selected_cmd_path()

    def __set_up_pixmap(self, grid: QGridLayout, row: int) -> int:
        label = QLabel(self)
        label.setGeometry(720, 10, 100, 100)
        label.adjustSize()

        pixmap = QPixmap(self.logo_path)
        pixmap_width = pixmap.width()
        pixmap_height = pixmap.height()
        row += 1

        pixmap_scaled = pixmap.scaled(
            int(pixmap_width * 0.3),
            int(pixmap_height * 0.3),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        label.setPixmap(pixmap_scaled)
        label.setScaledContents(True)

        grid.addWidget(label, row, 0, 1, 2)
        row += 1
        return row

    @staticmethod
    def __add_vertical_separator(grid: QGridLayout, row: int):
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        grid.addWidget(separator, row, 0, 1, 2)
        row += 1
        return row

    def __com_if_sel_index_changed(self, index: int):
        self._state.current_com_if = self._com_if_list[index][0]
        LOGGER.debug(f"Communication IF updated: {self._com_if_list[index][1]}")

    def __number_timeout_changed(self, value: float):
        LOGGER.info("PUS TM timeout changed to: " + str(value))


class SingleCommandTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setRowCount(1)
        self.setColumnCount(5)
        self.setHorizontalHeaderItem(0, QTableWidgetItem("Service"))
        self.setHorizontalHeaderItem(1, QTableWidgetItem("Subservice"))
        self.setHorizontalHeaderItem(2, QTableWidgetItem("SSC"))
        self.setHorizontalHeaderItem(3, QTableWidgetItem("Data"))
        self.setHorizontalHeaderItem(4, QTableWidgetItem("CRC"))
        self.setItem(0, 0, QTableWidgetItem("17"))
        self.setItem(0, 1, QTableWidgetItem("1"))
        self.setItem(0, 2, QTableWidgetItem("20"))
