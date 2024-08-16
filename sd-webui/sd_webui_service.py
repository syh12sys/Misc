import webuiapi
from tagger_interrogate import TaggerInterrogate
import json
from PIL import Image

clay_style_str = """
{
"type":"img2img",
"input_image":"E:/ai/2.jpg",
"checkpoint":"juggernautXL_version5.safetensors",
"vae":"None",
"prompt": "claymation, clay, best quality, masterpiece, {prompt}, clay_hair <lora:CLAYMATE_V2.03_:0.6>",
"negative_prompt":"painting",
"sampler_name":"Euler a",
"scheduler":"Karras",
"steps":25,
"denoising_strength":0.5,
"cfg_scale":7,
"width":536,
"height":960,
"upscale":"R-ESRGAN 4x+ Anime6B",
"controlnet":[
  {
    "module":"instant_id_face_embedding",
    "model":"ip-adapter_instant_id_sdx",
    "weight":0.5,
    "pixel_perfect":true
  },
  {
    "module":"instant_id_face_keypoints",
    "model":"control_instant_id_sdxl",
    "weight":0.5,
    "pixel_perfect":true
  },
  {
    "module":"dw_openpose_full",
    "model":"thibaud_xl_openpose",
    "weight":0.3,
    "pixel_perfect":true
  }
]
}
"""

class SDWebUIService:
  def __init__(self, filter_conf : any, host: str, port:int = 80):
    self.api_ = webuiapi.WebUIApi(host, port=port)
    self.tagger_interrogate_ = TaggerInterrogate('http://' + host + ":" + str(port)  + "/tagger/v1")
    
    if isinstance(filter_conf, str):
      self.filter_conf_ = json.loads(filter_conf)
    else:
      self.filter_conf_ = filter_conf
    self.control_net_key_ = 'controlnet'

    # 切换基模、vae
    options = {}
    if "checkpoint" in self.filter_conf_:
      options['sd_model_checkpoint'] = self.filter_conf_["checkpoint"]
    if "vae" in self.filter_conf_:
      options["sd_vae"] = self.filter_conf_["vae"]
    self.api_.set_options(options)

    image = Image.open(self.filter_conf_['input_image'])
    self.origin_input_image_size_ = image.size
    self.input_image_ = image
    # 图片剪切成适合大模型的尺寸
    self.input_image_ = self.crop_image_for_base_model(image)
    #self.input_image_.save("crop.jpg")

  def is_sdxl(self):
    return "XL" in self.filter_conf_['checkpoint']

  def crop_image_for_base_model(self, image : Image):
    dest_crop_value = None
    # 如果已经指定尺寸，那么就不再智能选择
    if "width" in self.filter_conf_ and "height" in self.filter_conf_:
        dest_crop_value = (self.filter_conf_["width"], self.filter_conf_["height"])
    else:
      # 智能选择缩放尺寸
      candidate_crop_scales = {}
      if image.width > image.height:
        for i in range(1024, 511, -64):
          candidate_crop_scales[1024 / i] = (1024, i)
      else:
        for i in range(1024, 511, -64):
          candidate_crop_scales[i / 1024] = (i, 1024)
      # 获取最相近的缩放比例
      origin_scale = image.width / image.height
      min_difference = float('inf')

      for key, value in candidate_crop_scales.items():
        if abs(key - origin_scale) < min_difference:
          min_difference = abs(key - origin_scale)
          dest_crop_value = value
      print('auto choose crop size=' + str(dest_crop_value))
    # 已经是最合适的尺寸，那么就不再裁剪
    if dest_crop_value == image.size:
      return image

    result = self.api_.extra_single_image(image, 
                                         resize_mode=1, 
                                         upscaling_resize_w=dest_crop_value[0],
                                         upscaling_resize_h=dest_crop_value[1],  
                                         upscaler_1="Nearest")
    return result.image
  
  def upscale_and_crop_for_output(self, image: Image):
    result = self.api_.extra_single_image(image,
                                         resize_mode=0, 
                                         upscaling_resize=1,
                                         upscaler_1=self.filter_conf_["upscale"])
    result.image.save("upscale.png")
    crop_size = self.origin_input_image_size_

    result = self.api_.extra_single_image(result.image, 
                                    resize_mode=0, 
                                    upscaling_resize_w=crop_size[0],
                                    upscaling_resize_h=crop_size[1],  
                                    upscaler_1="Nearest")
    return result.image


  def build_control_net(self, control_nets: list):
    # lineart + depth 作为兜底
    if self.control_net_key_ == 'other':
      # lineart
      if self.is_sdxl():
        model = 'bdsqlsz_controlllite_xl_lineart_anime_denoise'
      else:
        model = 'control_v11p_sd15s2_lineart_anime'
      lineart_controlnet = webuiapi.ControlNetUnit(image=self.input_image_, 
                                            module='lineart_standard (from white bg & black line)', 
                                            model=model, 
                                            weight=0.5, 
                                            pixel_perfect=True)

      # depth
      if self.is_sdxl():
        model = 'bdsqlsz_controlllite_xl_depth_V2'
      else:
        model = 'control_v11f1p_sd15_depth'
      depth_controlnet = webuiapi.ControlNetUnit(image=self.input_image_, 
                                            module='depth_anything_v2', 
                                            model=model, 
                                            weight=0.5, 
                                            pixel_perfect=True)

      return [lineart_controlnet, depth_controlnet]


    results = []
    for param in control_nets:
      threshold_a = 64
      if 'down_sampling_rate' in param:
        threshold_a = param['down_sampling_rate']
      control_mode = 0
      if 'control_mode' in param:
        control_mode = param['control_mode']
      low_vram = False
      if 'low_vram' in param:
        low_vram = True
      control_net = webuiapi.ControlNetUnit(image=self.input_image_, 
                                            module=param['module'], 
                                            model=param['model'], 
                                            weight=param['weight'],
                                            threshold_a = threshold_a,
                                            pixel_perfect=param['pixel_perfect'],
                                            control_mode = control_mode,
                                            low_vram = low_vram)
      results.append(control_net)
    return results

  def img2img(self):
    result = self.api_.img2img(prompt=self.filter_conf_['prompt'],
                negative_prompt=self.filter_conf_['negative_prompt'],
                images=[self.input_image_], 
                width=self.input_image_.width,
                height=self.input_image_.height,
                controlnet_units=self.build_control_net(self.filter_conf_['controlnet']),
                sampler_name=self.filter_conf_['sampler_name'],
                scheduler=self.filter_conf_['scheduler'],
                steps=self.filter_conf_['steps'],
                denoising_strength=self.filter_conf_['denoising_strength'],
                cfg_scale=self.filter_conf_["cfg_scale"],
              )
    return result

  def txt2img(self):
    result = self.api_.txt2img(prompt=self.filter_conf_['prompt'],
                          negative_prompt=self.filter_conf_['negative_prompt'],
                          sampler_name=self.filter_conf_['sampler_name'],
                          scheduler=self.filter_conf_['scheduler'],
                          steps=self.filter_conf_["steps"],
                          cfg_scale=self.filter_conf_["cfg_scale"],
                          width=self.input_image_.width,
                          height=self.input_image_.height,
                          controlnet_units=self.build_control_net(self.filter_conf_['controlnet']),
                        )
    return result
  
  def process_prompt(self):
    prompt_replacement_keys = ['{role}', '{prompt}']
    for i in range(len(prompt_replacement_keys)):
      if prompt_replacement_keys[i] in self.filter_conf_['prompt']:
        break
    else:
      return
    
    # 提示词反推
    self.tagger_interrogate_.interrogate(self.input_image_)

    # 性别处理
    if prompt_replacement_keys[0] in self.filter_conf_['prompt']:
      role_str = ''
      role = self.tagger_interrogate_.get_gender(self.filter_conf_['name'])
      if len(role) == 0:
        # 如果没有人，就找动物，就走入兜底流程
        self.control_net_key_ = 'other'
        role = self.tagger_interrogate_.get_animal()
      if len(role) > 0:
         role_str = role[0]
      elif self.tagger_interrogate_.is_animal:
        role_str = 'animal'
        
      prompt = self.filter_conf_['prompt']
      self.filter_conf_['prompt'] = prompt.replace(prompt_replacement_keys[0], role_str)

    # 高置信提示词
    if prompt_replacement_keys[1] in self.filter_conf_['prompt']:
      # 提取高置信率的tag放到prompt中
      high_confidence_tags = ','.join(self.tagger_interrogate_.get_high_confidence_tags())
      # 置信率及格但不高，但是影响比较大的词
      optional_tags = ["looking_at_viewer"]
      for iter in optional_tags:
        if self.tagger_interrogate_.has_tag(iter):
          high_confidence_tags += ',' + iter
      # 肤色特别处理，如果是黑人，那么不能把它变白，这是个很敏感的种族问题
      if self.tagger_interrogate_.is_black_person():
        high_confidence_tags += ',(dark_skin:1.2)'

      prompt = self.filter_conf_['prompt']
      self.filter_conf_['prompt'] = prompt.replace(prompt_replacement_keys[1], high_confidence_tags)

  def generate_image(self):
    self.control_net_key_ = 'controlnet'
    self.process_prompt()
    print('prompt=' + self.filter_conf_['prompt'])
    print('negative_prompt=' + self.filter_conf_['negative_prompt'])
    if self.filter_conf_['type'] == "img2img":
      return self.img2img()
    else:
      return self.txt2img()


#sdwebui_service = SDWebUIService(clay_style_str, 'sunyingshi-sd-webui-test.2345test.cn')
#sdwebui_service.generate_image().image.save('result.png')