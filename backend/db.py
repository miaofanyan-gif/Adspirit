import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./pipeline.db")
engine = create_engine(f"sqlite:///{DATABASE_PATH}")
SessionLocal = sessionmaker(bind=engine)

STAGE_ORDER = [
    "search_videos",
    "analyze_videos",
    "scrape_product",
    "llm_summarize",
    "generate_storyboard",
    "generate_clips",
    "final_assembly",
]


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    product_url: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"))
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    images: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Stage(Base):
    __tablename__ = "stages"

    stage_id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"))
    stage_name: Mapped[str] = mapped_column(String)
    stage_order: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String, default="pending")
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)


class Video(Base):
    __tablename__ = "videos"

    video_id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"))
    source_url: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String, default="tiktok")
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Storyboard(Base):
    __tablename__ = "storyboards"

    storyboard_id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Shot(Base):
    __tablename__ = "shots"

    shot_id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    storyboard_id: Mapped[str] = mapped_column(String, ForeignKey("storyboards.storyboard_id"))
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.task_id"))
    shot_order: Mapped[int] = mapped_column()
    prompt_text: Mapped[str] = mapped_column(String)
    duration_seconds: Mapped[int] = mapped_column(default=8)
    video_gen_status: Mapped[str] = mapped_column(String, default="pending")
    clip_url: Mapped[str | None] = mapped_column(String, nullable=True)
    video_gen_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def create_task(session: Session, product_url: str) -> str:
    task = Task(product_url=product_url, status="pending", current_stage=STAGE_ORDER[0])
    session.add(task)
    session.flush()
    task_id = task.task_id
    for order, stage_name in enumerate(STAGE_ORDER):
        session.add(Stage(task_id=task_id, stage_name=stage_name, stage_order=order))
    session.commit()
    return task_id


def get_task_with_stages(session: Session, task_id: str) -> dict | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    stages = session.scalars(
        select(Stage).where(Stage.task_id == task_id).order_by(Stage.stage_order)
    ).all()
    return {
        "task_id": task.task_id,
        "product_url": task.product_url,
        "status": task.status,
        "current_stage": task.current_stage,
        "error_message": task.error_message,
        "stages": [
            {
                "stage_name": s.stage_name,
                "status": s.status,
                "output_data": s.output_data,
                "error_message": s.error_message,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            }
            for s in stages
        ],
    }


def start_stage(session: Session, task_id: str, stage_name: str) -> None:
    stage = session.scalar(
        select(Stage).where(Stage.task_id == task_id, Stage.stage_name == stage_name)
    )
    stage.status = "running"
    stage.started_at = now()
    session.get(Task, task_id).current_stage = stage_name
    session.commit()


def finish_stage(session: Session, task_id: str, stage_name: str, output_data: dict) -> None:
    stage = session.scalar(
        select(Stage).where(Stage.task_id == task_id, Stage.stage_name == stage_name)
    )
    stage.status = "success"
    stage.output_data = output_data
    stage.finished_at = now()
    session.commit()


def fail_stage(session: Session, task_id: str, stage_name: str, error_message: str) -> None:
    stage = session.scalar(
        select(Stage).where(Stage.task_id == task_id, Stage.stage_name == stage_name)
    )
    stage.status = "failed"
    stage.error_message = error_message
    stage.finished_at = now()
    task = session.get(Task, task_id)
    task.status = "failed"
    task.error_message = error_message
    session.commit()
