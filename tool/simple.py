from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from zhipuai import ZhipuAI
import re

def keep_after_last_function_tag(s):
    match = re.search(r'</function>(.*)$', s, re.DOTALL)
    return match.group(1) if match else s


def generate_final_response_stream(message_list, search_results=None):
    """流式生成最终回复"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    print(f"search result for final generation is  {search_results}")
    search_results = keep_after_last_function_tag(search_results) if search_results else None

    system_prompt = {
        "role": "system",
        "content": "Your are a helpful travel assistant. You can only answer travel related questions."
    }

    messages = [system_prompt]
    messages.extend(message_list)
    if search_results:
        messages[-1]["content"] += f"\nAnswer my question based on below information.\n\nHere is the web search content:\n{search_results}\n"

    print(f"messages for final generation {messages}")

    # 返回生成器，yield 每一段内容
    def stream_content():
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return stream_content()


def smart_talk_stream(message_list, basic=True):
    """流式智能对话流程"""
    latest_user_message = next((msg for msg in reversed(message_list) if msg["role"] == "user"), None)

    if not latest_user_message:
        yield "请提出您的问题。"
        return

    if basic:
        for token in generate_final_response_stream(message_list):
            yield token

@csrf_exempt
def llm_talk_testing(request):
    def event_stream():
        yield 'data: {"llm_content": "'
        for token in smart_talk_stream([{"role":"user", "content": "generate a pretty long essay about climate change"}], basic=True):
            # 注意处理特殊字符，防止 JSON 错误
            yield token.replace('\n', '\\n').replace('"', '\\"')
        yield '"}\n\n'

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

