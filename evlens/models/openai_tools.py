from typing import List, Union, Tuple
from math import ceil
from openai import OpenAI
from PIL import Image
import io
import requests


def find_models(
    name: str
) -> Union[List[str], None]:

    client = OpenAI()
    models = client.models.list().model_dump()['data']

    models_found = []
    for e in models:
        m = e['id']
        if name in m:
            models_found.append(m)

    if len(models_found) == 0:
        return None
    else:
        return models_found
    

# From https://stackoverflow.com/a/44481279/8630238
def url_to_image(url: str) -> Image:
    data = requests.get(url).content
    return Image.open(io.BytesIO(data))


# Adapted from https://community.openai.com/t/how-do-i-calculate-image-tokens-in-gpt4-vision/492318/2
def count_image_tokens(
    dimensions: Tuple[int, int] = None,
    img: Image = None,
    url: str = None,
    high_resolution: bool = True
) -> int:
    
    if dimensions is not None:
        height, width = dimensions
    elif img is not None:
        height = img.height
        width = img.width
    elif url is not None:
        img = url_to_image(url)
        height = img.height
        width = img.width
    else:
        raise ValueError("One of `dimensions`, `object`, or `url` must be "
                         "provided")
    
    if high_resolution:
        h = ceil(height / 512)
        w = ceil(width / 512)
        n = w * h
        total = 85 + 170 * n
        return total
    
    else:
        return 85 # default tokens for low-res
    
    
def ask_simple_vision_question(
    question: str,
    img_url: str
) -> str:
    
    client = OpenAI()
    
    response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
        "role": "user",
        "content": [
            {"type": "text", "text": question},
            {
            "type": "image_url",
            "image_url": {
                "url": img_url,
            },
            },
        ],
        }
    ],
    max_tokens=300,
    )

    return response.choices[0].message.content
    