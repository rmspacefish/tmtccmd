"""Base class for Service 200 mode commanding reply handling.
"""

from __future__ import annotations

import struct
from typing import Optional

from deprecated.sphinx import deprecated
from spacepackets.ccsds.time import CcsdsTimeProvider
from spacepackets.ecss.tm import CdsShortTimestamp, PusTelemetry

from tmtccmd.pus import CustomFsfwPusService
from tmtccmd.pus.s200_fsfw_mode import Subservice
from tmtccmd.tmtc.tm_base import PusTmBase, PusTmInfoBase


class Service200FsfwReader:
    def __init__(self, tm: PusTelemetry) -> None:
        self.tm = tm
        if len(tm.source_data) < 4:
            raise ValueError("service 200 TM can not even hold object ID")
        self.object_id = bytes(tm.source_data[0:4])
        self.return_value = None
        if tm.subservice == Subservice.TM_CANT_REACH_MODE:
            self.return_value = struct.unpack("!H", tm.source_data[4:6])[0]
        self.mode = None
        self.submode = None
        if (
            tm.subservice == Subservice.TM_MODE_REPLY
            or tm.subservice == Subservice.TM_WRONG_MODE_REPLY
        ):
            self.mode = struct.unpack("!I", tm.source_data[4:8])[0]
            self.submode = tm.source_data[8]

    def contains_mode(self) -> bool:
        if self.mode is not None and self.submode is not None:
            return True
        return False

    def is_cant_reach_mode_reply(self) -> bool:
        return self.tm.subservice == Subservice.TM_CANT_REACH_MODE


@deprecated(version="7.0.0", reason="use Service200FsfwReader instead")
class Service200FsfwTm(PusTmBase, PusTmInfoBase):
    @deprecated(version="7.0.0", reason="use Service200FsfwReader instead")
    def __init__(
        self,
        subservice_id: int,
        object_id: bytes,
        time: Optional[CdsShortTimestamp],
        return_value: int = 0,
        mode: int = 0,
        submode: int = 0,
        ssc: int = 0,
        apid: int = -1,
        packet_version: int = 0b000,
        space_time_ref: int = 0b0000,
        destination_id: int = 0,
    ):
        source_data = bytearray()
        source_data.extend(object_id)
        if subservice_id == 7:
            source_data.extend(struct.pack("!H", return_value))
        elif subservice_id == 6 or subservice_id == 8:
            source_data.extend(struct.pack("!I", mode))
            source_data.append(submode)
        pus_tm = PusTelemetry(
            service=CustomFsfwPusService.SERVICE_200_MODE,
            subservice=subservice_id,
            time_provider=time,
            seq_count=ssc,
            source_data=source_data,
            apid=apid,
            packet_version=packet_version,
            space_time_ref=space_time_ref,
            destination_id=destination_id,
        )
        PusTmBase.__init__(self, pus_tm=pus_tm)
        PusTmInfoBase.__init__(self, pus_tm=pus_tm)
        self.set_packet_info("Mode Reply")

        self.is_cant_reach_mode_reply = False
        self.is_mode_reply = False
        self.object_id = object_id
        self.mode = mode
        self.submode = submode
        self.return_value = return_value
        self.__init_without_base(instance=self)

    @staticmethod
    def __init_without_base(instance: Service200FsfwTm):
        tm_data = instance.tm_data
        instance.object_id = bytes(tm_data[0:4])
        if instance.subservice == Subservice.TM_CANT_REACH_MODE:
            instance.append_packet_info(": Can't reach mode")
            instance.is_cant_reach_mode_reply = True
            instance.return_value = tm_data[4] << 8 | tm_data[5]
        elif (
            instance.subservice == Subservice.TM_MODE_REPLY
            or instance.subservice == Subservice.TM_WRONG_MODE_REPLY
        ):
            instance.is_mode_reply = True
            if instance.subservice == Subservice.TM_WRONG_MODE_REPLY:
                instance.append_packet_info(": Wrong Mode")
            elif instance.subservice == Subservice.TM_MODE_REPLY:
                instance.append_packet_info(": Mode reached")
            instance.mode = struct.unpack("!I", tm_data[4:8])[0]
            instance.submode = tm_data[8]

    @classmethod
    def __empty(cls) -> Service200FsfwTm:
        return cls(
            subservice_id=0, object_id=bytearray(4), time=CdsShortTimestamp.empty()
        )

    @classmethod
    def unpack(
        cls, raw_telemetry: bytes, time_reader: Optional[CcsdsTimeProvider]
    ) -> Service200FsfwTm:
        service_200_tm = cls.__empty()
        service_200_tm.pus_tm = PusTelemetry.unpack(
            data=raw_telemetry, time_reader=time_reader
        )
        service_200_tm.__init_without_base(instance=service_200_tm)
        return service_200_tm

    def append_telemetry_content(self, content_list: list):
        super().append_telemetry_content(content_list=content_list)
        object_id_num = struct.unpack("!I", self.object_id)[0]
        content_list.append(f"0x{object_id_num:08x}")
        if self.is_cant_reach_mode_reply:
            content_list.append(hex(self.return_value))
        elif self.is_mode_reply:
            if self.mode == 1:
                mode_string = "ON"
            elif self.mode == 2:
                mode_string = "NORMAL"
            elif self.mode == 3:
                mode_string = "RAW"
            elif self.mode == 0:
                mode_string = "OFF"
            else:
                mode_string = f"UNKNOWN ({self.mode})"
            content_list.append(mode_string)
            content_list.append(str(self.submode))

    def append_telemetry_column_headers(self, header_list: list):
        super().append_telemetry_column_headers(header_list=header_list)
        header_list.append("Object ID")
        if self.is_cant_reach_mode_reply:
            header_list.append("Return Value")
        elif self.is_mode_reply:
            header_list.append("Mode")
            header_list.append("Submode")
