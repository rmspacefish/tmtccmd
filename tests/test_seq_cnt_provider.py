import os
from pathlib import Path
from unittest import TestCase

from tmtccmd.pus.seqcnt import FileSeqCountProvider
from tempfile import NamedTemporaryFile


class TestSeqCount(TestCase):
    def setUp(self) -> None:
        self.file_name = Path("seq_cnt.txt")

    def test_basic(self):
        with NamedTemporaryFile("w+t") as file:
            file.write("0\n")
            file.seek(0)
            seq_cnt_provider = FileSeqCountProvider(Path(file.name))
            seq_cnt = seq_cnt_provider.current()
            self.assertEqual(seq_cnt, 0)
            self.assertEqual(next(seq_cnt_provider), 1)
            self.assertEqual(seq_cnt_provider.next_seq_count(), 2)
            file.seek(0)
            file.write(f"{pow(2, 14) - 1}\n")
            file.flush()
            # Assert rollover
            self.assertEqual(next(seq_cnt_provider), 0)

    def test_with_real_file(self):
        seq_cnt_provider = FileSeqCountProvider(self.file_name)
        self.assertTrue(self.file_name.exists())
        self.assertEqual(seq_cnt_provider.current(), 0)
        self.assertEqual(next(seq_cnt_provider), 1)
        pass

    def test_file_deleted_runtime(self):
        seq_cnt_provider = FileSeqCountProvider(self.file_name)
        self.assertTrue(self.file_name.exists())
        os.remove(self.file_name)
        with self.assertRaises(FileNotFoundError):
            next(seq_cnt_provider)
        with self.assertRaises(FileNotFoundError):
            seq_cnt_provider.current()

    def test_faulty_file_entry(self):
        with NamedTemporaryFile("w+t") as file:
            file.write("-1\n")
            file.seek(0)
            seq_cnt_provider = FileSeqCountProvider(Path(file.name))
            with self.assertRaises(ValueError):
                next(seq_cnt_provider)
            file.write(f"{pow(2, 15)}\n")
            file.seek(0)
            file.flush()
            seq_cnt_provider = FileSeqCountProvider(Path(file.name))
            with self.assertRaises(ValueError):
                next(seq_cnt_provider)

    def tearDown(self) -> None:
        if self.file_name.exists():
            os.remove(self.file_name)
