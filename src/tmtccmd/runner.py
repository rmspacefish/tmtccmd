#!/usr/bin/env python3
"""
:brief:     Core method called by entry point files to initiate the TMTC commander.
            The commander is started by first running initialize_tmtc_commander and then
            running run_tmtc_commander
:details:
:manual:
:author:     R. Mueller
"""
import sys
from typing import Union

from tmtccmd.core.hook_base import TmTcHookBase
from tmtccmd.core.backend import BackendBase
from tmtccmd.core.frontend_base import FrontendBase
from tmtccmd.core.definitions import CoreGlobalIds
from tmtccmd.core.globals_manager import update_global, get_global
from tmtccmd.core.object_id_manager import insert_object_ids
from tmtccmd.defaults.args_parser import parse_input_arguments
from tmtccmd.config.objects import get_core_object_ids
from tmtccmd.utility.tmtcc_logger import set_tmtc_logger, get_logger
from tmtccmd.utility.conf_util import AnsiColors

LOGGER = get_logger()


def initialize_tmtc_commander(hook_object: TmTcHookBase):
    """
    This function needs to be called first before running the TMTC commander core. A hook
    object handle needs to be passed to this function. The user should implement an own hook class
    instance which in turn implemented TmTcHookBase. An instantiation of the hook object is then
    passed to the core. The hook object ecncapsulates the control of the user over the TMTC
    commander core.

    Example for a simple main function content to use the command line mode:

        hook_obj = MyCustomHookClass()
        initialize_tmtccmd(hook_obj)
        run_tmtc_client(False)

    :param hook_object:     Instantiation of a custom hook object. The TMTC core will call the various
                            hook functions during program run-time.
    :raises: ValueError for an invalid hook object.
    """
    __assign_tmtc_commander_hooks(hook_object=hook_object)


def run_tmtc_commander(
        use_gui: bool, reduced_printout: bool = False, ansi_colors: bool = True,
        tmtc_backend: Union[BackendBase, None] = None,
        tmtc_frontend: Union[FrontendBase, None] = None
):
    """
    This is the primary function to run the TMTC commander. Users should call this function to
    start the TMTC commander. Please note that assign_tmtc_commander_hooks needs to be called
    before this function. Raises RuntimeError if initialize_tmtc_commander
    has not been called before calling this function.

    Example for a simple main function content to use the command line mode:

        hook_obj = MyCustomHookClass()
        initialize_tmtccmd(hook_obj)
        run_tmtc_client(False)

    :param use_gui:             Specify whether the GUI is used or not
    :param reduced_printout:    It is possible to reduce the initial printout with this flag
    :param ansi_colors:         Enable ANSI color output for terminal
    :param tmtc_backend:
    :param tmtc_frontend:
    :raises: ValueError if initialize_tmtc_commander was not called before
    :return:
    """
    try:
        __set_up_tmtc_commander(
            use_gui=use_gui, reduced_printout=reduced_printout, ansi_colors=ansi_colors
        )
    except ValueError:
        raise RuntimeError
    if use_gui:
        __start_tmtc_commander_qt_gui(tmtc_frontend=tmtc_frontend)
    else:
        if tmtc_backend is None:
            tmtc_backend = get_default_tmtc_backend()
        __start_tmtc_commander_cli(tmtc_backend=tmtc_backend)


def __assign_tmtc_commander_hooks(hook_object: TmTcHookBase):
    if hook_object is None:
        raise ValueError

    # Check whether all required hook functions have bee implemented properly, Python
    # does not enforce this.
    if hook_object.get_version is None or hook_object.add_globals_pre_args_parsing is None \
            or hook_object.add_globals_post_args_parsing is None:
        LOGGER.error("Passed hook base object handle is invalid. "
                     "Abstract functions have to be implemented!")
        raise ValueError
    # Insert hook object handle into global dictionary so it can be used by the TMTC commander
    update_global(CoreGlobalIds.TMTC_HOOK, hook_object)
    # Set core object IDs
    insert_object_ids(get_core_object_ids())
    # Set object IDs specified by the user.
    insert_object_ids(hook_object.set_object_ids())


def __set_up_tmtc_commander(
        use_gui: bool, reduced_printout: bool, ansi_colors: bool = True,
        tmtc_backend: Union[BackendBase, None] = None
):
    """
    Set up the TMTC commander. Raise ValueError if a passed parameter is invalid.
    :param use_gui:
    :param reduced_printout:
    :param ansi_colors:
    :param tmtc_backend:
    :return:
    """
    from tmtccmd.core.hook_base import TmTcHookBase
    from typing import cast
    set_tmtc_logger()

    # First, we check whether a hook object was passed to the TMTC commander. This hook object
    # encapsulates control of the commnader core so it is required for proper functioning
    # of the commander core.
    hook_obj_raw = get_global(CoreGlobalIds.TMTC_HOOK)
    if hook_obj_raw is None:
        LOGGER.warning(
            "No valid hook object found. initialize_tmtc_commander needs to be called first. Terminating.."
        )
        raise ValueError
    hook_obj = cast(TmTcHookBase, hook_obj_raw)

    if not reduced_printout:
        __handle_init_printout(use_gui, hook_obj.get_version(), ansi_colors)

    LOGGER.info("Starting TMTC Commander..")

    if use_gui:
        hook_obj.add_globals_pre_args_parsing(True)
    else:
        __handle_cli_args_and_globals()


def __handle_init_printout(use_gui: bool, version_string: str, ansi_colors: bool):
    if ansi_colors:
        print(f"{AnsiColors.GREEN}", end="")
    print(f"-- Python TMTC Commander --")
    if use_gui:
        print(f"-- GUI mode --")
    else:
        print(f"-- Command line mode --")

    print(f"-- Software version {version_string} --")
    if ansi_colors:
        print(f"{AnsiColors.RESET}", end="")


def __handle_cli_args_and_globals():
    from typing import cast
    from tmtccmd.core.globals_manager import get_global
    from tmtccmd.defaults.globals_setup import set_json_cfg_path

    hook_obj = cast(TmTcHookBase, get_global(CoreGlobalIds.TMTC_HOOK))
    LOGGER.info("Setting up pre-globals..")
    hook_obj.add_globals_pre_args_parsing(False)

    LOGGER.info("Parsing input arguments..")
    args = parse_input_arguments()
    LOGGER.info("Setting up post-globals..")
    hook_obj.add_globals_post_args_parsing(args=args)


def __start_tmtc_commander_cli(tmtc_backend: BackendBase):
    from tmtccmd.core.backend import TmTcHandler
    hook_obj = get_global(CoreGlobalIds.TMTC_HOOK)
    if not isinstance(hook_obj, TmTcHookBase):
        LOGGER.error(
            "TMTC hook is invalid. Please set it with initialize_tmtc_commander before"
            "starting the program"
        )
        raise ValueError
    __get_backend_init_variables()
    tmtc_backend.initialize()
    tmtc_backend.start()


def __start_tmtc_commander_qt_gui(
        tmtc_frontend: Union[None, FrontendBase] = None
):
    app = None
    if tmtc_frontend is None:
        from tmtccmd.core.frontend import TmTcFrontend
        from tmtccmd.core.backend import TmTcHandler
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            LOGGER.error("PyQt5 module not installed, can't run GUI mode!")
            sys.exit(1)
        app = QApplication(["TMTC Commander"])
        service, op_code, com_if, mode = __get_backend_init_variables()
        # The global variables are set by the argument parser.
        tmtc_backend = TmTcHandler(
            init_com_if=com_if, init_mode=mode, init_service=service, init_opcode=op_code
        )
        tmtc_frontend = TmTcFrontend(tmtc_backend=tmtc_backend)
    tmtc_frontend.start(app)


def __get_backend_init_variables():
    service = get_global(CoreGlobalIds.CURRENT_SERVICE)
    op_code = get_global(CoreGlobalIds.OP_CODE)
    com_if = get_global(CoreGlobalIds.COM_IF)
    mode = get_global(CoreGlobalIds.MODE)
    return service, op_code, com_if, mode


def get_default_tmtc_backend():
    from tmtccmd.core.backend import TmTcHandler
    service, op_code, com_if, mode = __get_backend_init_variables()
    # The global variables are set by the argument parser.
    tmtc_backend = TmTcHandler(
        init_com_if=com_if, init_mode=mode, init_service=service, init_opcode=op_code
    )
    tmtc_backend.set_one_shot_or_loop_handling(get_global(CoreGlobalIds.USE_LISTENER_AFTER_OP))
    return tmtc_backend
