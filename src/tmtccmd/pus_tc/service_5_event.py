from tmtccmd.config.globals import get_global_apid
from tmtccmd.core.definitions import QueueCommands
from tmtccmd.pus_tc.definitions import PusTelecommand, TcQueueT
from tmtccmd.pus.service_5_event import Srv5Subservices


def pack_enable_event_reporting_command(ssc: int, apid: int = -1):
    if apid == -1:
        apid = get_global_apid()
    return PusTelecommand(
        service=5, subservice=Srv5Subservices.ENABLE_EVENT_REPORTING, ssc=ssc, apid=apid
    )


def pack_disable_event_reporting_command(ssc: int, apid: int = -1):
    if apid == -1:
        apid = get_global_apid()
    return PusTelecommand(
        service=5, subservice=Srv5Subservices.DISABLE_EVENT_REPORTING, ssc=ssc, apid=apid
    )


def pack_generic_service5_test_into(tc_queue: TcQueueT, apid: int = -1):
    if apid == -1:
        apid = get_global_apid()
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 5"))
    # invalid subservice
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 5: Invalid subservice"))
    command = PusTelecommand(service=5, subservice=1, apid=apid, ssc=500)
    tc_queue.appendleft(command.pack_command_tuple())
    # disable events
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 5: Disable event"))
    command = pack_disable_event_reporting_command(ssc=501)
    tc_queue.appendleft(command.pack_command_tuple())
    # trigger event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 5: Trigger event"))
    command = PusTelecommand(service=17, subservice=128, apid=apid, ssc=510)
    tc_queue.appendleft(command.pack_command_tuple())
    # enable event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 5: Enable event"))
    command = pack_enable_event_reporting_command(ssc=520)
    tc_queue.appendleft(command.pack_command_tuple())
    # trigger event
    tc_queue.appendleft((QueueCommands.PRINT, "Testing Service 5: Trigger another event"))
    command = PusTelecommand(service=17, subservice=128, apid=apid, ssc=530)
    tc_queue.appendleft(command.pack_command_tuple())
    tc_queue.appendleft((QueueCommands.EXPORT_LOG, "log/tmtc_log_service5.txt"))

