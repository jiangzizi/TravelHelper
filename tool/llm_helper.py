from zhipuai import ZhipuAI
from pathlib import Path
import json
import os


def basic_talk(message_list):
    system_prompt = {"role": "system",
                     "content": "you are a helpful assistant"}
    messages = [system_prompt] + message_list

    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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",
    )

    completion = client.chat.completions.create(
        extra_headers={
            # Optional. Site URL for rankings on openrouter.ai.
            "HTTP-Referer": "<YOUR_SITE_URL>",
            # Optional. Site title for rankings on openrouter.ai.
            "X-Title": "<YOUR_SITE_NAME>",
        },
        extra_body={},
        model="deepseek/deepseek-chat-v3-0324:free",
        messages= messages
    )
    print(completion.choices[0].message.content)

    return completion.choices[0].message.content
