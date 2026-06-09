import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { API_BASE } from '../constants'

const HIGHLIGHT_PATTERNS = [
  { pattern: /^(Traceback|Error|Exception|Traceback \(most recent call last\)):?/gm, className: 'hl-error' },
  { pattern: /^  File ".+?", line \d+/gm, className: 'hl-file' },
  { pattern: /(^|\s)SyntaxError|^IndentationError|^TypeError|^NameError|^ImportError|^AttributeError|^RuntimeError/gm, className: 'hl-error' },
  { pattern: /warning|warn|注意|警告/gim, className: 'hl-warn' },
  { pattern: /success|成功|完成|^✅|done|^✓|^✔|^>/gm, className: 'hl-success' },
  { pattern: /pip install|npm install|yarn add|Installing|^Collecting/gm, className: 'hl-install' },
  { pattern: /localhost|127\.0\.0\.1|https?:\/\/[^\s]+/g, className: 'hl-url' },
  { pattern: /\bfalse\b|\btrue\b|\bNone\b|\bnull\b|\bundefined\b/g, className: 'hl-bool' },
  { pattern: /\b\d+(\.\d+)?(ms|s|μs)?\b/g, className: 'hl-number' },
  { pattern: /"[^"]{0,60}"|'[^']{0,60}'/g, className: 'hl-string' },
]

const COMMON_COMMANDS = [
  'python -m py_compile', 'python', 'node', 'npm', 'pip install',
  'ls', 'dir', 'cat', 'type', 'cd workspace', 'cd backend',
]

function highlight(text) {
  if (!text) return null
  const lines = text.split('\n')
  return lines.map((line, i) => {
    let highlighted = line
    let match
    const segments = []
    let lastIndex = 0
    const allMatches = []
    for (const { pattern, className } of HIGHLIGHT_PATTERNS) {
      const regex = new RegExp(pattern.source, pattern.flags)
      while ((match = regex.exec(line)) !== null) {
        allMatches.push({ start: match.index, end: match.index + match[0].length, className })
      }
    }
    allMatches.sort((a, b) => a.start - b.start)
    if (allMatches.length === 0) {
      return <span key={i}>{line || ' '}</span>
    }
    for (const m of allMatches) {
      if (m.start >= lastIndex) {
        if (m.start > lastIndex) segments.push(<span key={`${i}-pre-${lastIndex}`}>{line.slice(lastIndex, m.start)}</span>)
        segments.push(<span key={`${i}-hl-${m.start}`} className={m.className}>{line.slice(m.start, m.end)}</span>)
        lastIndex = m.end
      }
    }
    if (lastIndex < line.length) segments.push(<span key={`${i}-post-${lastIndex}`}>{line.slice(lastIndex)}</span>)
    return <span key={i}>{segments.length > 0 ? segments : (line || ' ')}</span>
  })
}

function formatTime(date) {
  return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <button className="term-copy-btn" onClick={copy} title="Copy">
      {copied ? (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
      ) : (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
      )}
    </button>
  )
}

function TermLine({ log, index, language }) {
  const time = log._time || new Date()
  const lineNum = String(index + 1).padStart(3, ' ')
  const isPrompt = log.type === 'prompt'
  const isError = log.type === 'error'
  const isDone = log.type === 'done'
  const isInfo = log.type === 'info'
  const content = log.data || ''
  const rawContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2)
  const highlighted = highlight(rawContent)
  const isHighlighted = highlighted && (highlighted.length > 1 || (highlighted[0] && highlighted[0].props && highlighted[0].props.children !== rawContent))

  if (isDone) {
    const icon = log.exit_code === 0 ? '✓' : '✗'
    const cls = log.exit_code === 0 ? 'term-exit-ok' : 'term-exit-fail'
    const time_str = log.elapsed ? `${log.elapsed.toFixed(2)}s` : ''
    return (
      <div className={`term-line ${cls} term-exit-line`}>
        <span className="term-linenum">{lineNum}</span>
        <span className="term-time">{formatTime(time)}</span>
        <span className="term-content">{icon} exit:{log.exit_code}</span>
        {time_str && <span className="term-elapsed">{time_str}</span>}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="term-line term-error-line">
        <span className="term-linenum">{lineNum}</span>
        <span className="term-time">{formatTime(time)}</span>
        <span className="term-content">{highlight(rawContent)}</span>
        <CopyButton text={rawContent} />
      </div>
    )
  }

  if (isInfo) {
    return (
      <div className="term-line term-info-line">
        <span className="term-linenum">{lineNum}</span>
        <span className="term-time">{formatTime(time)}</span>
        <span className="term-content">{highlight(rawContent)}</span>
        <CopyButton text={rawContent} />
      </div>
    )
  }

  if (isPrompt) {
    return (
      <div className="term-line term-prompt-line">
        <span className="term-linenum">{lineNum}</span>
        <span className="term-time">{formatTime(time)}</span>
        <span className="term-prompt-cmd">{highlight(rawContent.replace(/^\$\s*/, ''))}</span>
      </div>
    )
  }

  return (
    <div className={`term-line term-stdout-line${isHighlighted ? ' term-highlighted' : ''}`}>
      <span className="term-linenum">{lineNum}</span>
      <span className="term-time">{formatTime(time)}</span>
      <span className="term-content">{highlight(rawContent)}</span>
      <CopyButton text={rawContent} />
    </div>
  )
}

function SearchBar({ search, setSearch, onClose, language }) {
  const inputRef = useRef(null)
  useEffect(() => { inputRef.current?.focus() }, [])
  return (
    <div className="term-search-bar">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
      <input
        ref={inputRef}
        type="text"
        className="term-search-input"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder={language === 'zh' ? '搜索...' : 'Search...'}
        onKeyDown={e => { if (e.key === 'Escape') onClose() }}
      />
      {search && <span className="term-search-count">{language === 'zh' ? '按 Esc 关闭' : 'Esc to close'}</span>}
    </div>
  )
}

export default function TerminalPanel({ t, language, showTerminal, setShowTerminal, testLogs, setTestLogs, dangerCommand, setDangerCommand }) {
  const [command, setCommand] = useState('')
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [ws, setWs] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [cwd, setCwd] = useState('')
  const [statusText, setStatusText] = useState('')
  const [showHelp, setShowHelp] = useState(false)
  const [search, setSearch] = useState('')
  const [searchMatches, setSearchMatches] = useState([])
  const [showCompletions, setShowCompletions] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [height, setHeight] = useState(280)
  const [isResizing, setIsResizing] = useState(false)
  const terminalRef = useRef(null)
  const inputRef = useRef(null)
  const reconnectRef = useRef(0)
  const MAX_RECONNECT = 5
  const lineRefs = useRef({})

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = API_BASE ? new URL(API_BASE).host : '127.0.0.1:8000'
    const wsUrl = `${protocol}//${host}/api/test/terminal/ws`
    const socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      setIsConnected(true)
      reconnectRef.current = 0
      setStatusText('')
    }

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'connected') {
        setCwd(data.cwd || '')
        setStatusText(data.data || '')
        return
      }
      if (data.type === 'dangerous') {
        setDangerCommand(data.command)
      } else {
        setTestLogs(prev => [...prev, { ...data, _time: new Date() }])
      }
    }

    socket.onclose = () => {
      setIsConnected(false)
      setStatusText(language === 'zh' ? '连接断开' : 'Disconnected')
      if (reconnectRef.current < MAX_RECONNECT) {
        const delay = Math.min(1000 * (reconnectRef.current + 1), 5000)
        reconnectRef.current++
        setStatusText(language === 'zh' ? `重连中 (${reconnectRef.current}/${MAX_RECONNECT})...` : `Reconnecting (${reconnectRef.current}/${MAX_RECONNECT})...`)
        setTimeout(connect, delay)
      }
    }

    socket.onerror = () => {
      setStatusText(language === 'zh' ? '连接失败' : 'Connection failed')
    }

    setWs(socket)
    return socket
  }, [language])

  useEffect(() => {
    if (!showTerminal) return
    const socket = connect()
    return () => { socket?.close() }
  }, [showTerminal])

  useEffect(() => {
    if (!terminalRef.current || !autoScroll) return
    terminalRef.current.scrollTop = terminalRef.current.scrollHeight
  }, [testLogs, autoScroll])

  const handleScroll = useCallback(() => {
    if (!terminalRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = terminalRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 10
    if (!isAtBottom && autoScroll) setAutoScroll(false)
    if (isAtBottom && !autoScroll) setAutoScroll(true)
  }, [autoScroll])

  useEffect(() => {
    if (search && terminalRef.current) {
      const matches = []
      testLogs.forEach((log, i) => {
        const content = String(log.data || '')
        if (content.toLowerCase().includes(search.toLowerCase())) {
          matches.push(i)
          if (lineRefs.current[i]) {
            lineRefs.current[i].scrollIntoView({ block: 'center' })
          }
        }
      })
      setSearchMatches(matches)
    } else {
      setSearchMatches([])
    }
  }, [search, testLogs])

  const executeCommand = useCallback(() => {
    if (!command.trim() || !ws || ws.readyState !== WebSocket.OPEN) return
    setHistory(prev => [...prev, command])
    setHistoryIndex(-1)
    setShowCompletions(false)
    setTestLogs(prev => [...prev, { type: 'prompt', data: `$ ${command}`, _time: new Date() }])
    ws.send(JSON.stringify({ command }))
    setCommand('')
    setAutoScroll(true)
  }, [command, ws, testLogs])

  const handleTabComplete = useCallback(() => {
    const input = command.trim()
    if (!input) return
    const matches = COMMON_COMMANDS.filter(c => c.startsWith(input))
    if (matches.length === 1) {
      setCommand(matches[0] + ' ')
      setShowCompletions(false)
    } else if (matches.length > 1) {
      setTestLogs(prev => [...prev, { type: 'info', data: matches.join('  '), _time: new Date() }])
    }
  }, [command, testLogs])

  const handleKeyDown = useCallback((e) => {
    if (search) {
      if (e.key === 'Escape') {
        setSearch('')
        setSearchMatches([])
      }
      return
    }
    if (e.key === 'Enter') {
      executeCommand()
    } else if (e.key === 'Tab') {
      e.preventDefault()
      handleTabComplete()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (history.length > 0) {
        const newIndex = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1)
        setHistoryIndex(newIndex)
        setCommand(history[newIndex])
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex >= 0) {
        const newIndex = historyIndex + 1
        if (newIndex >= history.length) {
          setHistoryIndex(-1)
          setCommand('')
        } else {
          setHistoryIndex(newIndex)
          setCommand(history[newIndex])
        }
      }
    } else if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault()
      setTestLogs([])
    } else if (e.key === 'k' && e.ctrlKey) {
      e.preventDefault()
      setSearch(p => p ? '' : ' ')
    }
  }, [executeCommand, history, historyIndex, search, handleTabComplete, testLogs])

  const handleResizeStart = useCallback((e) => {
    e.preventDefault()
    setIsResizing(true)
    const startY = e.clientY
    const startH = height
    const onMove = (ev) => {
      const delta = startY - ev.clientY
      setHeight(Math.max(120, Math.min(600, startH + delta)))
    }
    const onUp = () => {
      setIsResizing(false)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }, [height])

  const displayLogs = useMemo(() => {
    if (!search) return testLogs
    if (searchMatches.length === 0) return testLogs
    return testLogs
  }, [testLogs, search, searchMatches])

  if (!showTerminal) return null

  return (
    <div className="terminal-panel" style={{ height }}>
      <div className="terminal-resize-handle" onMouseDown={handleResizeStart} />
      <div className="terminal-header">
        <div className="terminal-title">
          <span className={`terminal-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          <span className="terminal-icon">⬡</span>
          <span>Terminal</span>
          {statusText && <span className="terminal-status">{statusText}</span>}
          {cwd && <span className="terminal-cwd-badge">{cwd}</span>}
        </div>
        <div className="terminal-actions">
          <button className="terminal-btn" onClick={() => setSearch(p => p ? '' : ' ')} title={language === 'zh' ? '搜索 (Ctrl+K)' : 'Search (Ctrl+K)'}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
          </button>
          <button className="terminal-btn" onClick={() => setTestLogs([])} title={language === 'zh' ? '清空 (Ctrl+L)' : 'Clear (Ctrl+L)'}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
          </button>
          <button className="terminal-btn" onClick={() => setShowHelp(!showHelp)} title={language === 'zh' ? '帮助' : 'Help'}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </button>
          <button className="terminal-btn" onClick={() => setShowTerminal(false)} title="Close">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
      </div>

      {search && <SearchBar search={search} setSearch={setSearch} onClose={() => setSearch('')} language={language} />}

      {showHelp && (
        <div className="terminal-help">
          <div className="terminal-help-title">
            {language === 'zh' ? '⌨ 快捷键' : '⌨ Shortcuts'}
          </div>
          <div className="terminal-shortcuts">
            <div className="shortcut-item"><kbd>↑</kbd><kbd>↓</kbd> <span>{language === 'zh' ? '命令历史' : 'History'}</span></div>
            <div className="shortcut-item"><kbd>Tab</kbd> <span>{language === 'zh' ? '自动补全' : 'Auto-complete'}</span></div>
            <div className="shortcut-item"><kbd>Ctrl+K</kbd> <span>{language === 'zh' ? '搜索' : 'Search'}</span></div>
            <div className="shortcut-item"><kbd>Ctrl+L</kbd> <span>{language === 'zh' ? '清空输出' : 'Clear'}</span></div>
            <div className="shortcut-item"><kbd>Esc</kbd> <span>{language === 'zh' ? '关闭搜索' : 'Close search'}</span></div>
          </div>
          <div className="terminal-help-desc">
            {language === 'zh' ? (
              <>连接后端 workspace/，Agent 测试指令输出实时显示在此。危险命令会弹出确认框。</>
            ) : (
              <>Connected to backend workspace/. Agent test outputs stream here. Dangerous commands trigger a confirmation dialog.</>
            )}
          </div>
        </div>
      )}

      <div className="terminal-body" ref={terminalRef} onClick={() => inputRef.current?.focus()} onScroll={handleScroll}>
        {displayLogs.length === 0 && (
          <div className="term-line term-muted-line">
            <span className="term-linenum">   </span>
            <span className="term-time">{formatTime(new Date())}</span>
            <span className="term-content">
              {language === 'zh' ? '⬡  终端就绪。敲命令或等待 Agent 测试结果...' : '⬡  Terminal ready. Type a command or wait for Agent results...'}
            </span>
          </div>
        )}
        {displayLogs.map((log, i) => (
          <div
            key={i}
            ref={el => lineRefs.current[i] = el}
            className={searchMatches.includes(i) ? 'term-line-search-match' : ''}
          >
            <TermLine log={log} index={i} language={language} />
          </div>
        ))}
        {search && searchMatches.length === 0 && displayLogs.length > 0 && (
          <div className="term-line term-muted-line">
            <span className="term-linenum">   </span>
            <span className="term-time">{formatTime(new Date())}</span>
            <span className="term-content hl-error">
              {language === 'zh' ? `无匹配: "${search}"` : `No match: "${search}"`}
            </span>
          </div>
        )}
      </div>

      <div className="terminal-input-area">
        <span className="terminal-prompt-char">{isConnected ? '›' : '○'}</span>
        <input
          ref={inputRef}
          type="text"
          className="terminal-input"
          value={command}
          onChange={e => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={language === 'zh' ? '输入命令 (Tab 补全)...' : 'Type command (Tab to complete)...'}
          disabled={!isConnected}
          spellCheck={false}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
        />
        {history.length > 0 && (
          <span className="term-history-hint">{history.length} {language === 'zh' ? '条历史' : 'history'}</span>
        )}
      </div>
    </div>
  )
}
