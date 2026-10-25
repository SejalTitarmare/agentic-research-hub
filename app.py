import json

from flask import Flask, Response, request, send_from_directory

from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

app = Flask(__name__, static_folder="static", static_url_path="")


def to_text(content) -> str:
    """Agent/chain outputs can be a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            c.get("text", "") if isinstance(c, dict) else str(c) for c in content
        )
    return str(content)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def research_stream(topic: str):
    """Same four steps as pipeline.py, but yields an event after each one."""
    step = 1
    try:
        # Step 1: Search agent
        yield sse("step", {"step": 1, "status": "running"})
        search_agent = build_search_agent()
        search_result = search_agent.invoke({
            "messages": [("user", f"Find recent, reliable and detailed information on the topic: {topic}.")]
        })
        search_results = to_text(search_result["messages"][-1].content)
        yield sse("result", {"step": 1, "key": "search_results", "content": search_results})

        # Step 2: Reader agent
        step = 2
        yield sse("step", {"step": 2, "status": "running"})
        reader_agent = build_reader_agent()
        reader_result = reader_agent.invoke({
            "messages": [("user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search Results:\n{search_results[:800]}"
            )]
        })
        scraped = to_text(reader_result["messages"][-1].content)
        yield sse("result", {"step": 2, "key": "scraped_content", "content": scraped})

        # Step 3: Writer chain
        step = 3
        yield sse("step", {"step": 3, "status": "running"})
        research_combined = (
            f"Search Results:\n{search_results}\n\n"
            f"Detailed Scraped Content:\n{scraped}"
        )
        report = to_text(writer_chain.invoke({"topic": topic, "research": research_combined}))
        yield sse("result", {"step": 3, "key": "report", "content": report})

        # Step 4: Critic chain
        step = 4
        yield sse("step", {"step": 4, "status": "running"})
        feedback = to_text(critic_chain.invoke({"report": report}))
        yield sse("result", {"step": 4, "key": "feedback", "content": feedback})

        yield sse("done", {})
    except Exception as e:
        # "failure" (not "error") so it doesn't clash with EventSource's built-in error event
        yield sse("failure", {"step": step, "message": str(e)})


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/research")
def research():
    topic = request.args.get("topic", "").strip()
    if not topic:
        return {"error": "Topic is required"}, 400
    return Response(
        research_stream(topic),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    # debug=False: the auto-reloader would import the heavy LangChain stack twice
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)