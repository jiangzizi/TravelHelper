from zhipuai import ZhipuAI
from pathlib import Path
import json, os

def basic_talk(message_list):
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    system_prompt = {"role": "system", "content": "you are a helpful assistant"}
    messages = [system_prompt] + message_list

    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages
    )

    return response.choices[0].message.content