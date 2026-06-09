import { useState } from "react"

export default function NewTaskModal({
  t, language,
  show, setShow,
  presets, onRun, isRunning
}) {
  const [novelTitle, setNovelTitle] = useState("")
  const [chapterCount, setChapterCount] = useState("")
  const [taskInput, setTaskInput] = useState("")
  const [genre, setGenre] = useState("")
  const [outlineReviewMode, setOutlineReviewMode] = useState("auto")
  const [executionMode, setExecutionMode] = useState("lite")
  const [managerIdx, setManagerIdx] = useState(-1)
  const [workerIdx, setWorkerIdx] = useState(-1)
  const [reviewerIdx, setReviewerIdx] = useState(-1)

  const GENRES_ZH = ["玄幻", "都市", "言情", "仙侠", "科幻", "历史", "武侠", "悬疑", "恐怖", "喜剧", "都市爽文", "系统流"]
  const GENRES_EN = ["Fantasy", "Urban", "Romance", "Xianxia", "Sci-Fi", "Historical", "Martial Arts", "Suspense", "Horror", "Comedy", "Urban Fantasy", "System Flow"]
  const GENRES = language === "zh" ? GENRES_ZH : GENRES_EN

  const allRolesAssigned = presets.length > 0 && managerIdx >= 0 && workerIdx >= 0 && reviewerIdx >= 0

  const handleClose = () => {
    setShow(false)
    setNovelTitle(""); setChapterCount(""); setTaskInput(""); setGenre("")
    setOutlineReviewMode("auto"); setExecutionMode("lite")
    setManagerIdx(-1); setWorkerIdx(-1); setReviewerIdx(-1)
  }

  const handleStart = () => {
    if (!novelTitle.trim() || !chapterCount) return
    if (!allRolesAssigned) return
    onRun({
      novelTitle: novelTitle.trim(),
      genre,
      chapterCount,
      taskInput: taskInput.trim(),
      outlineReviewMode,
      executionMode,
      managerPreset: presets[managerIdx],
      workerPreset: presets[workerIdx],
      reviewerPreset: presets[reviewerIdx]
    })
  }

  if (!show) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content novel-modal" onClick={e => e.stopPropagation()}>
        <div className="novel-modal-header">
          <h2> {language === "zh" ? "新建小说任务" : "New Novel Task"}</h2>
          <button className="modal-close-btn" onClick={handleClose}>✕</button>
        </div>

        <div className="novel-modal-body">
          {/* Title */}
          <div className="form-group">
            <label> {language === "zh" ? "小说标题" : "Novel Title"}</label>
            <input
              type="text" value={novelTitle}
              onChange={e => setNovelTitle(e.target.value)}
              placeholder={language === "zh" ? "例如：一位少年踏上修仙之路" : "e.g., A youth embarks on a cultivation journey"}
              className="form-input" autoFocus
            />
          </div>

          {/* Genre + Chapters row */}
          <div className="form-row">
            <div className="form-group form-group-half">
              <label> {language === "zh" ? "类型" : "Genre"}</label>
              <select value={genre} onChange={e => setGenre(e.target.value)} className="form-select">
                <option value="">{language === "zh" ? "选择类型（可选）" : "Select (optional)"}</option>
                {GENRES.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="form-group form-group-half">
              <label> {language === "zh" ? "章节数" : "Chapters"}</label>
              <input
                type="number" value={chapterCount}
                onChange={e => setChapterCount(e.target.value)}
                placeholder="100" min="1" max="2000"
                className="form-input"
              />
            </div>
          </div>

          {/* Writing mode */}
          <div className="form-group">
            <label> {language === "zh" ? "写作模式" : "Writing Mode"}</label>
            <div className="mode-selector mode-selector-3">
              {[
                { key: "lite", label: language === "zh" ? "标准" : "Standard", desc: language === "zh" ? "精简提示词 · 主流模型" : "Compact prompts · Mainstream models" },
                { key: "pro", label: language === "zh" ? "兼容" : "Compatible", desc: language === "zh" ? "详细提示词 · 开源模型" : "Detailed prompts · Open models" },
                { key: "pro_polish", label: language === "zh" ? "完整" : "Full", desc: language === "zh" ? "润色循环 · 高级模型" : "Polish loop · Advanced models" },
              ].map(m => (
                <div
                  key={m.key}
                  className={`mode-card ${executionMode === m.key ? "active" : ""}`}
                  onClick={() => setExecutionMode(m.key)}
                >
                  <div className="mode-card-radio">
                    <div className={`radio-dot ${executionMode === m.key ? "checked" : ""}`} />
                  </div>
                  <div className="mode-card-text">
                    <span className="mode-card-label">{m.label}</span>
                    <span className="mode-card-desc">{m.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Outline review mode */}
          <div className="form-group">
            <label> {language === "zh" ? "大纲审核" : "Outline Review"}</label>
            <div className="mode-selector mode-selector-2">
              {[
                { key: "auto", label: language === "zh" ? "AI 自动审核" : "AI Auto Review", desc: language === "zh" ? "AI 自动审核大纲质量" : "AI reviews outline automatically" },
                { key: "manual", label: language === "zh" ? "人工确认" : "Manual Confirm", desc: language === "zh" ? "生成大纲后暂停，人工确认再继续" : "Pause after outline, manual confirm" },
              ].map(m => (
                <div
                  key={m.key}
                  className={`mode-card ${outlineReviewMode === m.key ? "active" : ""}`}
                  onClick={() => setOutlineReviewMode(m.key)}
                >
                  <div className="mode-card-radio">
                    <div className={`radio-dot ${outlineReviewMode === m.key ? "checked" : ""}`} />
                  </div>
                  <div className="mode-card-text">
                    <span className="mode-card-label">{m.label}</span>
                    <span className="mode-card-desc">{m.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Per-role model assignment */}
          <div className="form-group">
            <label> {language === "zh" ? "AI 模型分配" : "AI Model Assignment"}</label>
            {presets.length === 0 ? (
              <div className="preset-warning"> {language === "zh" ? "请先配置 API 预设" : "Please configure an API preset first"}</div>
            ) : (
              <div className="role-preset-grid">
                {[
                  { role: "manager", label: language === "zh" ? "🧠 管理者 (Manager)" : "🧠 Manager", desc: language === "zh" ? "负责大纲规划与任务调度" : "Outline planning & task scheduling", idx: managerIdx, setIdx: setManagerIdx },
                  { role: "worker", label: language === "zh" ? "✍️ 写手 (Worker)" : "✍️ Worker", desc: language === "zh" ? "负责逐章写作生成" : "Chapter-by-chapter writing", idx: workerIdx, setIdx: setWorkerIdx },
                  { role: "reviewer", label: language === "zh" ? "🔍 审校 (Reviewer)" : "🔍 Reviewer", desc: language === "zh" ? "负责质量审查与一致性校验" : "Quality review & consistency check", idx: reviewerIdx, setIdx: setReviewerIdx },
                ].map(r => (
                  <div key={r.role} className="role-preset-row">
                    <div className="role-preset-info">
                      <span className="role-preset-label">{r.label}</span>
                      <span className="role-preset-desc">{r.desc}</span>
                    </div>
                    <select
                      value={r.idx}
                      onChange={e => r.setIdx(parseInt(e.target.value))}
                      className="form-select role-preset-select"
                    >
                      <option value={-1}>{language === "zh" ? "— 选择模型 —" : "— Select model —"}</option>
                      {presets.map((p, i) => (
                        <option key={i} value={i}>{p.name} ({p.model})</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            )}
            {presets.length > 0 && !allRolesAssigned && novelTitle.trim() && chapterCount && (
              <div className="preset-warning" style={{ marginTop: 'var(--space-2)' }}>
                {language === "zh" ? "⚠️ 请为每个角色分配模型后才能开始写作" : "⚠️ Assign a model to each role before starting"}
              </div>
            )}
          </div>

          {/* Extra requirements */}
          <div className="form-group">
            <label> {language === "zh" ? "附加要求（可选）" : "Extra Requirements (optional)"}</label>
            <textarea
              value={taskInput}
              onChange={e => setTaskInput(e.target.value)}
              placeholder={language === "zh" ? "如：节奏要快，要有爽点，主角要冷酷" : "e.g., Fast pacing, protagonist should be cold"}
              rows={3} className="form-textarea"
            />
          </div>
        </div>

        <div className="novel-modal-footer">
          <button className="btn btn-cancel" onClick={handleClose} disabled={isRunning}>
            {language === "zh" ? "取消" : "Cancel"}
          </button>
          <button className="btn btn-primary btn-start" onClick={handleStart}
            disabled={isRunning || !novelTitle.trim() || !chapterCount || !allRolesAssigned}>
            {isRunning ? " ⏳ ..." : (outlineReviewMode === "manual"
              ? (language === "zh" ? "生成大纲（人工确认）" : "Generate Outline (Manual)")
              : (language === "zh" ? "🚀 开始写作" : "🚀 Start Writing"))}
          </button>
        </div>
      </div>
    </div>
  )
}
