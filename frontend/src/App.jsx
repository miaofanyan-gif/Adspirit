import { useEffect, useState } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";

const STAGE_LABELS = {
  search_videos: "搜索热门视频",
  analyze_videos: "分析视频",
  scrape_product: "抓取商品详情",
  llm_summarize: "LLM 总结内容要素",
  generate_storyboard: "生成分镜",
  generate_clips: "生成视频片段",
  final_assembly: "最终合成（人工确认）",
};

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function TaskList({ tasks, selectedId, onSelect }) {
  return (
    <ul className="task-list">
      {tasks.map((t) => (
        <li
          key={t.task_id}
          className={t.task_id === selectedId ? "selected" : ""}
          onClick={() => onSelect(t.task_id)}
        >
          <div className="task-url">{t.product_url}</div>
          <StatusBadge status={t.status} />
        </li>
      ))}
    </ul>
  );
}

function TaskDetail({ task, onResume }) {
  if (!task) return <p className="empty-hint">选择左侧一个任务查看进度</p>;

  return (
    <div>
      <h2>{task.product_url}</h2>
      <p>
        任务状态：<StatusBadge status={task.status} />
      </p>
      {task.error_message && <p className="error-text">错误：{task.error_message}</p>}
      <ol className="stage-list">
        {task.stages.map((s) => (
          <li key={s.stage_name} className={`stage stage-${s.status}`}>
            <div className="stage-header">
              <span>{STAGE_LABELS[s.stage_name] ?? s.stage_name}</span>
              <StatusBadge status={s.status} />
            </div>
            {s.output_data && (
              <pre className="stage-output">{JSON.stringify(s.output_data, null, 2)}</pre>
            )}
            {s.error_message && <p className="error-text">{s.error_message}</p>}
          </li>
        ))}
      </ol>
      {task.status === "waiting_for_review" && (
        <button onClick={() => onResume(task.task_id)}>确认并继续（人工剪辑完成）</button>
      )}
    </div>
  );
}

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [taskDetail, setTaskDetail] = useState(null);
  const [productUrl, setProductUrl] = useState("");
  const [streamKey, setStreamKey] = useState(0);

  const refreshTaskList = () => {
    fetch(`${API_BASE}/tasks`)
      .then((r) => r.json())
      .then(setTasks)
      .catch(() => {});
  };

  useEffect(() => {
    refreshTaskList();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setTaskDetail(null);
    const source = new EventSource(`${API_BASE}/tasks/${selectedId}/stream`);
    source.addEventListener("task_update", (event) => {
      const data = JSON.parse(event.data);
      setTaskDetail(data);
      setTasks((prev) =>
        prev.map((t) => (t.task_id === data.task_id ? { ...t, status: data.status } : t))
      );
    });
    source.onerror = () => source.close();
    return () => source.close();
  }, [selectedId, streamKey]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!productUrl.trim()) return;
    fetch(`${API_BASE}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_url: productUrl.trim() }),
    })
      .then((r) => r.json())
      .then(({ task_id }) => {
        setProductUrl("");
        refreshTaskList();
        setSelectedId(task_id);
      });
  };

  const handleResume = (taskId) => {
    fetch(`${API_BASE}/tasks/${taskId}/resume`, { method: "POST" }).then(() => {
      setStreamKey((k) => k + 1);
    });
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="粘贴商品链接"
            value={productUrl}
            onChange={(e) => setProductUrl(e.target.value)}
          />
          <button type="submit">发起任务</button>
        </form>
        <TaskList tasks={tasks} selectedId={selectedId} onSelect={setSelectedId} />
      </aside>
      <main className="main">
        <TaskDetail task={taskDetail} onResume={handleResume} />
      </main>
    </div>
  );
}
