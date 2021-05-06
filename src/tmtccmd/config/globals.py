import collections.abc
from typing import List, Union

from tmtccmd.utility.tmtcc_logger import get_logger
from tmtccmd.utility.conf_util import check_args_in_enum
from tmtccmd.core.definitions import CoreGlobalIds, CoreModeList, CoreComInterfaces,\
    CoreServiceList, CoreComInterfacesString, CoreModeStrings
from tmtccmd.core.globals_manager import update_global, get_global

LOGGER = get_logger()


def get_global_apid() -> int:
    return get_global(CoreGlobalIds.APID)


def check_and_set_core_mode_arg(
        mode_arg: any,
        custom_modes_list: Union[None, List[Union[dict, collections.abc.Iterable]]] = None
) -> int:
    """
    Checks whether the mode argument is contained inside the core mode list integer enumeration
    or a custom mode list integer which can be passed optionally.
    This function will set the single command mode as the global mode parameter if the passed mode
    is not found in either enumerations.
    :param mode_arg:
    :param custom_modes_list:
    :return:
    """
    in_enum, mode_value = check_args_in_enum(
        param=mode_arg, iterable=CoreModeList, warning_hint="mode integers"
    )
    if not in_enum:
        in_enum, mode_value = check_args_in_enum(
            param=mode_arg, iterable=CoreModeStrings, warning_hint="mode strings"
        )
    if in_enum:
        update_global(CoreGlobalIds.MODE, mode_value)
        return mode_value

    mode_arg_invalid = False
    if custom_modes_list is not None:
        for custom_mode_entry in custom_modes_list:
            in_enum, mode_value = check_args_in_enum(
                param=mode_arg, iterable=custom_mode_entry, warning_hint="custom mode"
            )
            if in_enum:
                break
        if not in_enum:
            mode_arg_invalid = True
    else:
        mode_arg_invalid = True

    if mode_arg_invalid:
        LOGGER.warning(f"Passed mode argument might be invalid, "
                       f"setting to {CoreModeList.SINGLE_CMD_MODE}")
        mode_value = CoreModeList.SINGLE_CMD_MODE
    update_global(CoreGlobalIds.MODE, mode_value)


def check_and_set_core_com_if_arg(
        com_if_arg: any,
        custom_com_ifs_list: Union[None, List[Union[dict, collections.abc.Iterable]]] = None
) -> int:
    in_enum, com_if_value = check_args_in_enum(
        param=com_if_arg, iterable=CoreComInterfaces, warning_hint="communication interface"
    )
    if not in_enum:
        in_enum, com_if_value = check_args_in_enum(
            param=com_if_arg, iterable=CoreComInterfacesString,
            warning_hint="communication interface"
        )
    if in_enum:
        update_global(CoreGlobalIds.COM_IF, com_if_value)
        return com_if_value
    com_if_arg_invalid = False
    if custom_com_ifs_list is not None:
        for custom_com_ifs_entry in custom_com_ifs_list:
            in_enum, com_if_value = check_args_in_enum(
                param=com_if_arg, iterable=custom_com_ifs_entry,
                warning_hint="custom communication interface"
            )
            if in_enum:
                break
        if not in_enum:
            com_if_arg_invalid = True
    else:
        com_if_arg_invalid = True

    if com_if_arg_invalid:
        LOGGER.warning(f"Passed communication interface argument might be invalid, "
                       f"setting to {CoreComInterfaces.DUMMY}")
        com_if_value = CoreComInterfaces.DUMMY
    update_global(CoreGlobalIds.COM_IF, com_if_value)
    return com_if_value


def check_and_set_core_service_arg(
        service_arg: any, custom_service_list: collections.abc.Iterable = None
):
    in_enum, service_value = check_args_in_enum(
        param=service_arg, iterable=CoreServiceList, warning_hint="service"
    )
    if in_enum:
        update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)
        return

    service_arg_invalid = False
    if custom_service_list is not None:
        for custom_services_entry in custom_service_list:
            in_enum, service_value = check_args_in_enum(
                param=service_arg, iterable=custom_services_entry, warning_hint="custom mode"
            )
            if in_enum:
                break
        if not in_enum:
            service_arg_invalid = True
    else:
        service_arg_invalid = True

    if service_arg_invalid:
        LOGGER.warning(f"Passed service argument might be invalid, "
                       f"setting to {CoreServiceList.SERVICE_17}")
        service_value = CoreServiceList.SERVICE_17
    update_global(CoreGlobalIds.CURRENT_SERVICE, service_value)
