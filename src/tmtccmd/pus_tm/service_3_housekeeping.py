# -*- coding: utf-8 -*-
"""
@file       service_3_housekeeping.py
@date       07.04.2021
@details    Deserialize Housekeeping TM
@author     R. Mueller
"""

from tmtccmd.ecss.tm import PusTelemetry
from tmtccmd.pus_tm.service_3_base import Service3Base
from tmtccmd.utility.tmtcc_logger import get_logger
from typing import Type
import struct

LOGGER = get_logger()


class Service3TM(Service3Base):
    """
    @brief  This class encapsulates the format of Service 3 telemetry
    @details
    This class was written to handle Service 3 telemetry coming from the on-board software
    based on the Flight Software Framework (FSFW). A custom class can be defined, but should then
    implement Service3Base.
    """
    # Minimal packet contains SID, which consists of object ID(4) and set ID(4)
    DEFAULT_MINIMAL_PACKET_SIZE = 8
    # Minimal structure report contains SID (8), reporting status(1), validity flag (1),
    # collection interval as float (4) and number of parameters(1)
    STRUCTURE_REPORT_FIXED_HEADER_SIZE = DEFAULT_MINIMAL_PACKET_SIZE + 7

    def __init__(self, byte_array: bytearray, custom_hk_handling: bool = False,
                 minimum_reply_size: int = DEFAULT_MINIMAL_PACKET_SIZE,
                 minimum_structure_report_header_size: int = STRUCTURE_REPORT_FIXED_HEADER_SIZE):
        """
        Service 3 packet class representation which can be built from a raw bytearray
        :param byte_array:
        :param custom_hk_handling:  Can be used if a custom HK format is used which does not
                                    use a 8 byte structure ID (SID).
        :param minimum_reply_size:
        :param minimum_structure_report_header_size:
        """
        from tmtccmd.core.object_id_manager import get_object_id_info
        super().__init__(byte_array)
        if len(self._tm_data) < 8:
            warning = "Service3TM: handle_filling_definition_arrays: Invalid Service 3 packet," \
                      " is too short!"
            LOGGER.warning(warning)
            return
        self.min_hk_reply_size = minimum_reply_size
        self.custom_hk_handling = custom_hk_handling
        self.hk_structure_report_header_size = minimum_structure_report_header_size
        self.object_id_bytes = self._tm_data[0:4]
        self.object_id = struct.unpack('!I', self.object_id_bytes)[0]
        self.set_id = struct.unpack('!I', self._tm_data[4:8])[0]

        self.specify_packet_info("Housekeeping Packet")
        self.param_length = 0
        if self.get_subservice() == 10 or self.get_subservice() == 12:
            self.handle_filling_definition_arrays()
        if self.get_subservice() == 25 or self.get_subservice() == 26:
            self.handle_filling_hk_arrays()

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        content_list.append(hex(self.object_id))
        content_list.append(hex(self.set_id))
        content_list.append(int(self.param_length))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        header_list.append("Set ID")
        header_list.append("HK Data Size")

    def handle_filling_definition_arrays(self):
        if len(self._tm_data) < self.hk_structure_report_header_size:
            LOGGER.warning(
                f"Service3TM: handle_filling_definition_arrays: Invalid structure report "
                f"from {hex(self.object_id)}, is shorter "
                f"than {self.hk_structure_report_header_size}"
            )
            return
        self.hk_header = ["Object ID", "Set ID", "Report Status", "Is valid",
                          "Collection Interval (s)", "Number Of IDs"]
        reporting_enabled = self._tm_data[8]
        set_valid = self._tm_data[9]
        collection_interval_seconds = struct.unpack('>f', self._tm_data[10:14])[0] / 1000.0
        num_params = self._tm_data[14]
        if len(self._tm_data) < self.hk_structure_report_header_size + num_params * 4:
            LOGGER.warning(
                f"Service3TM: handle_filling_definition_arrays: Invalid structure report " 
                f"from {hex(self.object_id)}, is shorter than "
                f"{self.hk_structure_report_header_size + num_params * 4}"
            )
            return

        parameters = []
        counter = 1
        for array_index in range(
                self.hk_structure_report_header_size,
                self.hk_structure_report_header_size + 4 * num_params, 4
        ):
            parameter = struct.unpack('>I', self._tm_data[array_index:array_index + 4])[0]
            self.hk_header.append("Pool ID " + str(counter))
            parameters.append(str(hex(parameter)))
            counter = counter + 1
        if reporting_enabled == 1:
            status_string = "On"
        else:
            status_string = "Off"
        if set_valid:
            valid_string = "Yes"
        else:
            valid_string = "No"
        self.hk_content = [hex(self.object_id), self.set_id, status_string, valid_string,
                           collection_interval_seconds, num_params]
        self.hk_content.extend(parameters)

    def handle_filling_hk_arrays(self):
        try:
            from tmtccmd.core.hook_helper import get_global_hook_obj
            hook_obj = get_global_hook_obj()
            if self.custom_hk_handling:
                (self.hk_header, self.hk_content, self.validity_buffer, self.number_of_parameters) \
                    = hook_obj.handle_service_3_housekeeping(
                        object_id=bytearray(), set_id=0, hk_data=self._tm_data[0:],
                        service3_packet=self
                    )
            else:
                (self.hk_header, self.hk_content, self.validity_buffer,
                 self.number_of_parameters) = \
                    hook_obj.handle_service_3_housekeeping(
                        object_id=self.object_id_bytes, set_id=self.set_id, hk_data=self._tm_data[8:],
                        service3_packet=self
                    )
        except ImportError:
            LOGGER.warning("Service3TM: User HK handling file missing!")
            return


Service3TM: Type[PusTelemetry]
