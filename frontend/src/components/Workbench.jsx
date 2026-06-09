import { useState, useEffect, useCallback } from "react"
import { API_BASE } from "../constants"
import useNovelReader from "../hooks/useNovelReader"
import ChapterList from "./Novel/ChapterList"
import ChapterEditor from "./Novel/ChapterEditor"
import NewTaskModal from "./Novel/NewTaskModal"
import TaskDetailModal from "./TaskDetailModal"
import OutlinePanel from "./OutlinePanel"
import CharacterPanel from "./CharacterPanel"
import MemoryPanel from "./MemoryPanel"

export default function Workbench({
  t, language,
  isDark, setIsDark, setLanguage, setShowWorkspaceSettings, setShowPresetSidebar, showPresetSidebar,
  presets, showNotification,
  isRunning, setIsRunning,
  agentCatalog
}) {
  const [tasks, setTasks] = useState([])
  const [activeTaskFolder, setActiveTaskFolder] = useState("")
  const [executionMode, setExecutionMode] = useState("lite")
  const [showNewTask, setShowNewTask] = useState(false)
  const [selectedTask, setSelectedTask] = useState(null)
  const [taskDetail, setTaskDetail] = useState(null)
  const [logs, setLogs] = useState([])
  const [showDialogue, setShowDialogue] = useState(false)
  const [feedbackInput, setFeedbackInput] = useState("")
  const [elapsed, setElapsed] = useState(0)
  const [activeSidePanel, setActiveSidePanel] = useState("chapters")

  const {
    chapters, outline, characters, memory, fileContent,
    activeFile, loadFiles, loadChapter, saveFile, setFileContent
  } = useNovelReader(activeTaskFolder)

  // --- Task loading ---
  const loadTasks = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/tasks`)
      if (resp.ok) { const data = await resp.json(); setTasks(data.tasks || []) }
    } catch (e) { console.error("Failed to load tasks:", e) }
  }, [])

  useEffect(() => { loadTasks() }, [loadTasks])
  useEffect(() => { if (activeTaskFolder) loadFiles() }, [activeTaskFolder, loadFiles])

  // --- Elapsed timer ---
  useEffect(() => {
    if (!isRunning) { setElapsed(0); return }
    const start = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [isRunning])

  const formatTime = (s) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
    return h > 0 ? `${h}h ${m}m ${sec}s` : `${m}m ${sec}s`
  }

  // --- Chapter count ---
  const chapterCount = chapters.length
  const totalChapters = tasks.find(tk => tk.folder === activeTaskFolder)?.total_chapters || 0

  // --- Start Task ---
  const handleStartTask = useCallback(async (taskData) => {
    const { novelTitle, genre, chapterCount, taskInput: extraReq, outlineReviewMode, executionMode: mode } = taskData
    setExecutionMode(mode)

    const taskContent = novelTitle + (genre ? `(${genre})` : "") + `, ${chapterCount} chapters` + (extraReq ? `, requirements: ${extraReq}` : "")
    const mgrPreset = taskData.managerPreset || presets[0] || {}
    const wkrPreset = taskData.workerPreset || presets[0] || {}
    const rvwPreset = taskData.reviewerPreset || presets[0] || {}
    const taskNodes = [
      { id: "m_1", type: "manager", config: { preset_name: mgrPreset.name || "", agent_role: "", custom_prompt: "", label: "Outline" } },
      { id: "w_1", type: "worker", config: { preset_name: wkrPreset.name || "", agent_role: "", custom_prompt: "", label: "" } },
      { id: "r_1", type: "reviewer", config: { preset_name: rvwPreset.name || "", agent_role: "", custom_prompt: "", label: "" } },
      { id: "m_2", type: "manager", config: { preset_name: mgrPreset.name || "", agent_role: "", custom_prompt: "", label: "Writing" } },
      { id: "w_2", type: "worker", config: { preset_name: wkrPreset.name || "", agent_role: "", custom_prompt: "", label: "" } },
      { id: "r_2", type: "reviewer", config: { preset_name: rvwPreset.name || "", agent_role: "", custom_prompt: "", label: "" } },
      { id: "m_3", type: "manager", config: { preset_name: mgrPreset.name || "", agent_role: "", custom_prompt: "", label: "Polish" } },
      { id: "w_3", type: "worker", config: { preset_name: wkrPreset.name || "", agent_role: "", custom_prompt: "", label: "" } },
      { id: "r_3", type: "reviewer", config: { preset_name: rvwPreset.name || "", agent_role: "", custom_prompt: "", label: "" } },
    ]

    const nodesPayload = taskNodes.map(n => ({
      id: n.id, type: n.type,
      config: { preset_name: n.config.preset_name || "", custom_prompt: n.config.custom_prompt || "", agent_role: n.config.agent_role || "", label: n.config.label || "" }
    }))
    const presetsPayload = presets.map(p => ({
      name: p.name, api_key: p.api_key, base_url: p.base_url, model: p.model,
      api_format: p.api_format || "openai", chat_template_kwargs: p.chat_template_kwargs || null
    }))

    try {
      setIsRunning(true)
      setShowDialogue(true)
      const response = await fetch(`${API_BASE}/run-task`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: taskContent, nodes: nodesPayload, connections: [],
          presets: presetsPayload, skills: [], conversation_history: [],
          stage_timeout_seconds: 600, execution_mode: mode, outline_review_mode: outlineReviewMode,
        })
      })
      if (!response.ok) {
        const err = await response.text()
        showNotification(t("taskError") + `: HTTP ${response.status}`, "error")
        setIsRunning(false)
        return
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value).split("\n")) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.replace("data: ", ""))
              setLogs(prev => [...prev, data])
              if (data.task_folder) {
                setActiveTaskFolder(data.task_folder)
                setShowNewTask(false)
                // 立即加载一次，然后最多重试 3 次，每次间隔 2 秒
                let retries = 0
                const loadWithRetry = () => {
                  loadFiles()
                  if (retries < 3) {
                    retries++
                    setTimeout(loadWithRetry, 2000)
                  }
                }
                loadWithRetry()
              }
              if (data.status === "done") { showNotification(t("taskCompleted"), "success"); setIsRunning(false); loadFiles(); loadTasks() }
              if (data.status === "paused") { showNotification(data.message || t("taskPaused"), "info"); setIsRunning(false); loadFiles(); loadTasks() }
              if (data.status === "error" && !data.node_id) { showNotification(data.message, "error"); setIsRunning(false) }
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      setLogs(prev => [...prev, { status: "error", role: "System", message: e.message }])
      setIsRunning(false)
    }
  }, [presets, t, showNotification, setIsRunning, loadFiles, loadTasks])

  // --- Resume Task ---
  const handleResumeTask = useCallback(async (folder) => {
    setActiveTaskFolder(folder)
    setShowDialogue(true)
    try {
      const resp = await fetch(`${API_BASE}/tasks/${encodeURIComponent(folder)}/resume`, {
        method: "POST", headers: { "Content-Type": "application/json" }
      })
      if (resp.ok) {
        setIsRunning(true)
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          for (const line of decoder.decode(value).split("\n")) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.replace("data: ", ""))
                setLogs(prev => [...prev, data])
                if (data.status === "done") { showNotification(t("taskCompleted"), "success"); setIsRunning(false) }
                if (data.status === "paused") { showNotification(data.message || t("taskPaused"), "info"); setIsRunning(false) }
              } catch (e) {}
            }
          }
        }
        loadFiles(); loadTasks()
      }
    } catch (e) { setIsRunning(false) }
  }, [showNotification, t, setIsRunning, loadFiles, loadTasks])

  // --- Click Task to view detail ---
  const handleTaskClick = useCallback(async (folder) => {
    setActiveTaskFolder(folder)
    try {
      const resp = await fetch(`${API_BASE}/tasks/${encodeURIComponent(folder)}`)
      if (resp.ok) {
        const data = await resp.json()
        setTaskDetail(data)
        setSelectedTask(folder)
      }
    } catch (e) { console.error("Failed to load task detail:", e) }
  }, [])

  // --- Stop / Delete ---
  const handleStopTask = useCallback(async () => {
    try { await fetch(`${API_BASE}/stop-task`, { method: "POST" }).catch(() => {}) } catch (e) {}
    setIsRunning(false); showNotification(t("taskStopped"), "info"); loadFiles(); loadTasks()
  }, [showNotification, t, setIsRunning, loadFiles, loadTasks])

  const handleDeleteTask = useCallback(async (folder) => {
    if (!confirm(t("deleteConfirm"))) return
    try {
      await fetch(`${API_BASE}/tasks/${encodeURIComponent(folder)}`, { method: "DELETE" })
      showNotification(t("taskDeleted"), "success")
      if (activeTaskFolder === folder) setActiveTaskFolder(""); loadTasks()
    } catch (e) { showNotification("Delete failed: " + e.message, "error") }
  }, [t, activeTaskFolder, loadTasks, showNotification])

  // --- Send feedback to AI ---
  const handleSendFeedback = useCallback(async () => {
    if (!feedbackInput.trim() || !isRunning) return
    try {
      await fetch(`${API_BASE}/run-task/feedback`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: feedbackInput.trim() })
      })
      setLogs(prev => [...prev, { status: "info", role: " You", message: feedbackInput.trim() }])
      setFeedbackInput("")
      showNotification(language === "zh" ? "反馈已发送" : "Feedback sent", "success")
    } catch (e) {}
  }, [feedbackInput, isRunning, showNotification, language])

  // --- Export ---
  const handleExport = useCallback(async (format) => {
    if (!activeTaskFolder || chapters.length === 0) return
    try {
      let fullText = ""
      for (const chapter of chapters) {
        const resp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(activeTaskFolder)}&file=${encodeURIComponent(chapter)}`)
        if (resp.ok) {
          const data = await resp.json()
          const num = parseInt(chapter.replace(/[^0-9]/g, ""))
          fullText += format === "md"
            ? `\n# Chapter ${num}\n\n${data.content || ""}\n\n---\n\n`
            : `\n\nChapter ${num}\n\n${data.content || ""}\n\n`
        }
      }
      const blob = new Blob([fullText], { type: format === "md" ? "text/markdown" : "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a"); a.href = url; a.download = `novel.${format}`; a.click()
      URL.revokeObjectURL(url); showNotification(t("exportSuccess"), "success")
    } catch (e) { showNotification(t("exportFailed"), "error") }
  }, [activeTaskFolder, chapters, t, showNotification])

  const SIDE_TABS = [
    { key: "chapters", label: " " + (language === "zh" ? "章节" : "Chapters") },
    { key: "outline", label: " " + (language === "zh" ? "大纲" : "Outline") },
    { key: "characters", label: " " + (language === "zh" ? "人物" : "Chars") },
    { key: "memory", label: " " + (language === "zh" ? "记忆" : "Memory") },
    { key: "tasks", label: " " + (language === "zh" ? "任务" : "Tasks") },
  ]

    return (
    <div className="wb-container">
      <div className="wb-toolbar">
        <div className="wb-toolbar-left">
          <div className="toolbar-brand">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              <line x1="8" y1="7" x2="16" y2="7"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
            <span>{language === "zh" ? "小说锻造" : "Novel Forge"}</span>
          </div>
          <div className="toolbar-divider" />
          <button className={`toolbar-btn ${showPresetSidebar ? "active" : ""}`} onClick={() => setShowPresetSidebar(!showPresetSidebar)} title={t("presets")}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            {t("presets")}
          </button>
          <button className="toolbar-btn" onClick={() => setShowWorkspaceSettings(true)} title={t("settings")}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            {t("settings")}
          </button>
          <div className="toolbar-divider" />
          <button className="wb-btn wb-btn-new" onClick={() => setShowNewTask(true)} disabled={isRunning}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            {language === "zh" ? "新任务" : "New Task"}
          </button>
          {activeTaskFolder && isRunning && (
            <button className="wb-btn wb-btn-stop" onClick={handleStopTask}>
              {language === "zh" ? "停止" : "Stop"}
            </button>
          )}
          <button className={`wb-btn ${showDialogue ? "active" : ""}`} onClick={() => setShowDialogue(!showDialogue)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            {showDialogue ? "▲" : "▼"}
          </button>
        </div>
        <div className="wb-toolbar-right">
          {isRunning && <span className="wb-timer">{"⏱"} {formatTime(elapsed)}</span>}
          <span className="wb-progress">{chapterCount}{totalChapters ? `/${totalChapters}` : ""} {language === "zh" ? "章" : "ch"}</span>
          <select value={executionMode} onChange={e => setExecutionMode(e.target.value)} className="wb-select">
            <option value="lite">{language === "zh" ? "精简" : "Lite"}</option>
            <option value="pro">{language === "zh" ? "标准" : "Standard"}</option>
            <option value="pro_polish">{language === "zh" ? "完整" : "Full"}</option>
          </select>
          {activeTaskFolder && (
            <>
              <button className="wb-btn" onClick={() => handleExport("md")}>{language === "zh" ? "导出" : "Export"} MD</button>
              <button className="wb-btn" onClick={() => handleExport("txt")}>{language === "zh" ? "导出" : "Export"} TXT</button>
            </>
          )}
          <div className="toolbar-divider" />
          <button className="toolbar-btn lang-toggle" onClick={() => setLanguage(l => l === "zh" ? "en" : "zh")}>
            {language === "en" ? "中文" : "EN"}
          </button>
          <button className="toolbar-btn theme-toggle" onClick={() => setIsDark(!isDark)}>
            {isDark ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2m0 18v2M21 12h2M1 12h2m16.95-6.95l1.414 1.414M2.636 21.364l1.414-1.414M4.636 4.636l1.414 1.414M17.95 19.364l1.414-1.414"/></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
            )}
          </button>
        </div>
      </div>

{/* Body */}
      <div className="wb-body">
        {/* Left Sidebar */}
        <aside className="wb-sidebar">
          <div className="wb-sidebar-tabs">
            {SIDE_TABS.map(tab => (
              <button key={tab.key} className={`wb-sidebar-tab ${activeSidePanel === tab.key ? "active" : ""}`}
                onClick={() => setActiveSidePanel(tab.key)}>
                {tab.label}
              </button>
            ))}
          </div>
          <div className="wb-sidebar-content">
            {activeSidePanel === "chapters" && (
              <ChapterList t={t} language={language}
                chapters={chapters} activeFile={activeFile}
                onSelectChapter={loadChapter} outline="" characters="" memory=""
                showOutline={false} setShowOutline={() => {}}
                showCharacters={false} setShowCharacters={() => {}}
                showMemory={false} setShowMemory={() => {}}
                taskStatus={isRunning ? "running" : "idle"}
              />
            )}
            {activeSidePanel === "outline" && (
              <OutlinePanel t={t} language={language} outline={outline}
                onSave={(text) => saveFile("outline.md", text)} showNotification={showNotification} />
            )}
            {activeSidePanel === "characters" && (
              <CharacterPanel t={t} language={language} characters={characters}
                onSave={(text) => saveFile("characters.md", text)} showNotification={showNotification} />
            )}
            {activeSidePanel === "memory" && (
              <MemoryPanel t={t} language={language} memory={memory} />
            )}
            {activeSidePanel === "tasks" && (
              <div className="side-panel">
                <div className="side-panel-header"><span> {t("task")}</span></div>
                <div className="side-panel-body">
                  {tasks.length === 0 ? (
                    <div className="side-panel-empty">{t("noTasks")}</div>
                  ) : (
                    tasks.map(task => (
                      <div key={task.folder} className={`wb-task-item ${activeTaskFolder === task.folder ? "active" : ""}`} onClick={() => handleTaskClick(task.folder)}>
                        <div className="wb-task-info">
                          <div className="wb-task-name">{task.task}</div>
                          <div className="wb-task-meta">
                            <span className={`wb-task-status wb-status-${task.status}`}>
                              {task.status === "completed" ? t("done") : task.status === "in_progress" ? t("paused") : t("paused")}
                            </span>
                            <span>{task.chapters_done ?? 0}/{task.total_chapters ?? 0}</span>
                          </div>
                        </div>
                        <div className="wb-task-actions">
                          {task.status === "in_progress" && (
                            <button className="wb-btn-sm wb-btn-resume" onClick={(e) => { e.stopPropagation(); handleResumeTask(task.folder) }} title={t('resumeTask')}>
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            </button>
                          )}
                          <button className="wb-btn-sm wb-btn-delete" onClick={(e) => { e.stopPropagation(); handleDeleteTask(task.folder) }} title={t('delete')}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Center Editor */}
        <main className="wb-main">
          <ChapterEditor t={t} language={language}
            fileName={activeFile} fileContent={fileContent}
            setFileContent={setFileContent}
            onSave={saveFile} showNotification={showNotification}
          />
        </main>

        {/* Right: AI Dialogue Panel */}
        {showDialogue && (
          <div className="wb-dialogue">
            <div className="wb-dialogue-header">
              <span> {language === "zh" ? "AI 对话" : "AI Dialogue"}</span>
              <button className="wb-dialogue-close" onClick={() => setShowDialogue(false)}></button>
            </div>
            <div className="wb-dialogue-messages">
              {logs.length === 0 && !isRunning && (
                <div className="wb-dialogue-empty">
                  {language === "zh" ? "开始写作后，这里会显示 AI 的实时状态" : "Start writing to see AI progress here"}
                </div>
              )}
              {logs.map((log, i) => (
                <div key={i} className={`wb-msg ${log.role === " You" ? "wb-msg-user" : ""} ${log.status === "error" ? "wb-msg-error" : ""}`}>
                  <span className="wb-msg-role">{log.role || ""}</span>
                  <span className="wb-msg-text">{log.message || ""}</span>
                </div>
              ))}
              {isRunning && (
                <div className="wb-msg wb-msg-loading">
                  <span className="wb-msg-role"></span>
                  <span className="wb-msg-dots"><span>.</span><span>.</span><span>.</span></span>
                </div>
              )}
            </div>
            {isRunning && (
              <div className="wb-dialogue-input">
                <input
                  type="text" value={feedbackInput}
                  onChange={e => setFeedbackInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") handleSendFeedback() }}
                  placeholder={language === "zh" ? "发送反馈给 AI..." : "Send feedback to AI..."}
                  className="wb-dialogue-field"
                />
                <button className="wb-dialogue-send" onClick={handleSendFeedback} disabled={!feedbackInput.trim()}>
                  
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* New Task Modal */}
      {showNewTask && (
        <NewTaskModal
          t={t} language={language}
          show={showNewTask} setShow={setShowNewTask}
          presets={presets} onRun={handleStartTask} isRunning={isRunning}
        />
      )}

      {/* Task Detail Modal */}
      {selectedTask && taskDetail && (
        <TaskDetailModal
          t={t} language={language} presets={presets}
          taskFolder={selectedTask} taskDetail={taskDetail}
          onClose={() => { setSelectedTask(null); setTaskDetail(null) }}
          onResume={() => { setSelectedTask(null); setTaskDetail(null); handleResumeTask(selectedTask) }}
          isRunning={isRunning} showNotification={showNotification}
        />
      )}
    </div>
  )
}