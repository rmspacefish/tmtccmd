from unittest import TestCase
from tmtccmd.core.object_id_manager import insert_object_id, get_object_id_info

TEST_ID_0 = bytearray([0x00, 0x01, 0x02, 0x03])


class TestObjIdManager(TestCase):

    def test_obj_id_manager(self):
        insert_object_id(object_id=TEST_ID_0, object_id_info=["TEST_ID_0"])
        info_list = get_object_id_info(object_id=TEST_ID_0)
        self.assertTrue(info_list[0] == "TEST_ID_0")
