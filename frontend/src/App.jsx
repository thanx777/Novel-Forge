import { useState, useEffect, useCallback } from "react"
import "./App.css"
import translations from "./translations"
import { API_BASE } from "./constants"
import usePreset from "./hooks/usePreset"
import useProject from "./hooks/useProject"
import useProjectV2 from "./hooks/useProjectV2"
import Workbench from "./components/Workbench"
import ProjectCenter from "./components/ProjectCenter"
import { PresetPanel } from "./components/Sidebar"
import { ProjectModal, WorkspaceSettings, ConfirmDialog, DangerConfirmModal } from "./components/Modals"

function App() {
  const [language, setLanguage] = useState("zh")
  const [isDark, setIsDark] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [agentCatalog, setAgentCatalog] = useState([])
  const [notification, setNotification] = useState(null)
  const [confirmDialog, setConfirmDialog] = useState(null)
  const [showWorkspaceSettings, setShowWorkspaceSettings] = useState(false)
  const [testLogs, setTestLogs] = useState([])
  const [dangerCommand, setDangerCommand] = useState(null)
  const [depMissing, setDepMissing] = useState(null)
  const [showPresetSidebar, setShowPresetSidebar] = useState(false)

  const t = (key) => translations[language][key] || key

  const showNotification = useCallback((msg, type = "info") => {
    setNotification({ msg, type, id: Date.now() })
    setTimeout(() => setNotification(null), 3500)
  }, [])

  const presetHook = usePreset({ t, showNotification })
  const projectHook = useProject({
    t, showNotification, setConfirmDialog,
    nodes: [], connections: [], conversations: [], memory: "", logs: []
  })
  const projectV2 = useProjectV2({ t, showNotification, presets: presetHook.presets })
  const [currentView, setCurrentView] = useState("project-center")  // project-center | workbench

  // Apply dark theme to document root
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light")
  }, [isDark])

  useEffect(() => {
    fetch(`${API_BASE}/agent-catalog`)
      .then(r => r.json())
      .then(d => setAgentCatalog(d.agents || []))
      .catch(() => {})
  }, [])

  const [workspaceSettings, setWorkspaceSettings] = useState({
    workspace_dir: "", projects_dir: "",
    current_workspace: "", current_projects: "",
    default_workspace: "", default_projects: ""
  })
  const [wsConfigLoading, setWsConfigLoading] = useState(false)

  const fetchWorkspaceConfig = useCallback(async () => {
    setWsConfigLoading(true)
    try {
      const resp = await fetch(`${API_BASE}/workspace-config`)
      if (resp.ok) setWorkspaceSettings(await resp.json())
    } catch (e) { console.error(e) }
    finally { setWsConfigLoading(false) }
  }, [])

  useEffect(() => { fetchWorkspaceConfig() }, [fetchWorkspaceConfig])

  useEffect(() => { presetHook.fetchPresets() }, [presetHook.fetchPresets])

  const handleSaveWorkspaceConfig = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/workspace-config`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(workspaceSettings)
      })
      showNotification(t("settingsSaved"), "success")
    } catch (e) { showNotification("Failed: " + e.message, "error") }
  }, [workspaceSettings, showNotification, t])

  const handleDangerConfirm = useCallback(async (command) => {
    try {
      const resp = await fetch(`${API_BASE}/test/confirm`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: `[TEST:CMD: ${command}]` })
      })
      const result = await resp.json()
      setTestLogs(prev => [...prev,
        { type: "prompt", data: `$ ${command} (force)`, elapsed: 0 },
        { type: result.success ? "done" : "error", data: result.output || result.error, exit_code: result.exit_code, elapsed: result.duration || 0 }
      ])
    } catch (err) {
      setTestLogs(prev => [...prev, { type: "error", data: err.message, elapsed: 0 }])
    }
  }, [])

  const handleDepInstall = useCallback(async (dep) => {
    setDepMissing(null)
    try {
      await fetch(`${API_BASE}/test/dep-install`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module: dep.module, suggestion: dep.suggestion })
      })
      showNotification(`Installed ${dep.module}`, "success")
    } catch (e) { showNotification("Install failed: " + e.message, "error") }
  }, [showNotification])

  const handleDepSkip = useCallback(() => setDepMissing(null), [])

  return (
    <div className="app">

      <div className="workspace-new">
        {/* 视图切换：项目中心 (v2) 与 Workbench (旧的节点流界面) */}
        <div style={{
          position: "absolute", top: 12, right: 20, zIndex: 50,
          display: "flex", gap: 6
        }}>
          <button
            onClick={() => setCurrentView("project-center")}
            className="pc-btn small"
            style={{
              background: currentView === "project-center" ? "var(--accent)" : "var(--bg-surface)",
              color: currentView === "project-center" ? "var(--bg-base)" : "var(--text)",
              borderColor: "var(--border)"
            }}
          >📚 项目中心</button>
          <button
            onClick={() => setCurrentView("workbench")}
            className="pc-btn small"
            style={{
              background: currentView === "workbench" ? "var(--accent)" : "var(--bg-surface)",
              color: currentView === "workbench" ? "var(--bg-base)" : "var(--text)",
              borderColor: "var(--border)"
            }}
          >⚙️ Workbench</button>
        </div>

        {showPresetSidebar && (
          <aside className="preset-sidebar-overlay">
            <div className="preset-sidebar-panel">
              <div className="preset-sidebar-header">
                <span>⚙️ {t("presets")}</span>
                <button className="preset-sidebar-close" onClick={() => setShowPresetSidebar(false)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
              <PresetPanel
                t={t} language={language}
                isDark={isDark}
                presets={presetHook.presets}
                showAddPreset={presetHook.showAddPreset} setShowAddPreset={presetHook.setShowAddPreset}
                newPresetName={presetHook.newPresetName} setNewPresetName={presetHook.setNewPresetName}
                newPresetConfig={presetHook.newPresetConfig} setNewPresetConfig={presetHook.setNewPresetConfig}
                handleAddPreset={presetHook.handleAddPreset}
                handleDeletePreset={presetHook.handleDeletePreset}
                editingPreset={presetHook.editingPreset} setEditingPreset={presetHook.setEditingPreset}
                editPresetConfig={presetHook.editPresetConfig} setEditPresetConfig={presetHook.setEditPresetConfig}
                handleUpdatePreset={presetHook.handleUpdatePreset}
                runTestConnection={presetHook.runTestConnection}
                testConnState={presetHook.testConnState} testConnResult={presetHook.testConnResult}
                selectedNode={null} updateNodeConfig={() => {}}
                openEditPreset={presetHook.openEditPreset}
                showNotification={showNotification}
                setConfirmDialog={setConfirmDialog}
                applyPresetToAll={() => {}}
                allNodes={[]}
              />
            </div>
          </aside>
        )}

        {currentView === "project-center" ? (
          <ProjectCenter
            t={t}
            language={language}
            projectV2={projectV2}
            showNotification={showNotification}
            presets={presetHook.presets}
          />
        ) : (
          <Workbench
            t={t} language={language}
            isDark={isDark} setIsDark={setIsDark}
            setLanguage={setLanguage}
            setShowWorkspaceSettings={setShowWorkspaceSettings}
            setShowPresetSidebar={setShowPresetSidebar}
            showPresetSidebar={showPresetSidebar}
            presets={presetHook.presets}
            showNotification={showNotification}
            isRunning={isRunning} setIsRunning={setIsRunning}
            agentCatalog={agentCatalog}
          />
        )}
      </div>

      <ProjectModal
        t={t} showProjectModal={projectHook.showProjectModal}
        setShowProjectModal={projectHook.setShowProjectModal}
        projectName={projectHook.projectName} setProjectName={projectHook.setProjectName}
        handleSaveProject={projectHook.handleSaveProject}
        projectList={projectHook.projectList}
        handleLoadProject={projectHook.handleLoadProject}
        handleDeleteProject={projectHook.handleDeleteProject}
        setConfirmDialog={setConfirmDialog}
        nodes={[]} connections={[]} conversations={[]} memory="" logs={[]}
      />

      <WorkspaceSettings
        t={t} showWorkspaceSettings={showWorkspaceSettings}
        setShowWorkspaceSettings={setShowWorkspaceSettings}
        workspaceSettings={workspaceSettings} setWorkspaceSettings={setWorkspaceSettings}
        handleSaveWorkspaceConfig={handleSaveWorkspaceConfig}
        wsConfigLoading={wsConfigLoading}
      />

      <ConfirmDialog t={t} confirmDialog={confirmDialog} setConfirmDialog={setConfirmDialog} />
      <DangerConfirmModal t={t} language={language} dangerCommand={dangerCommand} setDangerCommand={setDangerCommand} onConfirm={handleDangerConfirm} />

      {depMissing && (
        <div className="confirm-overlay" onClick={handleDepSkip}>
          <div className="danger-confirm-dialog" onClick={e => e.stopPropagation()} style={{ borderColor: "var(--orange)" }}>
            <div className="danger-confirm-icon">\u26a0\ufe0f</div>
            <div className="danger-confirm-title">{language === "zh" ? "\u73af\u5883\u4f9d\u8d56\u7f3a\u5931" : "Missing Dependency"}</div>
            <div className="danger-confirm-desc">
              {language === "zh"
                ? `Agent \u6d4b\u8bd5\u65f6\u53d1\u73b0\u7f3a\u5c11\u4f9d\u8d56 "${depMissing.module}"\uff0c\u662f\u5426\u5b89\u88c5\uff1f`
                : `Agent detected missing dependency "${depMissing.module}". Install?`}
            </div>
            <div className="danger-confirm-cmd">{depMissing.suggestion}</div>
            <div className="danger-confirm-actions">
              <button className="danger-confirm-reject" onClick={handleDepSkip}>{language === "zh" ? "\u8df3\u8fc7" : "Skip"}</button>
              <button className="danger-confirm-approve" onClick={() => handleDepInstall(depMissing)}>
                {language === "zh" ? `\u5b89\u88c5 ${depMissing.module}` : `Install ${depMissing.module}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {notification && (
        <div className={`notification ${notification.type}`}>{notification.msg}</div>
      )}
    </div>
  )
}

export default App
