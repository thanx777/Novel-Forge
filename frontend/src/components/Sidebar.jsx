import { useState } from 'react'
import { API_FORMATS } from '../constants'
import TestResultCard from './TestResultCard'

export function PresetPanel({ t, language, presets, showAddPreset, setShowAddPreset, newPresetName, setNewPresetName, newPresetConfig, setNewPresetConfig, handleAddPreset, handleDeletePreset, editingPreset, setEditingPreset, editPresetConfig, setEditPresetConfig, handleUpdatePreset, runTestConnection, testConnState, testConnResult, selectedNode, updateNodeConfig, openEditPreset, showNotification, setConfirmDialog, applyPresetToAll, allNodes }) {
  return (
    <div className="sidebar-section preset-section">
      <div className="sidebar-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{t('presets')}</span>
        <button className="preset-add-btn" onClick={() => { setShowAddPreset(true); setNewPresetName('') }} title={t('addPreset')}>+</button>
      </div>
      {showAddPreset && (
        <div style={{ padding: '6px 0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <input type="text" value={newPresetName} onChange={e => setNewPresetName(e.target.value)} placeholder={t('presetName')}
            style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text)', fontSize: '12px', boxSizing: 'border-box' }}
            onKeyDown={e => { if (e.key === 'Enter') handleAddPreset() }} />
          <div className="format-selector" style={{ gap: '4px' }}>
            {Object.entries(API_FORMATS).map(([key, format]) => (
              <div key={key} className={`format-option ${newPresetConfig.api_format === key ? 'active' : ''}`} onClick={() => setNewPresetConfig(prev => ({ ...prev, api_format: key }))} style={{ padding: '4px 6px', fontSize: '10px' }}>
                <div className="format-name" style={{ fontSize: '11px' }}>{t(key === 'openai' ? 'openaiCompatible' : 'anthropicClaude')}</div>
              </div>
            ))}
          </div>
          <input type="password" value={newPresetConfig.api_key} onChange={e => setNewPresetConfig(prev => ({ ...prev, api_key: e.target.value }))} placeholder={t('apiKey')}
            style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text)', fontSize: '12px', boxSizing: 'border-box' }} />
          <input value={newPresetConfig.model} onChange={e => setNewPresetConfig(prev => ({ ...prev, model: e.target.value }))} placeholder={t('model')}
            style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text)', fontSize: '12px', boxSizing: 'border-box' }} />
          {newPresetConfig.api_format && API_FORMATS[newPresetConfig.api_format] && (
            <div className="model-examples" style={{ flexWrap: 'wrap', gap: '3px' }}>
              {API_FORMATS[newPresetConfig.api_format].modelExamples.map((m, i) => (
                <span key={i} className="example-tag" style={{ fontSize: '10px' }} onClick={() => setNewPresetConfig(prev => ({ ...prev, model: m }))}>{m}</span>
              ))}
            </div>
          )}
          <input value={newPresetConfig.base_url} onChange={e => setNewPresetConfig(prev => ({ ...prev, base_url: e.target.value }))} placeholder={t('baseUrl')}
            style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text)', fontSize: '12px', boxSizing: 'border-box' }} />
          {(newPresetConfig.base_url.includes('deepseek') || newPresetConfig.model.includes('deepseek')) && (
            <div className="config-field" style={{ margin: 0 }}>
              <label style={{ fontSize: '11px' }}>{t('thinkingMode')}</label>
              <div className="format-selector" style={{ gap: '4px' }}>
                {[{ key: 'disabled', label: t('thinkingOff') }, { key: 'enabled', label: t('thinkingOn') }].map(opt => (
                  <div key={opt.key} className={`format-option ${(newPresetConfig.thinking_mode || 'disabled') === opt.key ? 'active' : ''}`}
                    onClick={() => setNewPresetConfig(prev => ({ ...prev, thinking_mode: opt.key }))}
                    style={{ padding: '4px 8px', fontSize: '10px', flex: 1, textAlign: 'center' }}>
                    {opt.label}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div style={{ display: 'flex', gap: '4px' }}>
            <button onClick={handleAddPreset} style={{ flex: 1, padding: '4px', borderRadius: '4px', border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: '12px' }}>{t('savePreset')}</button>
            <button onClick={() => { setShowAddPreset(false); setNewPresetName(''); setNewPresetConfig({ api_key: '', base_url: '', model: '', api_format: 'openai', thinking_mode: 'disabled' }) }} style={{ flex: 1, padding: '4px', borderRadius: '4px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer', fontSize: '12px' }}>{t('close')}</button>
          </div>
        </div>
      )}
      {presets.map((preset, i) => (
        <div key={i} className="model-card" onClick={() => { if (selectedNode) updateNodeConfig(selectedNode, { preset_name: preset.name }); openEditPreset(preset.name) }}>
          <div className="model-dot" style={{ background: '#58a6ff' }} />
          <div className="model-info">
            <div className="model-name">{preset.name}</div>
            <div className="model-id">{preset.model}</div>
          </div>
          {allNodes && allNodes.length > 0 && (
            <button className="preset-apply-all-btn"
              onClick={(e) => { e.stopPropagation(); applyPresetToAll(preset.name); showNotification(`已应用 "${preset.name}" 到全部 ${allNodes.length} 个节点`, 'success') }}
              title="一键应用到所有节点">
              全部
            </button>
          )}
          <button className="preset-delete-btn"
            onClick={(e) => { e.stopPropagation(); setConfirmDialog({ message: t('confirmDeletePreset'), onConfirm: async () => { await handleDeletePreset(preset.name); setConfirmDialog(null) }, onCancel: () => setConfirmDialog(null) }) }}
            title={t('deletePreset')}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
          </button>
        </div>
      ))}
      {editingPreset && (() => {
        const p = presets.find(pr => pr.name === editingPreset)
        if (!p) return null
        return (
          <div className="preset-edit-panel">
            <div className="preset-edit-header">
              <span className="preset-edit-title">{t('editPreset')}</span>
              <button className="preset-edit-close" onClick={() => setEditingPreset(null)}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="preset-edit-body">
              <div className="config-field"><label>{t('presetName')}</label><input value={editPresetConfig.name} onChange={e => setEditPresetConfig(prev => ({ ...prev, name: e.target.value }))} /></div>
              <div className="config-field">
                <label>{t('apiFormat')}</label>
                <div className="format-selector" style={{ gap: '4px' }}>
                  {Object.entries(API_FORMATS).map(([key]) => (
                    <div key={key} className={`format-option ${editPresetConfig.api_format === key ? 'active' : ''}`} onClick={() => setEditPresetConfig(prev => ({ ...prev, api_format: key }))} style={{ padding: '4px 6px', fontSize: '10px' }}>
                      <div className="format-name" style={{ fontSize: '11px' }}>{t(key === 'openai' ? 'openaiCompatible' : 'anthropicClaude')}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="config-field"><label>{t('apiKey')}</label><input type="password" value={editPresetConfig.api_key} onChange={e => setEditPresetConfig(prev => ({ ...prev, api_key: e.target.value }))} placeholder={t('apiKeyHint')} /></div>
              <div className="config-field">
                <label>{t('model')}</label>
                <input value={editPresetConfig.model} onChange={e => setEditPresetConfig(prev => ({ ...prev, model: e.target.value }))} placeholder={t('modelHint')} />
                {editPresetConfig.api_format && API_FORMATS[editPresetConfig.api_format] && (
                  <div className="model-examples" style={{ flexWrap: 'wrap', gap: '3px' }}>
                    {API_FORMATS[editPresetConfig.api_format].modelExamples.map((m, mi) => (
                      <span key={mi} className="example-tag" style={{ fontSize: '10px' }} onClick={() => setEditPresetConfig(prev => ({ ...prev, model: m }))}>{m}</span>
                    ))}
                  </div>
                )}
              </div>
              <div className="config-field">
                <label>{t('baseUrl')}</label>
                <input value={editPresetConfig.base_url} onChange={e => setEditPresetConfig(prev => ({ ...prev, base_url: e.target.value }))} placeholder={t('baseUrlHint')} />
                {editPresetConfig.api_format && API_FORMATS[editPresetConfig.api_format] && (
                  <div className="url-example" style={{ fontSize: '10px' }}><span className="example-label">{t('urlExample')}:</span><code>{API_FORMATS[editPresetConfig.api_format].baseUrlExample}</code></div>
                )}
              </div>
              {(editPresetConfig.base_url.includes('deepseek') || editPresetConfig.model.includes('deepseek')) && (
                <div className="config-field">
                  <label>{t('thinkingMode')}</label>
                  <div className="format-selector" style={{ gap: '4px' }}>
                    {[{ key: 'disabled', label: t('thinkingOff') }, { key: 'enabled', label: t('thinkingOn') }].map(opt => (
                      <div key={opt.key} className={`format-option ${(editPresetConfig.thinking_mode || 'disabled') === opt.key ? 'active' : ''}`}
                        onClick={() => setEditPresetConfig(prev => ({ ...prev, thinking_mode: opt.key }))}
                        style={{ padding: '4px 8px', fontSize: '10px', flex: 1, textAlign: 'center' }}>
                        {opt.label}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
                <button className="config-test-btn" style={{ flex: 1 }} onClick={() => runTestConnection(editPresetConfig, t)} disabled={testConnState === 'testing'}>
                  {testConnState === 'testing' ? t('testConnTesting') : t('testConnection')}
                </button>
                <button className="preset-edit-save-btn" style={{ flex: 1 }} onClick={() => handleUpdatePreset(t)}>{t('updatePreset')}</button>
              </div>
              <div style={{ marginTop: '6px' }}>
                <button className="ai-config-btn" onClick={() => {
                  const prompt = `${t('aiConfigPrompt')}\n\n---\n${t('name')}: [${t('fillName')}]\nAPI Key: [${t('fillKey')}]\nBase URL: [${t('fillUrl')}]\n${t('model')}: [${t('fillModel')}]\nAPI ${t('format')}: ${editPresetConfig.api_format || 'openai'}\n---\n\n${t('aiConfigHelp')}`
                  navigator.clipboard.writeText(prompt).then(() => showNotification(t('aiConfigCopied'), 'info'))
                }}>{t('aiConfig')}</button>
              </div>
              {testConnResult && (
                <TestResultCard result={testConnResult} onRetry={() => runTestConnection(editPresetConfig, t)} />
              )}
            </div>
          </div>
        )
      })()}
      {presets.length === 0 && !showAddPreset && <div className="sidebar-empty">-</div>}
    </div>
  )
}

export function ChatPanel({ t, language, conversations, dialogEndRef, memory, setMemory, showNotification, taskInput, setTaskInput, chapterCount, setChapterCount, isRunning, runTask, handleStop, sendFeedback, optimizing, showOptimizeDropdown, setShowOptimizeDropdown, handleOptimize, presets }) {
  return (
    <div className="sidebar-section dialog-section">
      <div className="sidebar-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{t('task')}</span>
        <input
          type="number"
          className="chapter-input"
          value={chapterCount}
          onChange={e => setChapterCount(e.target.value)}
          placeholder={language === 'zh' ? '章数' : 'Ch'}
          disabled={isRunning}
          min="1"
        />
      </div>
      {memory && (
        <div className="memory-box">
          <div className="memory-header">
            <span className="memory-title">{t('memory')}</span>
            <button className="memory-clear-btn" onClick={() => { setMemory(''); showNotification(t('memoryCleared'), 'info') }}>{t('clearMemory')}</button>
          </div>
          <div className="memory-content">{memory}</div>
        </div>
      )}
      <div className="dialog-messages">
        {conversations.length === 0 && (
          <div className="dialog-empty">{t('clickNodeTip')}</div>
        )}
        {conversations.map((msg, i) => (
          <div key={i} className={`dialog-msg dialog-${msg.role}`}>
            <div className="dialog-msg-role">{msg.role === 'user' ? t('task') : 'Manager'}</div>
            <div className="dialog-msg-content">{msg.content}</div>
          </div>
        ))}
        <div ref={dialogEndRef} />
      </div>
      <div className="dialog-input-area">
        <textarea
          className="dialog-input"
          value={taskInput}
          onChange={e => setTaskInput(e.target.value)}
          placeholder={isRunning ? (language === 'zh' ? '输入反馈...' : 'Feedback...') : t('enterTask')}
          disabled={!isRunning && false}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              if (isRunning) {
                if (taskInput.trim()) { sendFeedback(taskInput).then(ok => { if (ok) setTaskInput('') }) }
              } else {
                runTask(t)
              }
            }
          }}
        />
        <div style={{ display: 'flex', gap: '6px' }}>
          {isRunning && (
            <button
              className="dialog-send-btn"
              onClick={() => { if (taskInput.trim()) sendFeedback(taskInput).then(ok => { if (ok) setTaskInput('') }) }}
              disabled={!taskInput.trim()}
              style={{ flex: 1, background: 'var(--accent-dim)', fontSize: '12px' }}
              title={language === 'zh' ? '发送反馈给 Manager' : 'Send feedback to Manager'}
            >
              💬 {language === 'zh' ? '反馈' : 'Send'}
            </button>
          )}
          <button
            className={`dialog-send-btn ${isRunning ? 'dialog-stop-btn' : ''}`}
            onClick={isRunning ? handleStop : () => runTask(t)}
            disabled={!isRunning && !taskInput.trim()}
            style={isRunning ? {} : { flex: 1 }}
          >
            {isRunning ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
            )}
          </button>
        </div>
        {!isRunning && (
        <div className="optimize-btn-wrapper">
          <button className="dialog-send-btn optimize-btn" onClick={(e) => { e.stopPropagation(); setShowOptimizeDropdown(!showOptimizeDropdown) }} disabled={!taskInput.trim() || optimizing} title={t('optimizePrompt')}>
            {optimizing ? <span className="spinner" /> : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
            )}
          </button>
          {showOptimizeDropdown && (
            <div className="optimize-dropdown" onClick={e => e.stopPropagation()}>
              <div className="optimize-dropdown-header">{t('selectPresetToOptimize')}</div>
              {presets.filter(p => p.api_key).map(p => (
                <div key={p.name} className="optimize-dropdown-item" onClick={() => handleOptimize(p, t)}>
                  {p.name}
                </div>
              ))}
              {presets.filter(p => p.api_key).length === 0 && (
                <div className="optimize-dropdown-empty">{t('noPresets')}</div>
              )}
            </div>
          )}
        </div>
        )}
      </div>
    </div>
  )
}

export function TaskPanel({ t, language, tasks, onResume, onDelete, onRefresh, isRunning }) {
  const [expanded, setExpanded] = useState(false)
  const statusLabels = { completed: language === 'zh' ? '已完成' : 'Done', in_progress: language === 'zh' ? '已中断' : 'Paused', unknown: language === 'zh' ? '未知' : 'Unknown' }

  return (
    <div className="sidebar-section">
      <div className="task-section-header sidebar-title"
        onClick={() => { if (!expanded) onRefresh(); setExpanded(!expanded) }}>
        <span>{language === 'zh' ? '任务' : 'Tasks'} ({tasks.length})</span>
        <button className="task-refresh-btn" onClick={(e) => { e.stopPropagation(); onRefresh() }} title={t('refresh')}>↻</button>
      </div>
      {expanded && (
        <div className="task-list">
          {tasks.length === 0 && (
            <div className="sidebar-empty">
              {language === 'zh' ? '暂无中断任务' : 'No paused tasks'}
            </div>
          )}
          {tasks.map((task) => {
            const pct = task.total_chapters > 0 ? Math.round(task.chapters_done / task.total_chapters * 100) : 0
            return (
              <div key={task.folder} className="task-item">
                <div className="task-item-title">{task.task}</div>
                <div className="task-item-progress-row">
                  <div className="task-item-bar">
                    <div className={`task-item-bar-fill ${task.status || 'unknown'}`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="task-item-count">
                    {task.chapters_done}{task.total_chapters > 0 ? `/${task.total_chapters}` : ''}
                  </span>
                </div>
                <div className="task-item-footer">
                  <span className="task-item-status" style={{ color: task.status === 'in_progress' ? 'var(--amber)' : 'var(--accent)' }}>
                    {statusLabels[task.status] || task.status}
                  </span>
                  <div className="task-item-actions">
                    {task.status === 'in_progress' && (
                      <button className="task-btn-resume" onClick={() => onResume(task.folder)} disabled={isRunning}>
                        {language === 'zh' ? '继续' : 'Resume'}
                      </button>
                    )}
                    <button className="task-btn-delete" onClick={() => onDelete(task.folder)} disabled={isRunning}>
                      {language === 'zh' ? '删除' : 'Del'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
