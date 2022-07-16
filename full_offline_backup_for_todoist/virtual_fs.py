#!/usr/bin/python3
""" Definitions and implementations of a simple logging / tracing method """
from abc import ABCMeta, abstractmethod
import os.path
import io
import zipfile
from pathlib import Path

class VirtualFs(metaclass=ABCMeta):
    """ An abstract layer over the filesystem
        (e.g. can represent a real folder, a ZIP file, etc.) """

    @abstractmethod
    def set_path_hint(self, dst_path):
        """ Sets the associated physical path of this filesystem (if possible) """

    @abstractmethod
    def existed(self):
        """ Checks if the filesystem previously existed, or is newly created """

    @abstractmethod
    def file_list(self):
        """ Gets the list of files in this virtual file system """

    @abstractmethod
    def read_file(self, file_path):
        """ Reads a file from this virtual file system """

    @abstractmethod
    def write_file(self, file_path, file_data):
        """ Adds a file to the filesystem """

class ZipVirtualFs(VirtualFs):
    """ Represents a virtual filesystem over a ZIP file """
    __ZIP_FLAG_BITS_UTF8 = 0x800

    def __init__(self, src_path):
        self.src_path = src_path
        self.dst_path = src_path
        self._zip_file = None
        self._backing_storage = None

    def __enter__(self):
        if (self.src_path is not None and
                os.path.isfile(self.src_path) and
                zipfile.is_zipfile(self.src_path)):
            self._backing_storage = open(self.src_path, "ab+")
        else:
            self._backing_storage = io.BytesIO()

        self._zip_file = zipfile.ZipFile(self._backing_storage, 'a')

        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self._zip_file.close()

        if not exception_value and isinstance(self._backing_storage, io.BytesIO) and self.dst_path:
            Path(self.dst_path).write_bytes(self._backing_storage.getvalue())
        self._backing_storage.close()

    def set_path_hint(self, dst_path):
        if self.dst_path is None:
            self.dst_path = os.path.join(".", dst_path + ".zip")

    def existed(self):
        return not isinstance(self._backing_storage, io.BytesIO)

    def file_list(self):
        return self._zip_file.namelist()

    def read_file(self, file_path):
        return self._zip_file.read(file_path)

    def write_file(self, file_path, file_data):
        self._zip_file.writestr(file_path, file_data)

        # WORKAROUND FOR A PYTHON BUG in Python's zipfile (at least in Python 3.6.5)
        # There's a bug in the zipfile module, where if a file with a non-ASCII name
        # is first writen to the ZIP, and then immediately read before saving the ZIP,
        # then it will crash with something like:

        # zipfile.BadZipFile: File name in directory '🦋' and header b'\xf0\x9f\xa6\x8b' differ.
        # Sample reproduction:
        #    with zipfile.ZipFile(io.BytesIO(), "a") as zip:
        #    zip.writestr("🦋test", b'010203')
        #    print(zip.read("🦋test"))
        # This happens because the flag_bits specifying whether the filename is UTF-8 or not
        # are set when saving the ZIP, not when creating the in-memory ZipInfo instance,
        # so when reading the file again in-memory, it gets confused and thinks the filename
        # in the ZipInfo is not UTF-8 and tries to decode it with another encoding

        # This isn't really surprising because encoding in zipfile.py is a mess currently...
        # See also: https://bugs.python.org/issue12048 https://bugs.python.org/issue10614

        # As a workaround, we set the in-memory ZipInfo flag when the filename is UTF-8
        try:
            file_path.encode('ascii')
        except UnicodeEncodeError:
            file_info = self._zip_file.getinfo(file_path)
            file_info.flag_bits = file_info.flag_bits | self.__ZIP_FLAG_BITS_UTF8
