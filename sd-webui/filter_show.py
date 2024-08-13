import gradio as gr
import numpy as np
import setproctitle
import generate_image_util
from sd_webui_service import SDWebUIService

# 设置进程名称
setproctitle.setproctitle('filter-show')

enable_lcm_arg = False
styles_dict = generate_image_util.get_styles()
STYLE_NAMES = styles_dict.keys()
DEFAULT_STYLE_NAME = list(styles_dict.keys())[0]
MAX_SEED = np.iinfo(np.int32).max


def remove_tips():
    return gr.update(visible=False)

def randomize_seed_fn(seed: int, randomize_seed: bool) -> int:
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    return seed

def generate_image(
    face_image_path,
    style_name,
    progress=gr.Progress(track_tqdm=True),
):
    style_json = generate_image_util.get_style_json(styles_dict[style_name])
    style_json['input_image'] = face_image_path
    service = SDWebUIService(style_json, 'localhost', port=7860)
    return service.generate_image().image


# Description
title = r"""
<h1 align="center">v1.1-filter-demo</h1>
"""

description = r"""如过滤镜有问题，请及时联系【孙迎世】"""


tips = r"""
### Usage tips of InstantID
1. If you're not satisfied with the similarity, try increasing the weight of "IdentityNet Strength" and "Adapter Strength."    
2. If you feel that the saturation is too high, first decrease the Adapter strength. If it remains too high, then decrease the IdentityNet strength.
3. If you find that text control is not as expected, decrease Adapter strength.
4. If you find that realistic style is not good enough, go for our Github repo and use a more realistic base model.
"""

css = """
.gradio-container {width: 85% !important}
"""
with gr.Blocks(css=css) as demo:
    # description
    gr.Markdown(title)
    gr.Markdown(description)

    with gr.Row():
        with gr.Column():
            with gr.Row(equal_height=True):
                # upload face image
                face_file = gr.Image(
                    label="Upload a photo of your image", type="filepath"
                )


            submit = gr.Button("Submit", variant="primary")
            style = gr.Dropdown(
                label="Style template",
                choices=STYLE_NAMES,
                value=DEFAULT_STYLE_NAME,
            )

        with gr.Column(scale=1):
            gallery = gr.Image(label="Generated Images")

        submit.click(
            fn=generate_image,
            inputs=[
                face_file,
                style
            ],
            outputs=[gallery],
        )


demo.queue(api_open=False)
demo.launch(server_name="0.0.0.0", server_port=7861)