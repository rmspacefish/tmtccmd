import math
import time
import datetime

from crcmod import crcmod

from tmtccmd.ccsds.spacepacket import SpacePacketHeaderDeserializer, SPACE_PACKET_HEADER_SIZE
from tmtccmd.ecss.conf import get_pus_tm_version, PusVersion


class PusTelemetry:
    """
    Generic PUS telemetry class representation.
    It is instantiated by passing the raw pus telemetry packet (bytearray) to the constructor.
    It automatically deserializes the packet, exposing various packet fields via getter functions.
    PUS Telemetry structure according to ECSS-E-70-41A p.46. Also see structure below (bottom).
    """
    CDS_SHORT_SIZE = 7
    PUS_TIMESTAMP_SIZE = CDS_SHORT_SIZE

    def __init__(self, raw_telemetry: bytearray = bytearray()):
        """
        Attempts to construct a generic PusTelemetry class given a raw bytearray.
        Raises a ValueError if the format of the raw bytearray is invalid.
        @param raw_telemetry:
        """
        if raw_telemetry is None or raw_telemetry == bytearray():
            if raw_telemetry is None:
                print("PusTelemetry: Given byte stream ivalid!")
            elif raw_telemetry == bytearray():
                print("PusTelemetry: Given byte stream empty!")
            raise ValueError
        self.pus_version = get_pus_tm_version()
        self._packet_raw = raw_telemetry
        self._space_packet_header = SpacePacketHeaderDeserializer(pus_packet_raw=raw_telemetry)
        self._valid = False
        if self._space_packet_header.data_length + SPACE_PACKET_HEADER_SIZE + 1 > \
                len(raw_telemetry):
            print("PusTelemetry: Passed packet shorter than specified packet length in PUS header")
            raise ValueError
        self._data_field_header = PusPacketDataFieldHeader(
            raw_telemetry[SPACE_PACKET_HEADER_SIZE:], pus_version=self.pus_version
        )
        if self._data_field_header.get_header_size() + SPACE_PACKET_HEADER_SIZE > \
                len(raw_telemetry) - 2:
            print("PusTelemetry: Passed packet too short!")
            raise ValueError
        if self.get_packet_size() != len(raw_telemetry):
            print(f"PusTelemetry: Packet length field {self._space_packet_header.data_length} might be invalid!")
        self._tm_data = raw_telemetry[
            self._data_field_header.get_header_size() + SPACE_PACKET_HEADER_SIZE:-2
        ]
        self._crc = \
            raw_telemetry[len(raw_telemetry) - 2] << 8 | raw_telemetry[len(raw_telemetry) - 1]
        self.print_info = ""
        self.__perform_crc_check(raw_telemetry)

    def __str__(self):
        return f"PUS TM[{self._data_field_header.service_type}," \
               f"{self._data_field_header.service_subtype}] with subcounter " \
               f"{self._data_field_header.subcounter}"

    def __repr__(self):
        return f"{self.__class__.__name__}(service={self._data_field_header.service_subtype!r}, " \
               f"subservice={self._data_field_header.service_subtype!r})"

    def get_service(self):
        """
        :return: Service ID
        """
        return self._data_field_header.service_type

    def get_subservice(self):
        """
        :return: Subservice ID
        """
        return self._data_field_header.service_subtype

    def is_valid(self):
        return self._valid

    def get_tm_data(self) -> bytearray:
        """
        :return: TM application data (raw)
        """
        return self._tm_data

    def get_tc_packet_id(self):
        return self._space_packet_header.packet_id

    def __perform_crc_check(self, raw_telemetry: bytearray):
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        if len(raw_telemetry) < self.get_packet_size():
            print("PusTelemetry: Invalid packet length")
            return
        data_to_check = raw_telemetry[0:self.get_packet_size()]
        crc = crc_func(data_to_check)
        if crc == 0:
            self._valid = True
        else:
            print("PusTelemetry: Invalid CRC detected !")

    def specify_packet_info(self, print_info: str):
        """
        Caches a print information string for later printing
        :param print_info:
        :return:
        """
        self.print_info = print_info

    def append_packet_info(self, print_info: str):
        """
        Similar to the function above, but appends to the existing information string.
        :param print_info:
        :return:
        """
        self.print_info = self.print_info + print_info

    def append_telemetry_content(self, content_list: list):
        """
        Default implementation adds the PUS header content to the list which can then be
        printed with a simple print() command. To add additional content, override this method
        (don't forget to still call this function with super() if the header is required)
        :param content_list: Header content will be appended to this list
        :return:
        """
        self._data_field_header.append_data_field_header(content_list=content_list)
        self._space_packet_header.append_space_packet_header_content(content_list=content_list)
        if self.is_valid():
            content_list.append("Yes")
        else:
            content_list.append("No")

    def append_telemetry_column_headers(self, header_list: list):
        """
        Default implementation adds the PUS header content header (confusing, I know)
        to the list which can then be  printed with a simple print() command.
        To add additional headers, override this method
        (don't forget to still call this function with super() if the header is required)
        :param header_list: Header content will be appended to this list
        :return:
        """
        self._data_field_header.append_data_field_header_column_header(header_list=header_list)
        self._space_packet_header.append_space_packet_header_column_headers(header_list=header_list)
        header_list.append("Packet valid")

    def get_custom_printout(self) -> str:
        """
        Can be used to supply any additional custom printout.
        :return: String which will be printed by TmTcPrinter class as well as logged if specified
        """
        return ""

    def get_raw_packet(self) -> bytearray:
        """
        Get the whole TM packet as a bytearray (raw)
        :return: TM wiretapping_packet
        """
        return bytearray(self._packet_raw)

    def get_packet_size(self) -> int:
        """
        :return: Size of the TM packet based on the space packet header data length field.
        The space packet data field is the full length of data field minus one without the space packet header.
        """
        return SPACE_PACKET_HEADER_SIZE + self._space_packet_header.data_length + 1

    def get_ssc(self) -> int:
        """
        Get the source sequence count
        :return: Source Sequence Count (see below, or PUS documentation)
        """
        return self._space_packet_header.ssc

    def return_full_packet_string(self):
        return return_data_string(self._packet_raw, len(self._packet_raw))

    def print_full_packet_string(self):
        """
        Print the full TM packet in a clean format.
        """
        print(return_data_string(self._packet_raw, len(self._packet_raw)))

    def print_source_data(self):
        """
        Prints the TM source data in a clean format
        :return:
        """
        print(return_data_string(self._tm_data, len(self._tm_data)))

    def return_source_data_string(self):
        """
        Returns the source data string
        """
        return return_data_string(self._tm_data, len(self._tm_data))


class PusPacketDataFieldHeader:
    """
    Unpacks the PUS packet data field header. Currently only supports CDS short timestamps
    """

    def __init__(self, bytes_array: bytearray, pus_version: PusVersion):
        self.pus_version = pus_version
        if len(bytes_array) < self.get_header_size():
            print(f"Invalid PUS data field header size, less than expected {self.get_header_size()} bytes")
            return
        if pus_version == PusVersion.PUS_A:
            self.pus_version_number = (bytes_array[0] & 0x70) >> 4
        else:
            self.pus_version_number = (bytes_array[0] & 0xF0) >> 4
            self.spacecraft_time_ref = bytes_array[0] & 0x0F
        self.service_type = bytes_array[1]
        self.service_subtype = bytes_array[2]
        if pus_version == PusVersion.PUS_A:
            # TODO: This can be optional too, have option to ommit it?
            self.subcounter = bytes_array[3]
        else:
            self.subcounter = bytes_array[3] << 8 | bytes_array[4]
            self.destination_id = bytes_array[5] << 8 | bytes_array[6]
        if pus_version == PusVersion.PUS_A:
            self.time = PusCdsShortTimestamp(bytes_array[4: 4 + PusTelemetry.PUS_TIMESTAMP_SIZE])
        else:
            self.time = PusCdsShortTimestamp(bytes_array[7: 7 + PusTelemetry.PUS_TIMESTAMP_SIZE])

    def append_data_field_header(self, content_list: list):
        """
        Append important data field header parameters to the passed content list.
        :param content_list:
        :return:
        """
        content_list.append(str(self.service_type))
        content_list.append(str(self.service_subtype))
        content_list.append(str(self.subcounter))
        self.time.print_time(content_list)

    def append_data_field_header_column_header(self, header_list: list):
        """
        Append important data field header column headers to the passed list.
        :param header_list:
        :return:
        """
        header_list.append("Service")
        header_list.append("Subservice")
        header_list.append("Subcounter")
        self.time.print_time_headers(header_list)

    def get_header_size(self):
        if self.pus_version == PusVersion.PUS_A:
            return PusTelemetry.PUS_TIMESTAMP_SIZE + 4
        else:
            return PusTelemetry.PUS_TIMESTAMP_SIZE + 7


class PusCdsShortTimestamp:
    """
    Unpacks the time datafield of the TM packet. Right now, CDS Short timeformat is used,
    and the size of the time stamp is expected to be seven bytes.
    TODO: Implement more time formats
    """
    CDS_ID = 4
    SECONDS_PER_DAY = 86400
    EPOCH = datetime.datetime.utcfromtimestamp(0)
    DAYS_CCSDS_TO_UNIX = 4383
    TIMESTAMP_SIZE = PusTelemetry.PUS_TIMESTAMP_SIZE

    def __init__(self, byte_array: bytearray = bytearray([])):
        if len(byte_array) > 0:
            # pField = byte_array[0]
            self.days = ((byte_array[1] << 8) | (byte_array[2])) - \
                        PusCdsShortTimestamp.DAYS_CCSDS_TO_UNIX
            self.seconds = self.days * (24 * 60 * 60)
            s_day = ((byte_array[3] << 24) | (byte_array[4] << 16) |
                     (byte_array[5]) << 8 | byte_array[6]) / 1000
            self.seconds += s_day
            self.time = self.seconds
            self.time_string = \
                datetime.datetime.utcfromtimestamp(self.time).strftime("%Y-%m-%d %H:%M:%S.%f")

    @staticmethod
    def pack_current_time() -> bytearray:
        """
        Returns a seven byte CDS short timestamp
        """
        timestamp = bytearray()
        p_field = (PusCdsShortTimestamp.CDS_ID << 4) + 0
        days = \
            (datetime.datetime.utcnow() - PusCdsShortTimestamp.EPOCH).days + \
            PusCdsShortTimestamp.DAYS_CCSDS_TO_UNIX
        days_h = (days & 0xFF00) >> 8
        days_l = days & 0xFF
        seconds = time.time()
        fraction_ms = seconds - math.floor(seconds)
        days_ms = int((seconds % PusCdsShortTimestamp.SECONDS_PER_DAY) * 1000 + fraction_ms)
        days_ms_hh = (days_ms & 0xFF000000) >> 24
        days_ms_h = (days_ms & 0xFF0000) >> 16
        days_ms_l = (days_ms & 0xFF00) >> 8
        days_ms_ll = (days_ms & 0xFF)
        timestamp.append(p_field)
        timestamp.append(days_h)
        timestamp.append(days_l)
        timestamp.append(days_ms_hh)
        timestamp.append(days_ms_h)
        timestamp.append(days_ms_l)
        timestamp.append(days_ms_ll)
        return timestamp

    def print_time(self, content_list):
        content_list.append(self.time)
        content_list.append(self.time_string)

    @staticmethod
    def print_time_headers(header_list):
        header_list.append("OBSWTime (s)")
        header_list.append("Time")


def return_data_string(byte_array: bytearray, length: int) -> str:
    """
    Returns the TM data in a clean printable string format
    Prints payload data in default mode
    and prints the whole packet if full_packet = True is passed.
    :return:
    """
    str_to_print = "["
    for index in range(length):
        str_to_print += str(hex(byte_array[index])) + " , "
    str_to_print = str_to_print.rstrip()
    str_to_print = str_to_print.rstrip(',')
    str_to_print = str_to_print.rstrip()
    str_to_print += "]"
    return str_to_print

# pylint: disable=line-too-long
# Structure of a PUS Packet :
# A PUS packet consists of consecutive bits, the allocation and structure is standardised.
# Extended information can be found in ECSS-E-70-41A  on p.46
# The easiest form to send a PUS Packet is in hexadecimal form.
# A two digit hexadecimal number equals one byte, 8 bits or one octet
# o = optional, Srv = Service
#
# The structure is shown as follows for TM[17,2]
# 1. Structure Header
# 2. Structure Subheader
# 3. Component (size in bits)
# 4. Hexadecimal number
# 5. Binary Number
# 6. Decimal Number
#
# Packet Structure for PUS A:
#
# -------------------------------------------Packet Header(48)------------------------------------------|   Packet   |
#  ----------------Packet ID(16)----------------------|Packet Sequence Control (16)| Packet Length (16) | Data Field |
# Version       | Type(1) |Data Field    |APID(11)    | SequenceFlags(2) |Sequence |                    | (Variable) |
# Number(3)     |         |Header Flag(1)|            |                  |Count(14)|                    |            |
#           0x18               |    0x73              |       0xc0       | 0x19    |   0x00  |   0x04   |            |
#    000      1      0      000|  01110011            | 11  000000       | 00011001|00000000 | 0000100  |            |
#     0   |   1   |  0     |    115(ASCII s)          | 3 |            25          |   0     |    4     |            |
#
#   - Packet Length is an unsigned integer C = Number of Octets in Packet Data Field - 1
#
# Packet Data Field Structure:
#
# ------------------------------------------------Packet Data Field------------------------------------------------- |
# ---------------------------------Data Field Header --------------------------------------|AppData|Spare|PacketErrCtr |
# Spare(1)|TM PUS Ver.(3)|Spare(4)|SrvType (8)|SrvSubtype(8)|Subcounter(8)|Time(7)|Spare(o)|(var)  |(var)|  (16)       |
#        0x11 (0x1F)              |  0x11     |   0x01      |             |       |        |       |     |     Calc.   |
#    0     001     0000           |00010001   | 00000001    |             |       |        |       |     |             |
#    0      1       0             |    17     |     2       |             |       |        |       |     |             |
#
# - Thus subcounter is specified optional for PUS A, but for this implementation it is expected the subcounter
#   is contained in the raw packet
# - In PUS A, the destination ID can be present as one byte in the spare field. It was omitted for the FSFW
# - In PUS C, the last spare bits of the first byte are replaced by the space time reference field
# - PUS A and PUS C both use the CDS short seven byte timestamp in the time field
# - PUS C has a 16 bit counter sequence counter and a 16 bit destination ID before the time field
