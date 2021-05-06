import sys
from typing import Union

from tmtccmd.core.definitions import CoreGlobalIds, CoreComInterfaces
from tmtccmd.core.globals_manager import get_global, update_global
from tmtccmd.com_if.com_interface_base import CommunicationInterface
from tmtccmd.com_if.serial_com_if import SerialConfigIds, SerialCommunicationType
from tmtccmd.com_if.serial_utilities import determine_com_port, determine_baud_rate
from tmtccmd.com_if.tcpip_utilities import TcpIpConfigIds
from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.tmtc_printer import TmTcPrinter


LOGGER = get_logger()


def create_communication_interface_default(
        com_if: int, tmtc_printer: TmTcPrinter, json_cfg_path: str
) -> Union[CommunicationInterface, None]:
    from tmtccmd.com_if.serial_com_if import SerialComIF
    from tmtccmd.com_if.dummy_com_if import DummyComIF
    from tmtccmd.com_if.tcpip_udp_com_if import TcpIpUdpComIF
    from tmtccmd.com_if.qemu_com_if import QEMUComIF
    """
    Return the desired communication interface object
    :param tmtc_printer: TmTcPrinter object.
    :return: CommunicationInterface object
    """
    try:
        if com_if == CoreComInterfaces.TCPIP_UDP:
            ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
            send_addr = ethernet_cfg_dict[TcpIpConfigIds.SEND_ADDRESS]
            recv_addr = ethernet_cfg_dict[TcpIpConfigIds.RECV_ADDRESS]
            max_recv_size = ethernet_cfg_dict[TcpIpConfigIds.RECV_MAX_SIZE]
            init_mode = get_global(CoreGlobalIds.MODE)
            communication_interface = TcpIpUdpComIF(
                tm_timeout=get_global(CoreGlobalIds.TM_TIMEOUT),
                tc_timeout_factor=get_global(CoreGlobalIds.TC_SEND_TIMEOUT_FACTOR),
                send_address=send_addr, recv_addr=recv_addr, max_recv_size=max_recv_size,
                tmtc_printer=tmtc_printer, init_mode=init_mode
            )
        elif com_if == CoreComInterfaces.SERIAL_DLE or \
                com_if == CoreComInterfaces.SERIAL_FIXED_FRAME:
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_baudrate = serial_cfg[SerialConfigIds.SERIAL_BAUD_RATE]
            serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
            # Determine COM port, either extract from JSON file or ask from user.
            com_port = determine_com_port(json_cfg_path=json_cfg_path)
            communication_interface = SerialComIF(
                tmtc_printer=tmtc_printer, com_port=com_port, baud_rate=serial_baudrate,
                serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING)
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(dle_max_queue_len, dle_max_frame_size,
                                                     serial_timeout)
        elif com_if == CoreComInterfaces.SERIAL_QEMU:
            serial_cfg = get_global(CoreGlobalIds.SERIAL_CONFIG)
            serial_timeout = serial_cfg[SerialConfigIds.SERIAL_TIMEOUT]
            communication_interface = QEMUComIF(
                tmtc_printer=tmtc_printer, serial_timeout=serial_timeout,
                ser_com_type=SerialCommunicationType.DLE_ENCODING)
            dle_max_queue_len = serial_cfg[SerialConfigIds.SERIAL_DLE_QUEUE_LEN]
            dle_max_frame_size = serial_cfg[SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE]
            communication_interface.set_dle_settings(
                dle_max_queue_len, dle_max_frame_size, serial_timeout
            )
        else:
            communication_interface = DummyComIF(tmtc_printer=tmtc_printer)
        if not communication_interface.valid:
            LOGGER.warning("Invalid communication interface!")
            sys.exit()
        communication_interface.initialize()
        return communication_interface
    except (IOError, OSError) as e:
        LOGGER.error("Error setting up communication interface")
        print(e)
        sys.exit(1)


def default_tcpip_udp_cfg_setup(json_cfg_path: str):
    from tmtccmd.com_if.tcpip_utilities import determine_udp_send_address, \
        determine_recv_buffer_len, determine_udp_recv_address
    update_global(CoreGlobalIds.USE_ETHERNET, True)
    # This will either load the addresses from a JSON file or prompt them from the user.
    send_tuple = determine_udp_send_address(json_cfg_path=json_cfg_path)
    recv_tuple = determine_udp_recv_address(json_cfg_path=json_cfg_path)
    max_recv_buf_size = determine_recv_buffer_len(json_cfg_path=json_cfg_path, udp=True)
    ethernet_cfg_dict = get_global(CoreGlobalIds.ETHERNET_CONFIG)
    ethernet_cfg_dict.update({TcpIpConfigIds.SEND_ADDRESS: send_tuple})
    ethernet_cfg_dict.update({TcpIpConfigIds.RECV_ADDRESS: recv_tuple})
    ethernet_cfg_dict.update({TcpIpConfigIds.RECV_MAX_SIZE: max_recv_buf_size})
    update_global(CoreGlobalIds.ETHERNET_CONFIG, ethernet_cfg_dict)


def default_serial_cfg_setup(json_cfg_path: str, com_if: int):
    baud_rate = determine_baud_rate(json_cfg_path=json_cfg_path)
    if com_if == CoreComInterfaces.SERIAL_DLE:
        serial_port = determine_com_port(json_cfg_path=json_cfg_path)
    else:
        serial_port = ""
    set_up_serial_cfg(json_cfg_path=json_cfg_path, com_if=com_if, baud_rate=baud_rate, com_port=serial_port)


def set_up_serial_cfg(
        json_cfg_path: str, com_if: int, baud_rate: int, com_port: str = "",  tm_timeout: float = 0.01,
        ser_com_type: SerialCommunicationType = SerialCommunicationType.DLE_ENCODING,
        ser_frame_size: int = 256, dle_queue_len: int = 25, dle_frame_size: int = 1024
):
    """
    Default configuration to set up serial communication. The serial port and the baud rate
    will be determined from a JSON configuration file and prompted from the user
    :param json_cfg_path:
    :param com_if:
    :param com_port:
    :param baud_rate:
    :param tm_timeout:
    :param ser_com_type:
    :param ser_frame_size:
    :param dle_queue_len:
    :param dle_frame_size:
    :return:
    """
    update_global(CoreGlobalIds.USE_SERIAL, True)
    if com_if == CoreComInterfaces.SERIAL_DLE and com_port == "":
        LOGGER.warning("Invalid com port specified!")
        com_port = determine_com_port(json_cfg_path=json_cfg_path)
    serial_cfg_dict = get_global(CoreGlobalIds.SERIAL_CONFIG)
    serial_cfg_dict.update({SerialConfigIds.SERIAL_PORT: com_port})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_BAUD_RATE: baud_rate})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_TIMEOUT: tm_timeout})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_COMM_TYPE: ser_com_type})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_FRAME_SIZE: ser_frame_size})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_QUEUE_LEN: dle_queue_len})
    serial_cfg_dict.update({SerialConfigIds.SERIAL_DLE_MAX_FRAME_SIZE: dle_frame_size})
    update_global(CoreGlobalIds.SERIAL_CONFIG, serial_cfg_dict)
