import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from db import DATABASE_PATH, STAGE_ORDER, SessionLocal, Task, fail_stage, finish_stage, now, start_stage
from nodes import (
    analyze_videos,
    final_assembly,
    generate_clips,
    generate_storyboard,
    llm_summarize,
    scrape_product,
    search_videos,
)


class PipelineState(TypedDict, total=False):
    task_id: str
    product_url: str
    videos: list
    product: dict
    content_factors: dict
    storyboard: dict
    clips: list
    final_output: dict


NODE_FUNCS = {
    "search_videos": search_videos.run,
    "analyze_videos": analyze_videos.run,
    "scrape_product": scrape_product.run,
    "llm_summarize": llm_summarize.run,
    "generate_storyboard": generate_storyboard.run,
    "generate_clips": generate_clips.run,
    "final_assembly": final_assembly.run,
}


def with_stage_tracking(stage_name: str, fn):
    def wrapped(state: PipelineState) -> dict:
        task_id = state["task_id"]
        session = SessionLocal()
        try:
            start_stage(session, task_id, stage_name)
            try:
                result = fn(state)
            except Exception as exc:
                fail_stage(session, task_id, stage_name, str(exc))
                raise
            finish_stage(session, task_id, stage_name, result)
            return result
        finally:
            session.close()

    return wrapped


def _build_graph():
    builder = StateGraph(PipelineState)
    for stage_name in STAGE_ORDER:
        builder.add_node(stage_name, with_stage_tracking(stage_name, NODE_FUNCS[stage_name]))
    builder.set_entry_point(STAGE_ORDER[0])
    for a, b in zip(STAGE_ORDER, STAGE_ORDER[1:]):
        builder.add_edge(a, b)
    builder.add_edge(STAGE_ORDER[-1], END)

    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer, interrupt_before=["final_assembly"])


_graph = _build_graph()


def _mark_task_running(task_id: str) -> None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        task.status = "running"
        session.commit()
    finally:
        session.close()


def _sync_task_status_after_run(task_id: str) -> None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        state = _graph.get_state({"configurable": {"thread_id": task_id}})
        if state.next:
            task.status = "waiting_for_review"
        else:
            task.status = "completed"
            task.completed_at = now()
        session.commit()
    finally:
        session.close()


def run_pipeline(task_id: str, product_url: str) -> None:
    _mark_task_running(task_id)
    initial_state: PipelineState = {"task_id": task_id, "product_url": product_url}
    config = {"configurable": {"thread_id": task_id}}
    _graph.invoke(initial_state, config=config)
    _sync_task_status_after_run(task_id)


def resume_pipeline(task_id: str) -> None:
    _mark_task_running(task_id)
    config = {"configurable": {"thread_id": task_id}}
    _graph.invoke(None, config=config)
    _sync_task_status_after_run(task_id)
