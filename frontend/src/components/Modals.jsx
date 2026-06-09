import { useState } from 'react'
import { API_BASE } from '../constants'

export function LogsPanel({ t, logs, setLogs, logEndRef, setShowLogs }) {
  const [expandedLogs, setExpandedLogs] = useState({})
  const toggleLog = (i) => {
    setExpandedLogs(prev => ({ ...prev, [i]: !prev[i] }))
  }
  return (
    <div className="panel logs-panel">
      <div className="panel-header">
        <span>{t('logs')}</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={() => { setLogs([]); setExpandedLogs({}) }} title={t('clearLogs')}><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg></button>
          <button onClick={() => setShowLogs(false)}><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
        </div>
      </div>
      <div className="panel-body logs-body">
        {logs.length === 0 && <div className="panel-empty">-</div>}
        {logs.map((log, i) => {
          const isTest = log.message && (log.message.includes('🧪') || log.message.includes('测试'))
          const isTestResult = log.message && (log.message.includes('✅') && log.message.includes('测试完成'))
          const isTestFail = log.message && (log.message.includes('❌') && log.message.includes('测试'))
          let logClass = `log-line log-${log.status}`
          if (isTestFail) logClass += ' log-test-fail'
          else if (isTestResult) logClass += ' log-test-success'
          else if (isTest) logClass += ' log-test'
          const isLong = log.message && log.message.length > 200
          const isExpanded = expandedLogs[i]
          return (
            <div key={i} className={logClass + (isLong ? ' log-collapsible' : '')} onClick={isLong ? () => toggleLog(i) : undefined}>
              <span className="log-role">{log.role}</span>
              {log.model && <span className="log-model-badge" title={log.preset || ''}>{log.model}</span>}
              <span className={'log-msg' + (isLong && !isExpanded ? ' log-msg-collapsed' : '')}>{log.message}</span>
              {isLong && <span className="log-expand-icon">{isExpanded ? '▲' : '▼'}</span>}
            </div>
          )
        })}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}

export function FilesPanel({ t, files, activeFile, setActiveFile, fileContent, setFileContent, loadFiles, loadFile, saveFile, showNotification, setShowFiles }) {
  return (
    <div className="panel files-panel">
      <div className="panel-header">
        <span>{t('files')}</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={loadFiles}><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" /></svg></button>
          <button onClick={() => setShowFiles(false)}><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
        </div>
      </div>
      <div className="panel-body files-body">
        {files.length === 0 && <div className="panel-empty">-</div>}
        {files.map(f => (
          <div key={f} className={`file-item ${activeFile === f ? 'active' : ''}`} onClick={() => loadFile(f)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" /></svg>
            <span>{f}</span>
          </div>
        ))}
        {activeFile && (
          <div className="file-preview-area">
            <div className="file-preview-header"><span>{activeFile}</span><button onClick={saveFile}>{t('saved')}</button></div>
            <pre className="file-preview-content">{fileContent}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

export function ProjectModal({ t, showProjectModal, setShowProjectModal, projectName, setProjectName, handleSaveProject, projectList, handleLoadProject, handleDeleteProject, setConfirmDialog, nodes, connections, conversations, memory, logs }) {
  if (!showProjectModal) return null
  return (
    <div className="confirm-overlay" onClick={() => setShowProjectModal(false)}>
      <div className="confirm-dialog project-modal" onClick={e => e.stopPropagation()}>
        <div className="project-modal-header">
          <span>{showProjectModal === 'save' ? t('saveProject') : t('loadProject')}</span>
          <button className="preset-edit-close" onClick={() => setShowProjectModal(false)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="project-modal-body">
          {showProjectModal === 'save' ? (
            <div className="project-save-form">
              <div className="config-field"><label>{t('projectName')}</label><input value={projectName} onChange={e => setProjectName(e.target.value)} placeholder={t('projectName')} onKeyDown={e => { if (e.key === 'Enter') handleSaveProject(nodes, connections, conversations, memory, logs, t) }} /></div>
              <div className="project-save-hint">{t('saveProjectHint')}</div>
              <button className="preset-edit-save-btn" style={{ width: '100%' }} onClick={() => handleSaveProject(nodes, connections, conversations, memory, logs, t)}>{t('saveProject')}</button>
            </div>
          ) : (
            <div className="project-list">
              {projectList.length === 0 && <div className="panel-empty">{t('noProjects')}</div>}
              {projectList.map((proj, i) => (
                <div key={i} className="project-item">
                  <div className="project-info" onClick={() => handleLoadProject(proj.filename, t)}>
                    <div className="project-name">{proj.name}</div>
                    <div className="project-meta">{proj.updated || proj.created}</div>
                  </div>
                  <button className="project-delete-btn" onClick={() => setConfirmDialog({ message: t('confirmDeletePreset'), onConfirm: () => { handleDeleteProject(proj.filename, t); setConfirmDialog(null) }, onCancel: () => setConfirmDialog(null) })}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function WorkspaceSettings({ t, showWorkspaceSettings, setShowWorkspaceSettings, workspaceSettings, setWorkspaceSettings, handleSaveWorkspaceConfig, wsConfigLoading }) {
  if (!showWorkspaceSettings) return null
  return (
    <div className="confirm-overlay" onClick={() => setShowWorkspaceSettings(false)}>
      <div className="confirm-dialog project-modal" onClick={e => e.stopPropagation()}>
        <div className="project-modal-header">
          <span>{t('pathSettings')}</span>
          <button className="preset-edit-close" onClick={() => setShowWorkspaceSettings(false)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="project-modal-body">
          <div className="config-field">
            <label>{t('workspacePath')}</label>
            <input
              value={workspaceSettings.workspace_dir}
              onChange={e => setWorkspaceSettings(prev => ({ ...prev, workspace_dir: e.target.value }))}
              placeholder={workspaceSettings.default_workspace || ''}
            />
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
              {t('currentPath')}: {workspaceSettings.current_workspace || workspaceSettings.default_workspace || t('defaultPath')}
            </div>
          </div>
          <div className="config-field">
            <label>{t('projectsPath')}</label>
            <input
              value={workspaceSettings.projects_dir}
              onChange={e => setWorkspaceSettings(prev => ({ ...prev, projects_dir: e.target.value }))}
              placeholder={workspaceSettings.default_projects || ''}
            />
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
              {t('currentPath')}: {workspaceSettings.current_projects || workspaceSettings.default_projects || t('defaultPath')}
            </div>
          </div>
          <button
            className="preset-edit-save-btn"
            style={{ width: '100%', marginTop: '8px' }}
            onClick={handleSaveWorkspaceConfig}
            disabled={wsConfigLoading}
          >
            {wsConfigLoading ? t('testing') : t('savePreset')}
          </button>
        </div>
      </div>
    </div>
  )
}

export function ConnContextMenu({ t, connContextMenu, setConnContextMenu, connections, setAnnotationText, setEditingAnnotation, setConnections, setSelectedConn }) {
  if (!connContextMenu) return null
  return (
    <div className="conn-context-menu" style={{ position: 'fixed', left: connContextMenu.x, top: connContextMenu.y, zIndex: 10001 }}>
      <button className="conn-menu-item" onClick={() => {
        const conn = connections.find(c => c.id === connContextMenu.connId)
        if (conn) {
          setAnnotationText(conn.annotation || '')
          setEditingAnnotation(connContextMenu.connId)
        }
        setConnContextMenu(null)
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
        {t('annotation')}
      </button>
      <button className="conn-menu-item conn-menu-danger" onClick={() => {
        setConnections(prev => prev.filter(c => c.id !== connContextMenu.connId))
        setSelectedConn(null)
        setConnContextMenu(null)
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
        {t('deleteConnection')}
      </button>
    </div>
  )
}

export function AnnotationEditor({ t, editingAnnotation, setEditingAnnotation, annotationText, setAnnotationText, updateConnAnnotation }) {
  if (!editingAnnotation) return null
  return (
    <div className="confirm-overlay" onClick={() => setEditingAnnotation(null)}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()} style={{ width: '320px' }}>
        <div className="confirm-message">{t('editAnnotation')}</div>
        <input
          type="text"
          value={annotationText}
          onChange={e => setAnnotationText(e.target.value)}
          placeholder={t('annotationHint')}
          style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text)', fontSize: '13px', boxSizing: 'border-box', marginTop: '8px' }}
          onKeyDown={e => { if (e.key === 'Enter') { updateConnAnnotation(editingAnnotation, annotationText); setEditingAnnotation(null) } }}
          autoFocus
        />
        <div className="confirm-actions" style={{ marginTop: '12px' }}>
          <button className="confirm-cancel" onClick={() => setEditingAnnotation(null)}>{t('cancel')}</button>
          <button className="confirm-ok" onClick={() => { updateConnAnnotation(editingAnnotation, annotationText); setEditingAnnotation(null) }}>{t('confirm')}</button>
        </div>
      </div>
    </div>
  )
}


export function ConfirmDialog({ t, confirmDialog, setConfirmDialog }) {
  if (!confirmDialog) return null
  return (
    <div className="confirm-overlay" onClick={() => setConfirmDialog(null)}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
        <div className="confirm-icon-wrapper">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>
        <div className="confirm-message">{confirmDialog.message}</div>
        <div className="confirm-actions">
          <button className="confirm-cancel" onClick={confirmDialog.onCancel}>{t('cancel')}</button>
          <button className="confirm-ok" onClick={confirmDialog.onConfirm}>{t('confirm')}</button>
        </div>
      </div>
    </div>
  )
}

export function DangerConfirmModal({ t, language, dangerCommand, setDangerCommand, onConfirm }) {
  if (!dangerCommand) return null
  return (
    <div className="confirm-overlay" onClick={() => setDangerCommand(null)}>
      <div className="danger-confirm-dialog" onClick={e => e.stopPropagation()}>
        <div className="danger-confirm-icon">⚠️</div>
        <div className="danger-confirm-title">{language === 'zh' ? '危险命令确认' : 'Dangerous Command'}</div>
        <div className="danger-confirm-desc">{language === 'zh' ? 'Agent 请求执行以下命令，该命令可能造成不可逆操作：' : 'Agent requested to execute the following command, which may cause irreversible changes:'}</div>
        <div className="danger-confirm-cmd">{dangerCommand}</div>
        <div className="danger-confirm-actions">
          <button className="danger-confirm-reject" onClick={() => setDangerCommand(null)}>{language === 'zh' ? '拒绝执行' : 'Reject'}</button>
          <button className="danger-confirm-approve" onClick={() => { onConfirm(dangerCommand); setDangerCommand(null) }}>{language === 'zh' ? '确认执行' : 'Execute'}</button>
        </div>
      </div>
    </div>
  )
}
