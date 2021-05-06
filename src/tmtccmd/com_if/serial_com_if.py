"""
@file   tmtcc_serial_com_if.py
@brief  SERIAL Communication Interface
@author R. Mueller
@date   01.11.2019
"""
import enum
import threading
import time
import logging
from collections import deque

import serial
import serial.tools.list_ports

from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.utility.tmtc_printer import TmTcPrinter
from tmtccmd.pus_tm.factory import PusTelemetryFactory, PusTmListT
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.dle_encoder import encode_dle, decode_dle, STX_CHAR, ETX_CHAR, DleErrorCodes


LOGGER = get_logger()
SERIAL_FRAME_LENGTH = 256
DLE_FRAME_LENGTH = 1500
HEADER_BYTES_BEFORE_SIZE = 5


class SerialConfigIds(enum.Enum):
    from enum import auto
    SERIAL_PORT = auto()
    SERIAL_BAUD_RATE = auto()
    SERIAL_TIMEOUT = auto()
    SERIAL_COMM_TYPE = auto()
    SERIAL_FRAME_SIZE = auto()
    SERIAL_DLE_QUEUE_LEN = auto()
    SERIAL_DLE_MAX_FRAME_SIZE = auto()


class SerialCommunicationType(enum.Enum):
    """
    Right now, two serial communication methods are supported. One uses frames with a fixed size
    containing PUS packets and the other uses a simple ASCII based transport layer called DLE.
    If DLE is used, it is expected that the sender side encoded the packets with the DLE
    protocol. Any packets sent will also be encoded.
    """
    FIXED_FRAME_BASED = 1
    DLE_ENCODING = 2


# pylint: disable=arguments-differ
class SerialComIF(CommunicationInterface):
    """
    Communication Interface to use serial communication. This requires the PySerial library.
    """
    def __init__(self, tmtc_printer: TmTcPrinter, com_port: str, baud_rate: int,
                 serial_timeout: float,
                 ser_com_type: SerialCommunicationType = SerialCommunicationType.FIXED_FRAME_BASED):
        """
        Initiaze a serial communication handler.
        :param tmtc_printer: TMTC printer object. Can be used for diagnostic purposes, but main
        packet handling should be done by a separate thread.
        :param com_port: Specify COM port.
        :param baud_rate: Specify baud rate
        :param serial_timeout: Specify serial timeout
        :param ser_com_type: Specify how to handle serial reception
        """
        super().__init__(tmtc_printer)

        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial_timeout = serial_timeout
        self.serial = None

        self.ser_com_type = ser_com_type
        if self.ser_com_type == SerialCommunicationType.FIXED_FRAME_BASED:
            # Set to default value.
            self.serial_frame_size = 256
        elif self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
            self.reception_thread = None
            self.reception_buffer = None
            self.dle_polling_active_event = None
            # Set to default value.
            self.dle_queue_len = 10
            self.dle_max_frame = 256
            self.dle_timeout = 0.01

    def __del__(self):
        if self.serial is not None:
            self.close()

    def set_fixed_frame_settings(self, serial_frame_size: int):
        self.serial_frame_size = serial_frame_size

    def set_dle_settings(self, dle_queue_len: int, dle_max_frame: int, dle_timeout: float):
        self.dle_queue_len = dle_queue_len
        self.dle_max_frame = dle_max_frame
        self.dle_timeout = dle_timeout

    def initialize(self, args: any = None) -> any:
        if self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
            self.reception_buffer = deque(maxlen=self.dle_queue_len)
            self.dle_polling_active_event = threading.Event()

    def open(self, args: any = None) -> None:
        try:
            if self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
                self.dle_polling_active_event.set()
                self.reception_thread = threading.Thread(target=self.poll_dle_packets, daemon=True)
            self.serial = serial.Serial(
                port=self.com_port, baudrate=self.baud_rate, timeout=self.serial_timeout)
        except serial.SerialException:
            LOGGER.error("SERIAL Port opening failure!")
            raise IOError
        """
        Needs to be called by application code once for DLE mode!
        """
        if self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
            self.reception_thread.start()

    def close(self, args: any = None) -> None:
        try:
            if self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
                self.dle_polling_active_event.clear()
                self.reception_thread.join(0.4)
            self.serial.close()
        except serial.SerialException:
            logging.warning("SERIAL Port could not be closed!")

    def send_data(self, data: bytearray):
        self.serial.write(data)

    def send_telecommand(self, tc_packet: bytearray, tc_packet_obj: PusTelecommand = None) -> None:
        if self.ser_com_type == SerialCommunicationType.FIXED_FRAME_BASED:
            data = tc_packet
        elif self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
            data = encode_dle(tc_packet)
        else:
            LOGGER.warning("This communication type was not implemented yet!")
            return

        self.send_data(data)

    def receive_telemetry(self, parameters: any = 0) -> PusTmListT:
        packet_list = []
        if self.ser_com_type == SerialCommunicationType.FIXED_FRAME_BASED:
            if self.data_available():
                data = self.serial.read(self.serial_frame_size)
                pus_data_list = self.poll_pus_packets_fixed_frames(bytearray(data))
                for pus_packet in pus_data_list:
                    packet = PusTelemetryFactory.create(pus_packet)
                    if packet is None:
                        continue
                    packet_list.append(packet)
        elif self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
            while self.reception_buffer:
                data = self.reception_buffer.pop()
                dle_retval, decoded_packet, read_len = decode_dle(data)
                if dle_retval == DleErrorCodes.OK:
                    packet = PusTelemetryFactory.create(decoded_packet)
                    if packet is None:
                        continue
                    packet_list.append(packet)
                else:
                    LOGGER.warning("DLE decoder error!")
        else:
            LOGGER.warning("This communication type was not implemented yet!")
        return packet_list

    def data_available(self, timeout: float = 0) -> int:
        elapsed_time = 0
        start_time = time.time()
        sleep_time = timeout / 3.0
        if self.ser_com_type == SerialCommunicationType.FIXED_FRAME_BASED:
            if timeout > 0:
                start_time = time.time()
                elapsed_time = 0
                while elapsed_time < timeout:
                    if self.serial.inWaiting() > 0:
                        return self.serial.inWaiting()
                    elapsed_time = time.time() - start_time
                    time.sleep(sleep_time)
            if self.serial.inWaiting() > 0:
                return self.serial.inWaiting()
        elif self.ser_com_type == SerialCommunicationType.DLE_ENCODING:
            if timeout > 0:
                while elapsed_time < timeout:
                    if self.reception_buffer:
                        return self.reception_buffer.__len__()
                    elapsed_time = time.time() - start_time
                    time.sleep(sleep_time)
            if self.reception_buffer:
                return self.reception_buffer.__len__()
        return 0

    def poll_dle_packets(self):
        while True and self.dle_polling_active_event.is_set():
            # Poll permanently, but it is possible to join this thread every 200 ms
            self.serial.timeout = 0.2
            data = bytearray()
            byte = self.serial.read()
            if len(byte) == 1 and byte[0] == STX_CHAR:
                data.append(byte[0])
                self.serial.timeout = 0.1
                bytes_rcvd = self.serial.read_until(serial.to_bytes([ETX_CHAR]), DLE_FRAME_LENGTH)
                if bytes_rcvd[len(bytes_rcvd) - 1] == ETX_CHAR:
                    data.extend(bytes_rcvd)
                    self.reception_buffer.appendleft(data)
            elif len(byte) >= 1:
                data.append(byte[0])
                data.extend(self.serial.read(self.serial.inWaiting()))
                # It is assumed that all packets are DLE encoded, so throw it away for now.
                LOGGER.info("Non DLE-Encoded data with length " + str(len(data) + 1) + " found..")

    @staticmethod
    def poll_pus_packets_fixed_frames(data: bytearray) -> list:
        pus_data_list = []
        if len(data) == 0:
            return pus_data_list

        payload_length = data[4] << 8 | data[5]
        packet_size = payload_length + 7
        if payload_length == 0:
            return []
        read_size = len(data)
        pus_data = data[0:packet_size]
        pus_data_list.append(pus_data)

        SerialComIF.read_multiple_packets(data, packet_size, read_size, pus_data_list)
        return pus_data_list

    @staticmethod
    def read_multiple_packets(data: bytearray, start_index: int, frame_size: int,
                              pus_data_list: list):
        while start_index < frame_size:
            start_index = SerialComIF.parse_next_packets(data, start_index, frame_size,
                                                         pus_data_list)

    @staticmethod
    def parse_next_packets(data: bytearray, start_index: int, frame_size: int,
                           pus_data_list: list) -> int:
        next_payload_len = data[start_index + 4] << 8 | data[start_index + 5]
        if next_payload_len == 0:
            end_index = frame_size
            return end_index
        next_packet_size = next_payload_len + 7
        # remaining_size = frame_size - start_index

        if next_packet_size > SERIAL_FRAME_LENGTH:
            LOGGER.error("PUS Polling: Very large packet detected, "
                         "packet splitting not implemented yet!")
            LOGGER.error("Detected Size: " + str(next_packet_size))
            end_index = frame_size
            return end_index

        end_index = start_index + next_packet_size
        pus_data = data[start_index:end_index]
        pus_data_list.append(pus_data)
        return end_index


