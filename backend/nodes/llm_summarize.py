# TODO: call the Claude API (ANTHROPIC_API_KEY) with state["videos"] analysis
# results + state["product"] to summarize which content factors suit this
# product. Wire up the real anthropic.Anthropic() client here once the prompt
# is designed.
def run(state: dict) -> dict:
    content_factors = {
        "factors": ["TODO: derive from LLM analysis of videos + product"],
        "mock": True,
    }
    return {"content_factors": content_factors}
