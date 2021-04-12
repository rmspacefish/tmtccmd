from crcmod import crcmod

from tmtccmd.ecss.tm import PusCdsShortTimestamp, PusTelemetry
from tmtccmd.ccsds.spacepacket import PacketTypes, SpacePacketHeaderSerializer
from tmtccmd.ecss.conf import get_tm_apid, PusVersion, get_pus_tm_version


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
class PusTelemetryCreator:
    """
    Alternative way to create a PUS Telemetry packet by specifying telemetry parameters,
    similarly to the way telecommands are created. This can be used to create telemetry
    directly in the software. See documentation and more information related to
    the ESA PUS standard in the PusTelemetry documentation.
    """
    def __init__(self, service: int, subservice: int, ssc: int = 0,
                 source_data: bytearray = bytearray([]), apid: int = -1, version: int = 0b000,
                 pus_version: PusVersion = PusVersion.UNKNOWN, pus_tm_version: int = 0b0001,
                 ack: int = 0b1111, secondary_header_flag: int = -1):
        """
        Initiates the unserialized data fields for the PUS telemetry packet.
        """
        if apid == -1:
            apid = get_tm_apid()
        if pus_version == PusVersion.UNKNOWN:
            pus_version = get_pus_tm_version()
        self.pus_version = pus_version
        # packet type for telemetry is 0 as specified in standard
        # specified in standard
        data_field_header_flag = 1
        packet_type = PacketTypes.PACKET_TYPE_TM
        data_length = self.get_source_data_length(timestamp_len=PusTelemetry.PUS_TIMESTAMP_SIZE)
        self._space_packet_header = SpacePacketHeaderSerializer(
            apid=apid, packet_type=packet_type, secondary_header_flag=secondary_header_flag,
            version=version, data_length=data_length, source_sequence_count=ssc
        )
        self.pus_version_and_ack_byte = pus_tm_version | ack
        # NOTE: In PUS-C, the PUS Version is 2 and specified for the first 4 bits.
        # The other 4 bits of the first byte are the spacecraft time reference status
        # To change to PUS-C, set 0b00100000
        self.data_field_version = 0b00010000
        self.service = service
        self.subservice = subservice
        self.pack_subcounter = 0
        # it is assumed the time field consts of 8 bytes.

        self.source_data = source_data

    def print(self):
        """ Print the raw command in a clean format. """
        packet = self.pack()
        print_out = "Telemetry in Hexadecimal: ["
        for counter in range(len(packet)):
            if counter == len(packet) - 1:
                print_out += str(hex(packet[counter]))
            else:
                print_out += str(hex(packet[counter])) + ", "
        print_out += "]"
        print(print_out)

    def pack(self) -> bytearray:
        """
        Serializes the PUS telemetry into a raw packet.
        """
        tm_packet_raw = bytearray()
        # PUS Header
        tm_packet_raw.extend(self._space_packet_header.pack())
        # PUS Source Data Field
        tm_packet_raw.append(self.data_field_version)
        tm_packet_raw.append(self.service)
        tm_packet_raw.append(self.subservice)
        tm_packet_raw.append(self.pack_subcounter)
        tm_packet_raw.extend(PusCdsShortTimestamp.pack_current_time())
        # Source Data
        tm_packet_raw.extend(self.source_data)
        # CRC16 checksum
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc16 = crc_func(tm_packet_raw)
        tm_packet_raw.append((crc16 & 0xFF00) >> 8)
        tm_packet_raw.append(crc16 & 0xFF)
        return tm_packet_raw

    def get_source_data_length(self, timestamp_len: int) -> int:
        """
        Retrieve size of TM packet data header in bytes.
        Formula according to PUS Standard: C = (Number of octets in packet source data field) - 1.
        The size of the TM packet is the size of the packet secondary header with
        the timestamp + the length of the application data + PUS timestamp size +
        length of the CRC16 checksum - 1
        """
        try:
            data_length = 4 + timestamp_len + len(self.source_data) + 1
            return data_length
        except TypeError:
            print("PusTelecommand: Invalid type of application data!")
            return 0
