import { useState, useCallback, useRef } from 'react'
import { API_BASE } from '../constants'

const MAX_LOGS = 800       // 日志最大条数，超出后裁剪
const LOG_FLUSH_MS = 120   // 日志批量刷新间隔(ms)，减少 React 重渲染

export default function useTask({ showNotification, nodes, setNodes, connections, presets, conversations, setConversations, setLogs, setIsRunning, setElapsed, clearAllNodeActivity, updateNodeActivity, loadFiles, executionMode, elapsedOffsetRef }) {
  const [taskInput, setTaskInput] = useState('')
  const [chapterCount, setChapterCount] = useState('')
  const [isRunning, setIsRunningState] = useState(false)
  const [elapsed, setElapsedState] = useState(0)
  const [optimizing, setOptimizing] = useState(false)
  const [showOptimizeDropdown, setShowOptimizeDropdown] = useState(false)
  const abortRef = useRef(null)
  const timerRef = useRef(null)

  const setIsRunningWrapper = useCallback((val) => {
    setIsRunningState(val)
    setIsRunning(val)
  }, [setIsRunning])

  const setElapsedWrapper = useCallback((val) => {
    setElapsedState(val)
    setElapsed(val)
  }, [setElapsed])

  const resolveConfig = useCallback((node) => {
    if (!node.config.preset_name) return null
    const p = presets.find(pr => pr.name === node.config.preset_name)
    if (!p) return null
    return { api_key: p.api_key, base_url: p.base_url, model: p.model, api_format: p.api_format || 'openai', chat_template_kwargs: p.chat_template_kwargs || null }
  }, [presets])

  const runTask = useCallback(async (t) => {
    if (!taskInput.trim()) return
    const manager = nodes.find(n => n.type === 'manager')
    const workers = nodes.filter(n => n.type === 'worker')
    const managerConfig = manager ? resolveConfig(manager) : null
    if (!managerConfig && !workers.some(w => resolveConfig(w))) return showNotification(t('configureAgent'), 'error')

    const userMsg = { role: 'user', content: taskInput.trim(), timestamp: Date.now() }
    const taskContent = taskInput.trim() + (chapterCount ? `，共${chapterCount}章` : '')
    setConversations(prev => [...prev, userMsg])
    setTaskInput('')
    setIsRunningWrapper(true)
    setLogs([])
    clearAllNodeActivity()

    // 新任务：重置累计时间；续跑由 App.jsx 的 startResumeStream 处理，不会经过这里
    if (elapsedOffsetRef) elapsedOffsetRef.current = 0
    const offset = 0
    setElapsedWrapper(offset)
    const startTime = Date.now()
    timerRef.current = setInterval(() => {
      const current = offset + Math.floor((Date.now() - startTime) / 1000)
      setElapsedWrapper(current)
      if (elapsedOffsetRef) elapsedOffsetRef.current = current  // 实时记录，续跑时继续
    }, 1000)

    abortRef.current = new AbortController()

    try {
      const response = await fetch(`${API_BASE}/run-task`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        signal: abortRef.current.signal,
        body: JSON.stringify({
          task: taskContent,
          nodes: nodes.map(n => ({
            id: n.id,
            type: n.type,
            config: {
              preset_name: n.config.preset_name || '',
              custom_prompt: n.config.custom_prompt || '',
              agent_role: n.config.agent_role || '',
            }
          })),
          connections: connections.map(c => ({
            id: c.id,
            from: c.from,
            fromPort: c.fromPort || '',
            to: c.to,
            toPort: c.toPort || '',
            annotation: c.annotation || ''
          })),
          presets: presets.map(p => ({
            name: p.name,
            api_key: p.api_key,
            base_url: p.base_url,
            model: p.model,
            api_format: p.api_format || 'openai',
            chat_template_kwargs: p.chat_template_kwargs || null
          })),
          skills: [],
          conversation_history: conversations.slice(-10),
          stage_timeout_seconds: 600,
          execution_mode: executionMode
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      // === 帧级批量：收集原始数据，rAF 帧末一次性更新 React ===
      const rawLogs = []
      const frameNode = {}    // nodeId -> { activity, thought, response }
      const frameConvs = []
      let frameClear = false
      let rafId = null

      const applyFrame = () => {
        rafId = null
        // 日志
        if (rawLogs.length > 0) {
          const batch = rawLogs.splice(0)
          setLogs(prev => {
            const next = prev.concat(batch)
            return next.length > MAX_LOGS ? next.slice(-MAX_LOGS) : next
          })
        }
        // 节点：去重只留每节点最终状态
        const keys = Object.keys(frameNode)
        if (keys.length > 0) {
          const snap = { ...frameNode }
          for (const k of keys) delete frameNode[k]
          setNodes(prev => prev.map(n => snap[n.id] ? { ...n, activity: snap[n.id].activity, thought: snap[n.id].thought || n.thought, response: snap[n.id].response || n.response } : n))
        }
        if (frameClear) { frameClear = false; clearAllNodeActivity() }
        if (frameConvs.length > 0) {
          const msgs = frameConvs.splice(0)
          setConversations(prev => [...prev, ...msgs])
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.replace('data: ', ''))
              rawLogs.push(data)

              const status = data.status || ''
              const nodeId = data.node_id || ''

              if (nodeId) {
                const actMap = { info: 'thinking', working: 'responding', success: 'completed', error: 'idle' }
                const act = actMap[status]
                if (act) frameNode[nodeId] = { activity: act, thought: data.message || '', response: data.message || '' }
              }
              if (status === 'feedback_processing' || status === 'feedback_received') {
                frameClear = true
                frameConvs.push({ role: 'assistant', content: data.message, timestamp: Date.now() })
              }
              if (status === 'done') {
                frameConvs.push({ role: 'assistant', content: data.message, timestamp: Date.now() })
              } else if (status === 'error' && !nodeId) {
                showNotification(data.message, 'error')
              }

              if (!rafId) rafId = requestAnimationFrame(applyFrame)
            } catch (e) {}
          }
        }
      }
      // 最后 flush
      applyFrame()
    } catch (e) {
      applyFrame()
      if (e.name === 'AbortError') {
        setLogs(prev => [...prev, { status: 'warning', role: 'System', message: '⏹️ 任务已停止' }])
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
    loadFiles()
  }, [taskInput, nodes, connections, presets, conversations, resolveConfig, showNotification, setConversations, setLogs, setIsRunningWrapper, setElapsedWrapper, clearAllNodeActivity, updateNodeActivity, loadFiles])

  const sendFeedback = useCallback(async (message) => {
    if (!message.trim()) return
    try {
      const response = await fetch(`${API_BASE}/run-task/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message.trim() })
      })
      const data = await response.json()
      if (response.ok) {
        setConversations(prev => [...prev, { role: 'user', content: `📨 ${message.trim()}`, timestamp: Date.now() }])
        showNotification(data.message || '反馈已发送', 'success')
        return true
      } else {
        showNotification(data.detail || '反馈发送失败', 'error')
        return false
      }
    } catch (e) {
      showNotification('反馈发送失败: ' + e.message, 'error')
      return false
    }
  }, [showNotification, setConversations])

  const handleStop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
    fetch(`${API_BASE}/stop-task`, { method: 'POST' }).catch(() => {})
  }, [])

  const handleOptimize = useCallback(async (preset, t) => {
    setShowOptimizeDropdown(false)
    if (!taskInput.trim() || !preset) return
    setOptimizing(true)
    try {
      const response = await fetch(`${API_BASE}/optimize-prompt`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: taskInput.trim(),
          preset: {
            api_key: preset.api_key,
            base_url: preset.base_url,
            model: preset.model,
            api_format: preset.api_format || 'openai',
            chat_template_kwargs: preset.chat_template_kwargs || null
          }
        })
      })
      const data = await response.json()
      if (response.ok && data.optimized) {
        setTaskInput(data.optimized)
        showNotification(t('optimizeDone'), 'success')
      } else {
        showNotification(t('optimizeFailed') + ': ' + (data.detail || ''), 'error')
      }
    } catch (err) {
      showNotification(t('optimizeFailed') + ': ' + err.message, 'error')
    } finally {
      setOptimizing(false)
    }
  }, [taskInput, showNotification])

  return {
    taskInput, setTaskInput,
    chapterCount, setChapterCount,
    isRunning, setIsRunning: setIsRunningWrapper,
    elapsed, setElapsed: setElapsedWrapper,
    optimizing, showOptimizeDropdown, setShowOptimizeDropdown,
    runTask, handleStop, sendFeedback, handleOptimize,
    abortRef
  }
}
