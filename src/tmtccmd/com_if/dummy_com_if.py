"""
:file:      dummy_com_if.py
:date:      09.03.2020
:brief:     Dummy Communication Interface. Currently serves to provide an example without external hardware
"""
from typing import cast

from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.pus_tm.factory import PusTelemetryFactory, PusTmListT
from tmtccmd.pus_tm.service_1_verification import Service1TmPacked
from tmtccmd.pus_tm.service_17_test import Service17TmPacked
from tmtccmd.pus.service_17_test import Srv17Subservices
from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class DummyComIF(CommunicationInterface):
    def __init__(self, tmtc_printer):
        super().__init__(tmtc_printer)
        self.dummy_handler = DummyHandler()
        self.service_sent = 0
        self.tc_ssc = 0
        self.tc_packet_id = 0

    def initialize(self, args: any = None) -> any:
        pass

    def open(self, args: any = None) -> None:
        pass

    def close(self, args: any = None) -> None:
        pass

    def data_available(self, parameters):
        if self.dummy_handler.reply_pending:
            return True
        return False

    def send_data(self, data: bytearray):
        pass

    def receive_telemetry(self, parameters: any = 0) -> PusTmListT:
        return self.dummy_handler.receive_reply_package()

    def send_telecommand(self, tc_packet: bytearray, tc_packet_obj: PusTelecommand = None):
        if tc_packet_obj is not None:
            self.dummy_handler.pass_telecommand(pus_tc=tc_packet_obj)


class DummyHandler:
    def __init__(self):
        self.last_telecommand = None
        self.next_telemetry_package = []
        self.last_tc_ssc = 0
        self.last_tc_packet_id = 0
        self.current_ssc = 0
        self.reply_pending = False

    def pass_telecommand(self, pus_tc: PusTelecommand):
        self.last_telecommand = pus_tc
        self.last_tc_ssc = pus_tc.get_ssc()
        self.last_tc_packet_id = pus_tc.get_packet_id()
        self.reply_pending = True
        self.generate_reply_package()

    def generate_reply_package(self):
        """
        Generate the replies. This function will perform the following steps:
         - Generate an object representation of the telemetry to be generated based on service and subservice
         - Generate the raw bytearray of the telemetry
         - Generate the object representation which would otherwise be generated from the raw bytearray received
           from an external source
        """
        telecommand = cast(PusTelecommand, self.last_telecommand)
        if telecommand.get_service() == 17:
            if telecommand.get_subservice() == 1:
                tm_packer = Service1TmPacked(
                    subservice=1, ssc=self.current_ssc, tc_packet_id=self.last_tc_packet_id,
                    tc_ssc=self.last_tc_ssc
                )

                self.current_ssc += 1
                tm_packet_raw = tm_packer.pack()
                tm_packet = PusTelemetryFactory.create(tm_packet_raw)
                self.next_telemetry_package.append(tm_packet)
                tm_packer = Service1TmPacked(
                    subservice=7, ssc=self.current_ssc, tc_packet_id=self.last_tc_packet_id,
                    tc_ssc=self.last_tc_ssc
                )
                tm_packet_raw = tm_packer.pack()
                tm_packet = PusTelemetryFactory.create(tm_packet_raw)
                self.next_telemetry_package.append(tm_packet)
                self.current_ssc += 1

                tm_packer = Service17TmPacked(subservice=Srv17Subservices.PING_REPLY)
                tm_packet_raw = tm_packer.pack()
                tm_packet = PusTelemetryFactory.create(tm_packet_raw)
                self.next_telemetry_package.append(tm_packet)
                self.current_ssc += 1

    def receive_reply_package(self) -> PusTmListT:
        if self.reply_pending:
            return_list = self.next_telemetry_package.copy()
            self.next_telemetry_package.clear()
            self.reply_pending = False
            return return_list
        else:
            return []
