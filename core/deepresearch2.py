from praisonaiagents import Agent, Agents, MCP
import os
os.environ["DUFFEL_API_KEY_LIVE"] = "duffel_test_Li5UOd_hOzpiAwxv3GLp4lQ23Y8bkaXo86R216FMgD-"
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
agent = Agent(
    instructions="""You are a helpful assistant that can check stock prices and perform other tasks.
    Use the available tools when relevant to answer user questions.""",
    llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    tools = MCP("python3 /Users/zhizhi/Desktop/code/25sp/SOA/aws/check/app.py")
)

# NOTE: Replace with your actual Python path and app.py file path

agent.start("What is the stock price of Tesla?")
