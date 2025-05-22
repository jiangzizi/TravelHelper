from praisonaiagents import Agent, Agents, MCP
import os

brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0" #     os.getenv("BRAVE_API_KEY")
os.environ["BRAVE_API_KEY"] = brave_api_key
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")

brave_api_key = os.getenv("BRAVE_API_KEY")

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

# General Search Agent
general_search_agent = Agent(
    instructions="Perform general web searches to gather information",
    llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
)
agents = Agents(agents=[general_search_agent])
def general_query(query):
    """Function to handle travel-related queries"""
    # Here you can implement the logic to process the query
    # For example, you can call the agents to get information
    # and return the results.
    result = agents.start(query)
    return result


if __name__ == "__main__":
    # Example usage - research travel destinations
    destination = "London, UK"
    dates = "August 15-22, 2025"
    budget = "Mid-range (£1000-£1500)"
    preferences = "Historical sites, local cuisine, avoiding crowded tourist traps"
    travel_query = f"What are the best attractions to visit in {destination} during {dates} on a budget of {budget} with preferences of {preferences}?"
    agents = Agents(agents=[research_agent, flight_agent, hotel_agent, planning_agent])

    result = agents.start(travel_query)
    print(f"\n=== DESTINATION RESEARCH: {destination} ===\n")
    print(result)

    result = agents.start(travel_query+ "tell me why")
    print(f"\n=== DESTINATION RESEARCH: {destination} ===\n")
    print(result)
