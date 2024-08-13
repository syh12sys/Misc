from sd_webui_service import SDWebUIService
import util
import json
import os


file_path = os.path.join(util.get_py_file_dir(), 'filter-conf/woolen.json')
with open(file_path, 'r', encoding='utf-8') as file:
    data = file.read()

def get_style_content(style_path: str)->str:
  with open(style_path, 'r', encoding='utf-8') as file:
    return file.read()

def get_style_json(style_path: str)->json:
  with open(style_path, 'r', encoding='utf-8') as file:
    return json.load(file)

def get_styles()->dict:
  result = dict()
  style_dir = os.path.join(util.get_py_file_dir(), 'filter-conf')
  files = os.listdir(style_dir)
  for filename in files:
    file_path = os.path.join(style_dir, filename)
    if os.path.isfile(file_path) and filename.endswith('.json'):
        with open(file_path, 'r', encoding='utf-8') as file:
           data = json.load(file)
           key = data['description'] + ' (' + data['checkpoint']  + ')'
           result[key] = file_path
  return result

if __name__ == '__main__':
  sd_webui_service = SDWebUIService(str(data), 'sunyingshi-sd-webui-test.2345test.cn')
  sd_webui_service.generate_image().image.save('result.png')