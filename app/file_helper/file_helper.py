import os
import sys

def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def get_schema_path():
    return os.path.join(get_app_path(), "schema")

def get_dnet_schema_path():
    return os.path.join(get_schema_path(), "dnet")

def get_i7565dnm_dll_path():
    return os.path.join(get_app_path(), "x64", "I7565DNM.dll")