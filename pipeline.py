from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain
from rich import print

def run_research_pipeline(topic : str) -> str:
    state ={}

    # Search Agent Working
    print("\n"+"="*50)
    print("Step 1:Search Agent is working...")
    print("="*50)

    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages" : [("user", f"Find recent, reliable and detailed information on the topic: {topic}.")]
    })
    state["search_results"] = search_result['messages'][-1].content
    print("\n Search Results: \n", state["search_results"])

    # Reader Agent Working
    print("\n"+"="*50)
    print("Step 2:Reader Agent is scrapping top resources...")
    print("="*50)

    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{state['search_results'][:800]}"
        )]
    })
    state["scraped_content"] = reader_result['messages'][-1].content
    print("\n Scraped Content: \n", state["scraped_content"][:800])

    # Writer Chain Working
    print("\n"+"="*50)
    print("Step 3:Writer Chain is drafting a research report...")
    print("="*50)

    research_combined = (
        f"Search Results:\n{state['search_results']}\n\n"
        f"Detailed Scraped Content:\n{state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })

    print("\n Final Report\n",state['report'])

    # Critic Chain Working
    print("\n"+"="*50)
    print("Step 4:Critic Chain is reviewing the report...")
    print("="*50)

    state["feedback"] = critic_chain.invoke({
        "report": state['report']
    })

    print("\n Critic Feedback\n",state['feedback'])

    return state


# to call pipeline.py with a topic, you can use the following code:
if __name__ == "__main__":
    topic = input("Enter a research topic: ")
    run_research_pipeline(topic)