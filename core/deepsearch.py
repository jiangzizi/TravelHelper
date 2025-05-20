from mypraisonaiagents import Agent, Agents, MCP
import os

def deepsearch():

    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key
    # Ensure GROQ_API_KEY is set if your Agent/MCP depends on it internally
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")


    # Travel Research Agent
    research_agent = Agent(
        instructions="Research about travel destinations, attractions, local customs, and travel requirements",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Flight Booking Agent
    flight_agent = Agent(
        instructions="Search for available flights, compare prices, and recommend optimal flight choices",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Accommodation Agent
    hotel_agent = Agent(
        instructions="Research hotels and accommodation based on budget and preferences",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Itinerary Planning Agent
    planning_agent = Agent(
        instructions="Design detailed day-by-day travel plans incorporating activities, transport, and rest time",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Example usage - research travel destinations
    destination = "London, UK"
    dates = "August 15-22, 2025"
    budget = "Mid-range (£1000-£1500)"
    preferences = "Historical sites, local cuisine, avoiding crowded tourist traps"
    travel_query = f"What are the best attractions to visit in {destination} during {dates} on a budget of {budget} with preferences of {preferences}?"
    agents = Agents(agents=[research_agent, flight_agent, hotel_agent, 
                            planning_agent
                            ])

    result, tool_call_result = agents.start(travel_query, return_dict = True)
    print(f"\n=== DESTINATION RESEARCH: {destination} ===\n")
    print(result)
    print("\n=== TOOL CALL RESULT ===\n")
    print(tool_call_result)

if __name__ == "__main__":

    deepsearch()