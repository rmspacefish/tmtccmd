from typing import Dict


INVALID_ID = bytes([0xff, 0xff, 0xff, 0xff])


def get_core_object_ids() -> Dict[bytes, list]:
    """
    These are the object IDs for the tmtccmd core. The core will usually take care of
    inserting these into the object manager during the program initialization.
    :return: Dictionary of the core object IDs
    """
    object_id_dict = {
        INVALID_ID: ["Invalid ID"],
    }
    return object_id_dict
