from praisonaiagents import Agent, Agents, MCP
import os

def deepsearcher():

    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    os.environ["DUFFEL_API_KEY_LIVE"] = "duffel_test_Li5UOd_hOzpiAwxv3GLp4lQ23Y8bkaXo86R216FMgD-"
    os.environ["GOOGLE_MAPS_API_KEY"] = "AIzaSyD8kz0EW1KKo8B3I8GU7nAy19R8S6X6RVE"
    maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyD8kz0EW1KKo8B3I8GU7nAy19R8S6X6RVE")

    # Travel Research Agent
    """research_agent = Agent(
        instructions="Research about travel destinations, attractions, local customs, and travel requirements",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )"""

    # Flight Booking Agent
    flight_agent = Agent(
        instructions="""You are a helpful assistant that can interact with Google Maps.
    Use the available tools when relevant to handle location-based queries.""",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-google-maps",
            env={"GOOGLE_MAPS_API_KEY": maps_api_key})
    )

    """# Accommodation Agent
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
    )"""

    # Example usage - research travel destinations
    destination = "London, UK"
    dates = "August 15-22, 2025"
    budget = "Mid-range (£1000-£1500)"
    preferences = "Historical sites, local cuisine, avoiding crowded tourist traps"
    travel_query = f"What are the best attractions to visit in {destination} during {dates} on a budget of {budget} with preferences of {preferences}?"
    travel_query = "Find nearby restaurants in London"
    agents = Agents(agents=[
        # research_agent, 
        flight_agent, 
        # hotel_agent, 
                            # planning_agent
                            ])

    result, tool_call_result = agents.start(travel_query, return_dict = True)
    print(f"\n=== DESTINATION RESEARCH: {destination} ===\n")
    print(result)
    print("\n=== TOOL CALL RESULT ===\n")
    print(tool_call_result)

if __name__ == "__main__":

    deepsearcher()