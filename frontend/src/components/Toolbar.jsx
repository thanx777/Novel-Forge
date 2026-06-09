export default function Toolbar({ t, language, isDark, isRunning, elapsed, executionMode, setExecutionMode, setPan, setShowProjectModal, fetchProjects, setShowWorkspaceSettings, fetchWorkspaceConfig, showLogs, setShowLogs, showFiles, setShowFiles, showTerminal, setShowTerminal, setLanguage, setIsDark, resetNovelCanvas }) {
  const formatTime = (s) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <header className="toolbar">
      <div className="toolbar-left">
        <div className="toolbar-brand">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            <line x1="8" y1="7" x2="16" y2="7"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
          <span>{language === 'zh' ? '小说锻造' : 'Novel Forge'}</span>
        </div>
        <div className="toolbar-divider" />
        {resetNovelCanvas && (
          <button className="toolbar-btn" onClick={() => resetNovelCanvas(executionMode)} title="重置为默认小说流水线拓扑">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            重置画布
          </button>
        )}
        <button className="toolbar-btn" onClick={() => setPan({ x: 0, y: 0 })} title="Reset View">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4" /></svg>
          Reset
        </button>
      </div>
      <div className="toolbar-right">
        <button className="toolbar-btn" onClick={() => { fetchProjects(); setShowProjectModal('save') }} title={t('saveProject')}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></svg>
          {t('saveProject')}
        </button>
        <button className="toolbar-btn" onClick={() => { fetchProjects(); setShowProjectModal('load') }} title={t('loadProject')}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>
          {t('projects')}
        </button>
        <div className="toolbar-divider" />
        <button className="toolbar-btn" onClick={() => { fetchWorkspaceConfig(); setShowWorkspaceSettings(true) }} title={t('settings')}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
          {t('settings')}
        </button>
        <button className={`toolbar-btn ${showLogs ? 'active' : ''}`} onClick={() => setShowLogs(!showLogs)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" /></svg>
          {t('logs')}
        </button>
        <button className={`toolbar-btn ${showFiles ? 'active' : ''}`} onClick={() => setShowFiles(!showFiles)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>
          {t('files')}
        </button>
        <button className={`toolbar-btn ${showTerminal ? 'active' : ''}`} onClick={() => setShowTerminal(!showTerminal)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" /></svg>
          {t('terminal')}
        </button>
        {isRunning && (
          <div className="toolbar-status">
            <span className="spinner" />
            <span>{formatTime(elapsed)}</span>
          </div>
        )}
        <div className="mode-segmented">
          <button className={`mode-seg ${executionMode === 'compatible' ? 'active' : ''}`} onClick={() => { setExecutionMode('compatible'); resetNovelCanvas('compatible') }} title={language === 'zh' ? '兼容版：润色循环+详细提示词，适合低级模型' : 'Compatible: polish cycle + detailed prompts for low-tier models'}>
            {language === 'zh' ? '兼容' : 'CMP'}
          </button>
          <button className={`mode-seg ${executionMode === 'standard' ? 'active' : ''}`} onClick={() => { setExecutionMode('standard'); resetNovelCanvas('standard') }} title={language === 'zh' ? '标准版：精简提示词，适合主流模型' : 'Standard: concise prompts for mainstream models'}>
            {language === 'zh' ? '标准' : 'STD'}
          </button>
          <button className={`mode-seg ${executionMode === 'full' ? 'active' : ''}`} onClick={() => { setExecutionMode('full'); resetNovelCanvas('full') }} title={language === 'zh' ? '完整版：润色循环+详尽提示词，适合高级模型' : 'Full: polish cycle + verbose prompts for advanced models'}>
            {language === 'zh' ? '完整' : 'FULL'}
          </button>
        </div>
        <button className="toolbar-btn lang-toggle" onClick={() => setLanguage(l => l === 'en' ? 'zh' : 'en')}>
          {language === 'en' ? '中文' : 'EN'}
        </button>
        <button className="toolbar-btn theme-toggle" onClick={() => setIsDark(!isDark)}>
          {isDark ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5" /><path d="M12 1v2m0 18v2M21 12h2M1 12h2m16.95-6.95l1.414 1.414M2.636 21.364l1.414-1.414M4.636 4.636l1.414 1.414M17.95 19.364l1.414-1.414" /></svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" /></svg>
          )}
        </button>
      </div>
    </header>
  )
}
