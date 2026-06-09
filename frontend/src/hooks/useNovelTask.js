import { useState, useCallback, useRef } from 'react'
import { API_BASE } from '../constants'

export default function useNovelTask({ showNotification }) {
  const [taskInput, setTaskInput] = useState('')
  const [chapterCount, setChapterCount] = useState('')
  const [genre, setGenre] = useState('')
  const [novelTitle, setNovelTitle] = useState('')
  const [outlineReviewMode, setOutlineReviewMode] = useState('auto') // 'auto' | 'manual'
  const [isRunning, setIsRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [logs, setLogs] = useState([])
  const [conversations, setConversations] = useState([])
  const [nodes, setNodes] = useState([])
  const [runningTaskFolder, setRunningTaskFolder] = useState('')

  const abortRef = useRef(null)
  const timerRef = useRef(null)

  const setIsRunningWrapper = useCallback((val) => {
    setIsRunning(val)
    if (val) {
      setElapsed(0)
      setLogs([])
      setConversations([])
    }
  }, [])

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    if (h > 0) return `${h}h ${m}m ${s}s`
    return `${m}m ${s}s`
  }

  const runTask = useCallback(async (presets, nodesConfig, t) => {
    if (!novelTitle.trim() || !chapterCount || !presets?.length) return
    const manager = nodesConfig?.find(n => n.type === 'manager')

    const taskContent = novelTitle.trim() + (genre ? `（${genre}）` : '') + `，共${chapterCount}章` + (taskInput ? `，要求：${taskInput}` : '')

    setConversations([{ role: 'user', content: taskContent, timestamp: Date.now() }])
    setIsRunningWrapper(true)

    abortRef.current = new AbortController()

    const startTime = Date.now()
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)

    try {
      const response = await fetch(`${API_BASE}/run-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortRef.current.signal,
        body: JSON.stringify({
          task: taskContent,
          nodes: nodesConfig?.map(n => ({
            id: n.id,
            type: n.type,
            config: {
              preset_name: n.config.preset_name || '',
              custom_prompt: n.config.custom_prompt || '',
              agent_role: n.config.agent_role || '',
              label: n.config.label || '',
            }
          })),
          connections: nodesConfig?.getConnections?.() || [],
          presets: presets.map(p => ({
            name: p.name,
            api_key: p.api_key,
            base_url: p.base_url,
            model: p.model,
            api_format: p.api_format || 'openai',
            chat_template_kwargs: p.chat_template_kwargs || null
          })),
          skills: [],
          conversation_history: [],
          stage_timeout_seconds: 600,
          execution_mode: 'lite',
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
                setRunningTaskFolder(data.task_folder)
              }
              if (data.status === 'error' && !data.node_id) {
                showNotification(data.message, 'error')
              }
              if (data.status === 'done') {
                showNotification(t('taskCompleted'), 'success')
              }
              if (data.status === 'outline_pending_review') {
                showNotification(t('outlinePending'), 'warning')
              }
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        setLogs(prev => [...prev, { status: 'warning', role: 'System', message: '⏹️ Task stopped' }])
      } else {
        setLogs(prev => [...prev, { status: 'error', role: 'System', message: e.message }])
      }
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setIsRunningWrapper(false)
    abortRef.current = null
  }, [novelTitle, genre, chapterCount, taskInput, outlineReviewMode, setIsRunningWrapper, showNotification])

  const stopTask = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort()
    fetch(`${API_BASE}/stop-task`).catch(() => {})
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setIsRunning(false)
  }, [])

  return {
    novelTitle, setNovelTitle,
    genre, setGenre,
    taskInput, setTaskInput,
    chapterCount, setChapterCount,
    outlineReviewMode, setOutlineReviewMode,
    isRunning,
    elapsed,
    logs,
    runningTaskFolder,
    runTask,
    stopTask,
    formatTime,
  }
}
