import webuiapi
from PIL import Image
import os
import util
import json

class TaggerInterrogate:
  def __init__(self, baseurl: str):
    self.api_ = webuiapi.WebUIApi(baseurl=baseurl)
    self.caption_ = None
    self.high_confidence_ = 0.85
    self.low_confidence_ = 0.6
    #self.gender_candidate_ = ['girls', 'girl', 'woman', 'women', 'boys', 'boy',  'man', 'men']
    self.gender_candidate_ = ['girls', 'girl', 'boys', 'boy']

    file_path = os.path.join(util.get_py_file_dir(), 'filter-conf/animals.txt')
    with open(file_path, 'r', encoding='utf-8') as file:
        self.animals = json.load(file)['animal']

  def interrogate(self, image: Image):
    result = self.api_.interrogate(image, "wd14-vit-v2-git")
    exclude = ['general', 'sensitive', 'questionable', 'explicit']
    self.caption_ = {key: value for key, value in result.info.items() if key not in exclude}

  def get_gender(self, filter_name:str = "")->list:
    result = list()
    for key, value in self.caption_.items():
      if value < self.low_confidence_:
        continue
      for i in range(len(self.gender_candidate_)):
        if self.gender_candidate_[i] in key:
          # 特殊处理 murano_glass滤镜 female和male效果最好
          if filter_name == "murano_glass":
            if i < 4:
              result.append("female")
            else:
              result.append("male")
          else:
            result.append(key)
      
    return result

  # 获取动物种类
  def get_animal(self)->list:
    result = list()
    for key, value in self.caption_.items():
      if value < self.low_confidence_:
        continue
      for i in range(len(self.animals)):
        if self.animals[i] == key:
            result.append(key)
      
    return result

  # get_animal有可能不能获取到动物的类别，但通过no_humans和animal_focus可以判断出是动物
  # 能判断出动物，对出图也是非常有帮助的
  def is_animal(self)->bool:
    return self.has_tag('no_humans') and self.has_tag('animal_focus')
  
  def get_high_confidence_tags(self)->list:
    result = []
    for key, value in self.caption_.items():
      if value < self.high_confidence_:
        continue
      # 剔除性别
      for i in range(len(self.gender_candidate_)):
        if self.gender_candidate_[i] in key:
          break
      else:
        # 剔除动物
        for i in range(len(self.animals)):
          if self.animals[i] in key:
            break
        else:
          result.append(key)
    return result


  def get_tags(self, input_tags:list)->list:
    result = []
    for key, value in self.caption_.items():
      if value < self.low_confidence_:
        continue
      for input_tag in input_tags:
        if input_tag in key:
          result.append(key)
    return result


  def has_tag(self, tag: str)->bool:
    for key in self.caption_.keys():
      if tag in key and self.caption_[key] >= self.low_confidence_:
        return True
    return False

#image = Image.open('E:/ai/test-images/2.png')
#tagger_interrogate = TaggerInterrogate('http://sunyingshi-sd-webui-test.2345test.cn/tagger/v1')
#tagger_interrogate.interrogate(image)
#print(tagger_interrogate.has_tag("hair")) 
#print(tagger_interrogate.get_high_confidence_tags())
