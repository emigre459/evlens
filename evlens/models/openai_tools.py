from typing import List, Union
from openai import OpenAI


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