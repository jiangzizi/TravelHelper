from zhipuai import ZhipuAI
import json

def should_search(message_list):
    """判断是否需要搜索"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    
    # 系统提示，明确告诉模型只需要回答是否需要搜索
    system_prompt = {
        "role": "system",
        "content": """Decide whether you need to call web search function to answer user's query. Only output 'YES' or 'NO'.
        Output 'YES' if use ask for weather.
        """
    }

    # 构建消息列表
    messages = [system_prompt] + [message_list[-1]]
    print(f"should search {messages}")
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages,
        max_tokens=10
    )
    
    decision = response.choices[0].message.content.strip().upper()
    print(f"search decision {decision}")
    return decision == "YES"

import requests

def perform_search(query):
    api_key = "AIzaSyBCnrHC_z71C_0tgHNzFEuZrdeL27md5CI"
    cx = "017576662512468239146:omuauf_lfve"
    search_url = f"https://www.google.com/search?q={query}"
    
    try:
        response = requests.get(search_url)
        print(response)
        response.raise_for_status()  # 如果响应失败会抛出异常
        print(response.json())
        #return response.json()  # 返回 dict 对象
    except requests.RequestException as e:
        print(f"error {str(e)}")
        #return {"error": str(e)}
    print("this is a demo research answer")

def generate_final_response(message_list, search_results=None):
    """生成最终回复"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    
    system_prompt = {
        "role": "system",
        "content": "Your are a helpful assistant."
    }
    
    # 如果有搜索结果，添加到消息中
    messages = [system_prompt]
    if search_results:
        messages.append({
            "role": "system",
            "content": f"Here is the web search content \n{search_results}\n"
        })
    
    # 添加历史消息和最新问题
    messages.extend(message_list)
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages
    )
    
    return response.choices[0].message.content

def smart_talk(message_list, basic = True):
    """智能对话流程，包含搜索判断"""
    # 获取最新用户问题（假设是最后一条用户消息）
    latest_user_message = next((msg for msg in reversed(message_list) if msg["role"] == "user"), None)

    if not latest_user_message:
        return "请提出您的问题。"
    
    user_query = latest_user_message["content"]
    if basic :
        return generate_final_response(message_list)
    # 第一步：判断是否需要搜索
    if should_search(message_list):
        # 第二步：如果需要搜索，执行搜索
        search_results = perform_search(user_query)
        # 第三步：结合搜索结果生成最终回复
        return generate_final_response(message_list, search_results)
    else:
        # 如果不需要搜索，直接生成回复
        return generate_final_response(message_list)

# 使用示例
if __name__ == "__main__":
    conversation_history = [
        {"role": "user", "content": "How is the weather in beijing"}
    ]
    
    response = smart_talk(conversation_history)
    print(response)
