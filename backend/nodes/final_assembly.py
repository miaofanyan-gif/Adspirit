# The graph interrupts before this node (see graph.py) so the user can
# manually review/edit the generated clips in state["clips"] before the task
# is marked complete. This node just records that the human confirmed.
def run(state: dict) -> dict:
    return {"final_output": {"status": "awaiting_manual_edit", "mock": True}}
