import argparse
from abc import abstractmethod
from typing import Union, Dict, Tuple

from core.definitions import DEFAULT_APID
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class TmTcHookBase:
    from tmtccmd.core.backend import TmTcHandler
    from tmtccmd.utility.tmtc_printer import TmTcPrinter
    from tmtccmd.pus_tm.base import PusTelemetry
    from tmtccmd.pus_tc.base import PusTelecommand
    from tmtccmd.pus_tc.base import TcQueueT
    from tmtccmd.com_if.com_interface_base import CommunicationInterface
    from tmtccmd.pus_tm.service_3_base import Service3Base

    def __init__(self):
        pass

    @abstractmethod
    def get_version(self) -> str:
        from tmtccmd import VERSION_NAME, __version__
        return f"{VERSION_NAME} {__version__}"

    @abstractmethod
    def set_object_ids(self) -> Dict[int, bytearray]:
        pass

    @abstractmethod
    def add_globals_pre_args_parsing(self, gui: bool = False):
        from tmtccmd.defaults.globals_setup import set_default_globals_pre_args_parsing
        set_default_globals_pre_args_parsing(apid=DEFAULT_APID)

    @abstractmethod
    def add_globals_post_args_parsing(self, args: argparse.Namespace):
        from tmtccmd.defaults.globals_setup import set_default_globals_post_args_parsing
        set_default_globals_post_args_parsing(args=args)

    @abstractmethod
    def assign_communication_interface(
            self, com_if: int, tmtc_printer: TmTcPrinter
    ) -> Union[CommunicationInterface, None]:
        from tmtccmd.defaults.com_setup import create_communication_interface_default
        return create_communication_interface_default(com_if=com_if, tmtc_printer=tmtc_printer)

    @abstractmethod
    def perform_mode_operation(self, tmtc_backend: TmTcHandler, mode: int):
        pass

    @abstractmethod
    def pack_service_queue(self, service: int, op_code: str, service_queue: TcQueueT):
        pass

    @abstractmethod
    def pack_total_service_queue(self) -> Union[None, TcQueueT]:
        pass

    @abstractmethod
    def tm_user_factory_hook(self, raw_tm_packet: bytearray) -> Union[None, PusTelemetry]:
        pass

    @abstractmethod
    def command_preparation_hook(self) -> Union[None, PusTelecommand]:
        pass

    @staticmethod
    def custom_args_parsing() -> Union[None, argparse.Namespace]:
        """
        The user can implement args parsing here to override the default argument parsing for
        the CLI mode
        :return:
        """
        return None

    @staticmethod
    def handle_service_8_telemetry(
            object_id: int, action_id: int, custom_data: bytearray
    ) -> Tuple[list, list]:
        """
        This function is called by the TMTC core if a Service 8 data reply (subservice 130)
        is received. The user can return a tuple of two lists, where the first list
        is a list of header strings to print and the second list is a list of values to print.
        The TMTC core will take care of printing both lists and logging them.

        @param object_id:
        @param action_id:
        @param custom_data:
        @return:
        """
        LOGGER.info(
            "TmTcHookBase: No service 8 handling implemented yet in handle_service_8_telemetry "
            "hook function"
        )
        return [], []

    @staticmethod
    def handle_service_3_housekeeping(
        object_id: int, set_id: int, hk_data: bytearray, service3_packet: Service3Base
    ) -> Tuple[list, list, bytearray, int]:
        """
        This function is called when a Service 3 Housekeeping packet is received.
        @param object_id:
        @param set_id:
        @param hk_data:
        @param service3_packet:
        @return: Expects a tuple, consisting of two lists, a bytearray and an integer
        The first list contains the header columns, the second list the list with
        the corresponding values. The bytearray is the validity buffer, which is usually appended
        at the end of the housekeeping packet. The last value is the number of parameters.
        """
        LOGGER.info(
            "TmTcHookBase: No service 3 housekeeping data handling implemented yet in "
            "handle_service_3_housekeeping hook function"
        )
        return [], [], bytearray(), 0



