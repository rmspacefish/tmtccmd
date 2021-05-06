# -*- coding: utf-8 -*-
"""
:file:      service_5_event.py
:date:      30.12.2019
:brief:     Deserialize PUS Event Report
:author:    R. Mueller
"""
import struct
from tmtccmd.pus.service_list import PusServices
from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.ecss.tm_creator import PusTelemetryCreator
from tmtccmd.pus.service_5_event import Srv5Subservices, Severity
from tmtccmd.utility.tmtcc_logger import get_logger


LOGGER = get_logger()


class Service5TM(PusTelemetry):
    def __init__(self, byte_array, call_srv5_hook: bool = True):
        """
        Deserialize a raw service 5 packet
        :param byte_array:      Raw bytearray to deserialize, containing the service 5 packet.
        :param call_srv5_hook:  Calls the global hook function to retrieve a custom printout for Service 5 packets.
        """
        super().__init__(raw_telemetry=byte_array)
        if self.get_service() != 5:
            LOGGER.warning("This packet is not an event service packet!")

        self.specify_packet_info("Event")
        if self.get_subservice() == Srv5Subservices.INFO_EVENT:
            self.append_packet_info(" Info")
        elif self.get_subservice() == Srv5Subservices.LOW_SEVERITY_EVENT:
            self.append_packet_info(" Error Low Severity")
        elif self.get_subservice() == Srv5Subservices.MEDIUM_SEVERITY_EVENT:
            self.append_packet_info(" Error Med Severity")
        elif self.get_subservice() == Srv5Subservices.HIGH_SEVERITY_EVENT:
            self.append_packet_info(" Error High Severity")
        self.event_id = struct.unpack('>H', self._tm_data[0:2])[0]
        self.object_id = struct.unpack('>I', self._tm_data[2:6])[0]
        self.param_1 = struct.unpack('>I', self._tm_data[6:10])[0]
        self.param_2 = struct.unpack('>I', self._tm_data[10:14])[0]
        self.custom_service_5_print = ""
        if call_srv5_hook:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            self.custom_service_5_print = hook_obj.handle_service_5_event(
                object_id=self._tm_data[2:6], event_id=self.event_id, param_1=self.param_1, param_2=self.param_2
            )

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(str(self.event_id))
        content_list.append(hex(self.object_id))
        content_list.append(str(hex(self.param_1)) + ", " + str(self.param_1))
        content_list.append(str(hex(self.param_2)) + ", " + str(self.param_2))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Event ID")
        header_list.append("Reporter ID")
        header_list.append("Parameter 1")
        header_list.append("Parameter 2")

    def handle_service_5_event(self, object_id: bytearray, event_id: int, param_1: int, param_2: int) -> str:
        try:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            custom_string = hook_obj.handle_service_5_event(
                    object_id=self.object_id, event_id=event_id, param_1=param_1, param_2=param_2
                )
            return custom_string
        except ImportError:
            LOGGER.warning("Service 5 user data hook not supplied!")
        return ""

    def get_custom_printout(self) -> str:
        return self.custom_service_5_print

    def set_custom_printout(self, custom_printout: str):
        self.custom_service_5_print = custom_printout

    def get_reporter_id(self):
        return self.object_id

    def get_event_id(self):
        return self.event_id

    def get_param_1(self):
        return self.param_1

    def get_param_2(self):
        return self.param_2


class Service5TmPacked(PusTelemetryCreator):
    """
    Class representation for Service 5 TM creation.
    """
    def __init__(
            self, severity: Severity, event_id: int, object_id: bytearray = bytearray(),
            param_1: int = 0, param_2: int = 0, ssc: int = 0
    ):
        self.event_id = event_id
        self.object_id = object_id
        self.param_1 = param_1
        self.param_2 = param_2
        source_data = bytearray()
        source_data.extend(struct.pack('!H', self.event_id))
        source_data.extend(object_id)
        source_data.extend(struct.pack('!I', self.param_1))
        source_data.extend(struct.pack('!I', self.param_2))
        super().__init__(
            service=PusServices.SERVICE_5_EVENT, subservice=severity, ssc=ssc,
            source_data=source_data)

    def pack(self) -> bytearray:
        return super().pack()
