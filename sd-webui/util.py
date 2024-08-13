import os
def get_py_file_dir():
  script_path = os.path.abspath(__file__)
  return os.path.dirname(script_path)