# -*- coding: utf-8 -*-
"""
:file:      tmtcc_com_interface_base.py
:data:      01.11.2019
:details:
Generic Communication Interface. Defines the syntax of the communication functions.
Abstract methods must be implemented by child class (e.g. Ethernet Com IF)

:author:     R. Mueller
"""
from abc import abstractmethod

from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.pus_tm.factory import PusTmListT
from tmtccmd.utility.tmtc_printer import TmTcPrinter


# pylint: disable=useless-return
# pylint: disable=no-self-use
# pylint: disable=unused-argument
class CommunicationInterface:
    """
    Generic form of a communication interface to separate communication logic from
    the underlying interface.
    """
    def __init__(self, tmtc_printer: TmTcPrinter):
        self.tmtc_printer = tmtc_printer
        self.valid = True

    @abstractmethod
    def initialize(self, args: any = None) -> any:
        """
        Perform initializations step which can not be done in constructor or which require
        returnvalues.
        """

    @abstractmethod
    def open(self, args: any = None) -> None:
        """
        Opens the communication interface to allow communication.
        @return:
        """

    @abstractmethod
    def close(self, args: any = None) -> None:
        """
        Closes the ComIF and releases any held resources (for example a Communication Port)
        :return:
        """

    @abstractmethod
    def send_data(self, data: bytearray):
        """
        Send raw data
        """

    @abstractmethod
    def send_telecommand(self, tc_packet: bytearray, tc_packet_obj: PusTelecommand) -> None:
        """
        Send telecommands.
        :param tc_packet: TC wiretapping_packet to send
        :param tc_packet_obj: TC packet object representation
        :return: None for now
        """

    @abstractmethod
    def receive_telemetry(self, parameters: any = 0) -> PusTmListT:
        """
        Returns a list of packets. The child class can use a separate thread to poll for
        the packets or use some other mechanism and container like a deque to store packets
        to be returned here.
        :param parameters:
        :return:
        """
        packet_list = []
        return packet_list

    @abstractmethod
    def data_available(self, parameters: any) -> int:
        """
        Check whether TM data is available
        :param parameters: Can be an arbitrary parameter like a timeout
        :return: 0 if no data is available, number of bytes or anything > 0 otherwise.
        """
