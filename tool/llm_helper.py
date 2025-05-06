from zhipuai import ZhipuAI
from pathlib import Path
import json, os


def basic_talk(user_input:str):
    print(f"zhipu question {user_input}")
    print(user_input)
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    system_prompt = "you are a helpful assistant"
    response = client.chat.completions.create(
        model="glm-4-flash",  
        messages=[
            {"role": "system", "content": f"{system_prompt}"},
            {"role": "user", "content": user_input},
        ],
    )
    print(f"zhipu answer {response.choices[0].message}")
    return response.choices[0].message.content