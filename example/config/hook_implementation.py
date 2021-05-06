import argparse
from typing import Union, Dict, Tuple
from tmtccmd.core.hook_base import \
    TmTcHookBase, TmTcPrinter, CommunicationInterface, TmTcHandler, PusTelemetry, TcQueueT, \
    PusTelecommand, Service3Base
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class ExampleHookClass(TmTcHookBase):

    def set_json_config_file_path(self) -> str:
        return "tmtc_config.json"

    def get_version(self) -> str:
        return "My Version String"

    def add_globals_pre_args_parsing(self, gui: bool = False):
        from tmtccmd.defaults.globals_setup import set_default_globals_pre_args_parsing
        set_default_globals_pre_args_parsing(gui=gui, apid=0xef)

    def add_globals_post_args_parsing(self, args: argparse.Namespace, json_cfg_path: str = ""):
        from tmtccmd.defaults.globals_setup import set_default_globals_post_args_parsing
        set_default_globals_post_args_parsing(args=args, json_cfg_path=json_cfg_path)

    def assign_communication_interface(self, com_if: int, tmtc_printer: TmTcPrinter) -> \
            Union[CommunicationInterface, None]:
        from tmtccmd.defaults.com_setup import create_communication_interface_default
        LOGGER.info("Communication interface assignment function was called")
        return create_communication_interface_default(
            com_if=com_if, tmtc_printer=tmtc_printer, json_cfg_path=self.set_json_config_file_path()
        )

    def perform_mode_operation(self, tmtc_backend: TmTcHandler, mode: int):
        LOGGER.info("Mode operation hook was called")
        pass

    def pack_service_queue(self, service: int, op_code: str, service_queue: TcQueueT):
        from tmtccmd.defaults.tc_packing import default_service_queue_preparation
        LOGGER.info("Service queue packer hook was called")
        default_service_queue_preparation(
            service=service, op_code=op_code, service_queue=service_queue
        )

    def tm_user_factory_hook(self, raw_tm_packet: bytearray) -> PusTelemetry:
        from tmtccmd.defaults.tm_handling import default_factory_hook
        LOGGER.info("TM user factory hook was called")
        return default_factory_hook(raw_tm_packet=raw_tm_packet)

    def set_object_ids(self) -> Dict[bytes, list]:
        pass

    def pack_total_service_queue(self) -> Union[None, TcQueueT]:
        from tmtccmd.defaults.tc_packing import default_total_queue_preparation
        return default_total_queue_preparation()

    def command_preparation_hook(self) -> Union[None, PusTelecommand]:
        LOGGER.info("Single command hook was called")
        from tmtccmd.defaults.tc_packing import default_single_packet_preparation
        return default_single_packet_preparation()

    @staticmethod
    def handle_service_8_telemetry(
            object_id: int, action_id: int, custom_data: bytearray
    ) -> Tuple[list, list]:
        pass

    @staticmethod
    def handle_service_3_housekeeping(
        object_id: int, set_id: int, hk_data: bytearray, service3_packet: Service3Base
    ) -> Tuple[list, list, bytearray, int]:
        pass
