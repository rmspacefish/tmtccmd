import struct
from typing import Dict

from tmtccmd.utility.tmtcc_logger import get_logger

LOGGER = get_logger()


class ObjectIdManager:
    """
    Global object manager. This is a singleton class, only one global instance should be created.
    The instance can be retrieved with the get_manager class method.
    """
    MANAGER_INSTANCE = None

    @classmethod
    def get_manager(cls):
        """
        Retrieve a handle to the global object ID manager.
        """
        if cls.MANAGER_INSTANCE is None:
            cls.MANAGER_INSTANCE = ObjectIdManager()
        return cls.MANAGER_INSTANCE

    def __init__(self):
        self.object_id_dict = dict()

    # noinspection PyUnresolvedReferences
    def get_object_id_info(self, object_id: bytearray):
        object_id = self.object_id_dict.get(bytes(object_id))
        if object_id is None:
            try:
                LOGGER.error("This key does not exist in the object ID dictionary!")
            except ImportError:
                print("Could not import LOGGER!")
            return bytearray(4)
        else:
            return object_id

    def get_object_id_info_from_int_id(self, object_id: int):
        object_id_bytearray = struct.pack('!I', object_id)
        return self.get_object_id_info(object_id=bytearray(object_id_bytearray))

    def insert_object_id(self, object_id: bytearray, object_id_info: list):
        self.object_id_dict.update({bytes(object_id): object_id_info})

    def insert_object_ids(self, object_id_dict: Dict[bytes, list]):
        self.object_id_dict.update(object_id_dict)


def insert_object_id(object_id: bytearray, object_id_info: list):
    return ObjectIdManager.get_manager().insert_object_id(
        object_id=object_id, object_id_info=object_id_info
    )


def insert_object_ids(object_id_dict: Dict[bytes, list]):
    if object_id_dict is not None:
        return ObjectIdManager.get_manager().insert_object_ids(object_id_dict=object_id_dict)


def get_object_id_info(object_id: bytearray):
    return ObjectIdManager.get_manager().get_object_id_info(object_id=object_id)
