from zhipuai import ZhipuAI
import json
from praisonaiagents import Agent, Agents, MCP
import os

brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0" #     os.getenv("BRAVE_API_KEY")
os.environ["BRAVE_API_KEY"] = brave_api_key
os.environ["GROQ_API_KEY"] = "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"
# General Search Agent
general_search_agent = Agent(
    instructions="Perform general web searches to gather information",
    llm="groq/llama-3.1-8b-instant",
    tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
)

def general_query(query):
    """Function to handle travel-related queries"""
    # Here you can implement the logic to process the query
    # For example, you can call the agents to get information
    # and return the results.
    agents = Agents(agents=[general_search_agent])
    result = agents.start(query)
    return result


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

def perform_search(query):
    print(f"perform search {query}")
    """执行搜索"""
    answer = general_query(query)
    print(f"search result {answer}")
    return answer

import re

def keep_after_last_function_tag(s):
    match = re.search(r'</function>(.*)$', s, re.DOTALL)
    return match.group(1) if match else ''

def generate_final_response(message_list, search_results=None):
    """生成最终回复"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    search_results = keep_after_last_function_tag(search_results) if search_results else None
    print(f"search result for final generation is  {search_results}")
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
    response = smart_talk(conversation_history, basic=False)
    print(response)
