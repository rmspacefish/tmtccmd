#!/usr/bin/env python3
import unittest

from unittest import TestCase
from crcmod import crcmod

from tmtccmd.ecss.tc import PusTelecommand
from tmtccmd.ecss.tc import generate_crc, generate_packet_crc
from tmtccmd.ccsds.spacepacket import get_sp_packet_sequence_control
from tmtccmd.ecss.conf import set_default_apid, get_default_apid, PusVersion, get_pus_tm_version
from tmtccmd.pus_tm.service_17_test import Service17TM, Service17TmPacked
from tmtccmd.ecss.tm import PusTelemetry


class TestTelemetry(TestCase):
    def test_space_packet_functions(self):
        psc = get_sp_packet_sequence_control(sequence_flags=0b111, source_sequence_count=42)
        self.assertTrue(psc & 0xc000 == 0xc000)

    def test_generic_pus_c(self):
        pus_17_telecommand = Service17TmPacked(subservice=1, ssc=36)
        pus_17_raw = pus_17_telecommand.pack()
        pus_17_telemetry = None
        def tm_func(raw_telemetry: bytearray): return Service17TM(raw_telemetry=raw_telemetry)
        self.assertRaises(ValueError, tm_func, bytearray())
        self.assertRaises(ValueError, tm_func, None)

        pus_17_telemetry = Service17TM(raw_telemetry=pus_17_raw)
        self.assertTrue(get_pus_tm_version() == PusVersion.PUS_C)
        self.assertTrue(pus_17_telemetry.get_service() == 17)
        self.assertTrue(pus_17_telemetry.get_subservice() == 1)
        self.assertTrue(pus_17_telemetry.get_ssc() == 36)
        self.assertTrue(pus_17_telemetry.get_tm_data() == bytearray())
        self.assertTrue(pus_17_telemetry.is_valid())
        self.assertTrue(pus_17_telemetry.get_custom_printout() == "")
        self.assertTrue(pus_17_telemetry.return_source_data_string() == "[]")
        pus_17_telemetry.print_source_data()
        pus_17_telemetry.print_full_packet_string()
        # This string changes  depending on system time, so its complicated to test its validity
        full_string = pus_17_telemetry.return_full_packet_string()
        print(pus_17_telemetry)
        print(repr(pus_17_telemetry))

        raw_tm_created = pus_17_telemetry.get_raw_packet()
        self.assertTrue(raw_tm_created == pus_17_raw)
        self.assertTrue(pus_17_telemetry.get_tc_packet_id() == 0x8 << 8 | 0xef)

    def test_list_functionality(self):
        pus_17_telecommand = Service17TmPacked(subservice=1, ssc=36)
        pus_17_raw = pus_17_telecommand.pack()
        pus_17_telemetry = Service17TM(raw_telemetry=pus_17_raw)

        header_list = []
        content_list = []
        pus_17_telemetry.append_telemetry_column_headers(header_list=header_list)
        pus_17_telemetry.append_telemetry_content(content_list=content_list)

        self.assertTrue(header_list != [])
        self.assertTrue(content_list != [])


class TestTelecommand(TestCase):

    def test_generic(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        pus_17_telecommand.print()
        self.assertTrue(pus_17_telecommand.get_total_length() == len(pus_17_telecommand.pack()))
        command_tuple = pus_17_telecommand.pack_command_tuple()
        self.assertTrue(len(command_tuple[0]) == pus_17_telecommand.get_total_length())
        print(repr(pus_17_telecommand))
        print(pus_17_telecommand)
        self.assertTrue(pus_17_telecommand.get_packet_id() == (0x18 << 8 | 0xef))
        self.assertTrue(pus_17_telecommand.get_app_data() == bytearray())
        self.assertTrue(pus_17_telecommand.get_apid() == get_default_apid())

        set_default_apid(42)
        self.assertTrue(get_default_apid() == 42)

        test_app_data = bytearray([1, 2, 3])
        pus_17_telecommand_with_app_data = PusTelecommand(service=17, subservice=32, ssc=52, app_data=test_app_data)

        self.assertTrue(len(pus_17_telecommand_with_app_data.get_app_data()) == 3)
        self.assertTrue(pus_17_telecommand_with_app_data.get_app_data() == bytearray([1, 2, 3]))

        pus_17_telecommand_invalid = PusTelecommand(service=493, subservice=5252, ssc=99432942)
        self.assertTrue(pus_17_telecommand_invalid.get_service() == 0)
        self.assertTrue(pus_17_telecommand_invalid.get_subservice() == 0)
        self.assertTrue(pus_17_telecommand_invalid.get_ssc() == 0)

        invalid_input = "hello"
        self.assertTrue(pus_17_telecommand_invalid.get_data_length(invalid_input) == 0)
        self.assertRaises(TypeError, pus_17_telecommand_invalid.get_data_length(invalid_input))

    def test_crc_16(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
        crc = crc_func(pus_17_telecommand.pack())
        self.assertTrue(crc == 0)

        test_data = bytearray([192, 23, 4, 82, 3, 6])
        data_with_crc = generate_crc(test_data)
        crc = crc_func(data_with_crc)
        self.assertTrue(crc == 0)

        packet_raw = pus_17_telecommand.pack()
        packet_raw[len(packet_raw) - 1] += 1
        self.assertTrue(crc_func(packet_raw) != 0)
        packet_raw = generate_packet_crc(packet_raw)
        self.assertTrue(crc_func(packet_raw) == 0)

    def test_getter_functions(self):
        pus_17_telecommand = PusTelecommand(service=17, subservice=1, ssc=25)
        self.assertTrue(pus_17_telecommand.get_ssc() == 25)
        self.assertTrue(pus_17_telecommand.get_service() == 17)
        self.assertTrue(pus_17_telecommand.get_subservice() == 1)


if __name__ == '__main__':
    unittest.main()
