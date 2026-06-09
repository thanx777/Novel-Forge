import useNovelReader from '../../hooks/useNovelReader'
import useNovelTask from '../../hooks/useNovelTask'
import ChapterList from './ChapterList'
import ChapterEditor from './ChapterEditor'
import NewTaskModal from './NewTaskModal'

const NOVEL_DEFAULT_NODES = [
  { id: 'm_1', type: 'manager', x: 60, y: 40, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '📖 大纲' } },
  { id: 'w_1', type: 'worker', x: 340, y: 40, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '' } },
  { id: 'r_1', type: 'reviewer', x: 620, y: 40, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '' } },
  { id: 'm_2', type: 'manager', x: 60, y: 190, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '✍️ 创作' } },
  { id: 'w_2', type: 'worker', x: 340, y: 190, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '' } },
  { id: 'r_2', type: 'reviewer', x: 620, y: 190, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '' } },
  { id: 'm_3', type: 'manager', x: 60, y: 340, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '🔍 审校' } },
  { id: 'w_3', type: 'worker', x: 340, y: 340, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '' } },
  { id: 'r_3', type: 'reviewer', x: 620, y: 340, config: { preset_name: '', agent_role: '', custom_prompt: '', label: '' } },
]

export default function NovelWorkspace({
  t, language, presets, showNewTask, setShowNewTask, showNotification, isRunning: globalRunning, setIsRunning: setGlobalRunning
}) {
  const [tasks, setTasks] = useState([])
  const [activeTaskFolder, setActiveTaskFolder] = useState('')
  const [showLogs, setShowLogs] = useState(false)
  const [showOutline, setShowOutline] = useState(false)
  const [showCharacters, setShowCharacters] = useState(false)
  const [showMemory, setShowMemory] = useState(false)
  const [executionMode, setExecutionMode] = useState('lite')
  const [logs, setLogs] = useState([])

  const {
    chapters, outline, characters, memory, fileContent,
    activeFile, loadFiles, loadChapter, saveFile, setFileContent
  } = useNovelReader(activeTaskFolder)

  // Load task list
  const loadTasks = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/tasks`)
      if (resp.ok) { const data = await resp.json(); setTasks(data.tasks || []) }
    } catch (e) { console.error('Failed to load tasks:', e) }
  }, [])

  useEffect(() => { loadTasks() }, [loadTasks])
  useEffect(() => { if (activeTaskFolder) loadFiles() }, [activeTaskFolder, loadFiles])

  // === Start Task ===
  const handleStartTask = useCallback(async (taskData) => {
    const { novelTitle, genre, chapterCount, taskInput: extraReq, outlineReviewMode, executionMode: mode } = taskData
    setExecutionMode(mode)

    // Build task content
    const taskContent = novelTitle + (genre ? `（${genre}）` : '') + `，共${chapterCount}章` + (extraReq ? `，要求：${extraReq}` : '')

    // Apply preset to all nodes
    const selectedPreset = presets[0]
    const taskNodes = NOVEL_DEFAULT_NODES.map(n => ({
      ...n,
      config: { ...n.config, preset_name: selectedPreset.name }
    }))

    const nodesPayload = taskNodes.map(n => ({
      id: n.id, type: n.type,
      config: { preset_name: n.config.preset_name || '', custom_prompt: n.config.custom_prompt || '', agent_role: n.config.agent_role || '', label: n.config.label || '' }
    }))

    const presetsPayload = presets.map(p => ({
      name: p.name, api_key: p.api_key, base_url: p.base_url, model: p.model,
      api_format: p.api_format || 'openai', chat_template_kwargs: p.chat_template_kwargs || null
    }))

    try {
      setGlobalRunning(true)
      const response = await fetch(`${API_BASE}/run-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: taskContent,
          nodes: nodesPayload,
          connections: [],
          presets: presetsPayload,
          skills: [],
          conversation_history: [],
          stage_timeout_seconds: 600,
          execution_mode: mode,
          outline_review_mode: outlineReviewMode,
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.replace('data: ', ''))
              setLogs(prev => [...prev, data])

              if (data.task_folder) {
                setActiveTaskFolder(data.task_folder)
                setShowNewTask(false)
                // Reload files after task started
                setTimeout(loadFiles, 1000)
              }
              if (data.status === 'done') {
                showNotification(t('taskCompleted'), 'success')
                setGlobalRunning(false)
                loadFiles()
                loadTasks()
              }
              if (data.status === 'error' && !data.node_id) {
                showNotification(data.message, 'error')
                setGlobalRunning(false)
              }
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      console.error('Task failed:', e)
      setLogs(prev => [...prev, { status: 'error', role: 'System', message: e.message }])
      setGlobalRunning(false)
    }
  }, [presets, t, showNotification, setGlobalRunning, loadFiles, loadTasks, setShowNewTask])

  // === Resume Task ===
  const handleResumeTask = useCallback(async (folder) => {
    setActiveTaskFolder(folder)
    try {
      const resp = await fetch(`${API_BASE}/tasks/${encodeURIComponent(folder)}/resume`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }
      })
      if (resp.ok) {
        setGlobalRunning(true)
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value)
          for (const line of chunk.split('\n')) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.replace('data: ', ''))
                setLogs(prev => [...prev, data])
                if (data.status === 'done') {
                  showNotification(t('taskCompleted'), 'success')
                  setGlobalRunning(false)
                }
              } catch (e) {}
            }
          }
        }
        loadFiles()
        loadTasks()
      }
    } catch (e) { setGlobalRunning(false) }
  }, [showNotification, t, setGlobalRunning, loadFiles, loadTasks])

  // === Delete Task ===
  const handleDeleteTask = useCallback(async (folder) => {
    if (!confirm(t('deleteConfirm'))) return
    try {
      const resp = await fetch(`${API_BASE}/tasks/${encodeURIComponent(folder)}`, { method: 'DELETE' })
      if (resp.ok) {
        showNotification(t('taskDeleted'), 'success')
        if (activeTaskFolder === folder) setActiveTaskFolder('')
        loadTasks()
      }
    } catch (e) { showNotification('Delete failed: ' + e.message, 'error') }
  }, [t, activeTaskFolder, loadTasks, showNotification])

  // === Stop Task ===
  const handleStopTask = useCallback(async () => {
    try { await fetch(`${API_BASE}/stop-task`, { method: 'POST' }).catch(() => {}) } catch (e) {}
    setGlobalRunning(false)
    showNotification(t('taskStopped'), 'info')
    loadFiles()
    loadTasks()
  }, [showNotification, t, setGlobalRunning, loadFiles, loadTasks])

  // === Export ===
  const handleExport = useCallback(async (format) => {
    if (!activeTaskFolder || chapters.length === 0) return
    try {
      let fullText = ''
      for (const chapter of chapters) {
        const resp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(activeTaskFolder)}&file=${encodeURIComponent(chapter)}`)
        if (resp.ok) {
          const data = await resp.json()
          const num = parseInt(chapter.replace(/[^0-9]/g, ''))
          if (format === 'md') {
            fullText += `\n# ${t('chapter').replace('{n}', num)}\n\n${data.content || ''}\n\n---\n\n`
          } else {
            fullText += `\n\n${t('chapter').replace('{n}', num)}\n\n${data.content || ''}\n\n`
          }
        }
      }
      if (outline) fullText = (format === 'md' ? '# ' : '') + t('outline') + '\n\n' + outline + '\n\n---\n\n' + fullText
      if (characters) fullText += (format === 'md' ? '# ' : '') + t('characters') + '\n\n' + characters + '\n\n---\n\n'

      const blob = new Blob([fullText], { type: format === 'md' ? 'text/markdown' : 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `novel.${format}`; a.click()
      URL.revokeObjectURL(url)
      showNotification(t('exportSuccess'), 'success')
    } catch (e) { showNotification(t('exportFailed'), 'error') }
  }, [activeTaskFolder, chapters, outline, characters, t, showNotification])

  // === Format time ===
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!globalRunning) { setElapsed(0); return }
    const start = Date.now()
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [globalRunning])

  const formatTime = (s) => {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = s % 60
    return h > 0 ? `${h}h ${m}m ${sec}s` : `${m}m ${sec}s`
  }

  return (
    <div className="novel-workspace">
      {/* Top Toolbar */}
      <div className="novel-toolbar">
        <div className="novel-toolbar-left">
          <button className="novel-toolbar-btn" onClick={() => setShowNewTask(true)}>✏️ {t('newNovel')}</button>
          {activeTaskFolder && (
            <button className="novel-toolbar-btn" onClick={handleStopTask} disabled={!globalRunning}>⏹ {t('stopTask')}</button>
          )}
        </div>
        <div className="novel-toolbar-right">
          {globalRunning && <div className="novel-timer">⏱ {formatTime(elapsed)}</div>}
          <select value={executionMode} onChange={e => setExecutionMode(e.target.value)} className="novel-mode-select">
            <option value="lite">{t('modeStd')}</option>
            <option value="pro">{t('modeCmp')}</option>
            <option value="pro_polish">{t('modeFull')}</option>
          </select>
          {activeTaskFolder && (
            <>
              <button className="novel-toolbar-btn" onClick={() => handleExport('md')}>📥 {t('exportMarkdown')}</button>
              <button className="novel-toolbar-btn" onClick={() => handleExport('txt')}>📥 {t('exportTxt')}</button>
            </>
          )}
          <button className="novel-toolbar-btn" onClick={() => setShowLogs(!showLogs)}>📋 {t('logs')} {showLogs ? '▲' : '▼'}</button>
        </div>
      </div>

      <div className="novel-workspace-body">
        {/* Left: Chapter List */}
        <div className="novel-sidebar">
          <ChapterList
            t={t} language={language}
            chapters={chapters} activeFile={activeFile}
            onSelectChapter={loadChapter}
            outline={outline} characters={characters} memory={memory}
            showOutline={showOutline} setShowOutline={setShowOutline}
            showCharacters={showCharacters} setShowCharacters={setShowCharacters}
            showMemory={showMemory} setShowMemory={setShowMemory}
            taskStatus={globalRunning ? 'running' : 'idle'}
          />
        </div>

        {/* Center: Chapter Editor */}
        <div className="novel-main">
          <ChapterEditor
            t={t} language={language}
            fileName={activeFile} fileContent={fileContent}
            setFileContent={setFileContent}
            onSave={saveFile} showNotification={showNotification}
          />
        </div>

        {/* Right: Logs Panel */}
        {showLogs && (
          <div className="novel-logs-panel">
            <div className="logs-panel-header">
              <span>📋 {t('logs')}</span>
              <button className="logs-close-btn" onClick={() => setShowLogs(false)}>✕</button>
            </div>
            <div className="logs-panel-body">
              {logs.map((log, i) => (
                <div key={i} className={`log-entry log-${log.status || 'info'}`}>
                  <span className="log-role">[{log.role || '?'}]</span> {log.message || ''}
                </div>
              ))}
              {globalRunning && <div className="log-entry log-loading">● {t('loading')}...</div>}
            </div>
          </div>
        )}
      </div>

      {/* Task list (shown when no active task) */}
      {!activeTaskFolder && (
        <div className="novel-task-list">
          <div className="novel-task-list-header">
            <span>📁 {t('task')}</span>
            <button className="refresh-btn" onClick={loadTasks}>↻</button>
          </div>
          {tasks.length === 0 ? (
            <div className="task-list-empty">{t('noTasks')}</div>
          ) : (
            <div className="task-list-body">
              {tasks.map(task => (
                <div key={task.folder} className="task-list-item">
                  <div className="task-info">
                    <div className="task-name">{task.task}</div>
                    <div className="task-meta">
                      <span className={`task-status task-${task.status}`}>
                        {task.status === 'completed' ? t('done') : task.status === 'in_progress' ? t('running') : t('paused')}
                      </span>
                      <span className="task-chapters">{task.chapters_done}/{task.total_chapters}</span>
                    </div>
                  </div>
                  <div className="task-actions">
                    {task.status === 'in_progress' && (
                      <button className="task-action-btn resume" onClick={() => handleResumeTask(task.folder)}>{t('resumeTask')}</button>
                    )}
                    <button className="task-action-btn delete" onClick={() => handleDeleteTask(task.folder)}>{t('deleteTask')}</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* New Task Modal */}
      <NewTaskModal
        t={t} language={language}
        show={showNewTask} setShow={setShowNewTask}
        novelTitle="" setNovelTitle={() => {}}
        chapterCount="" setChapterCount={() => {}}
        taskInput="" setTaskInput={() => {}}
        presets={presets}
        onRun={handleStartTask}
        isRunning={globalRunning}
        tConfig={{}}
      />
    </div>
  )
}
