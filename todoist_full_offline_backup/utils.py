#!/usr/bin/python3
""" Simple standalone utility methods """
import re

def sanitize_file_name(filename):
    """ Sanitizes a file name, removing characters that may cause problems on some platforms """
    return re.sub(r'[^a-zA-Z0-9_.\- ]', "_", filename)
