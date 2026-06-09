import { useState, useCallback } from 'react'
import { API_BASE } from '../constants'

export default function useProject({ language, showNotification, setNodes, setConnections, setConversations, setMemory, setLogs, fetchPresets, fetchProjects }) {
  const [showProjectModal, setShowProjectModal] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [projectList, setProjectList] = useState([])

  const _fetchProjects = useCallback(() => {
    fetch(`${API_BASE}/projects`)
      .then(r => r.json())
      .then(d => setProjectList(d.projects || []))
      .catch(() => {})
  }, [])

  const handleSaveProject = useCallback((nodes, connections, conversations, memory, logs, t) => {
    if (!projectName.trim()) {
      showNotification(language === 'zh' ? '请输入项目名称' : 'Please enter project name', 'error')
      return
    }
    fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: projectName.trim(),
        nodes: nodes.map(n => ({ id: n.id, type: n.type, x: n.x, y: n.y, config: n.config, ports: n.ports })),
        connections: connections.map(c => ({ id: c.id, from: c.from, fromPort: c.fromPort, to: c.to, toPort: c.toPort, annotation: c.annotation || '' })),
        conversations: conversations,
        summary: memory,
        preset_names: nodes.map(n => n.config.preset_name).filter(Boolean),
        logs: logs
      })
    })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(() => {
        showNotification(t('projectSaved'), 'success')
        setShowProjectModal(false)
        setProjectName('')
        _fetchProjects()
      })
      .catch(err => { showNotification(language === 'zh' ? '保存失败: ' : 'Save failed: ' + err.message, 'error') })
  }, [projectName, language, showNotification, _fetchProjects])

  const handleLoadProject = useCallback((filename, t) => {
    const NODE_TYPES = {
      manager: { defaultPorts: { inputs: [], outputs: [] } },
      worker: { defaultPorts: { inputs: [], outputs: [] } },
      reviewer: { defaultPorts: { inputs: [], outputs: [] } },
    }
    fetch(`${API_BASE}/projects/${filename}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(data => {
        const loadedNodes = (data.nodes || []).map(n => ({
          ...n,
          ports: n.ports || NODE_TYPES[n.type]?.defaultPorts || { inputs: [], outputs: [] },
          config: { preset_name: '', agent_role: '', custom_prompt: '', ...n.config },
          activity: n.activity || 'idle',
          thought: n.thought || '',
          response: n.response || '',
          history: n.history || []
        }))
        if (loadedNodes.length > 0) setNodes(loadedNodes)
        if (data.connections) setConnections(data.connections.map(c => ({ ...c, annotation: c.annotation || '' })))
        if (data.conversations) setConversations(data.conversations)
        if (data.summary) setMemory(data.summary)
        if (data.logs) setLogs(data.logs)
        showNotification(t('projectLoaded'), 'success')
        setShowProjectModal(false)
        _fetchProjects()
      })
      .catch(err => { showNotification(language === 'zh' ? '加载失败: ' : 'Load failed: ' + err.message, 'error') })
  }, [language, showNotification, setNodes, setConnections, setConversations, setMemory, setLogs, _fetchProjects])

  const handleDeleteProject = useCallback((filename, t) => {
    fetch(`${API_BASE}/projects/${filename}`, { method: 'DELETE' })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(() => { showNotification(t('projectDeleted'), 'success'); _fetchProjects() })
      .catch(err => { showNotification(language === 'zh' ? '删除失败: ' : 'Delete failed: ' + err.message, 'error') })
  }, [language, showNotification, _fetchProjects])

  return {
    showProjectModal, setShowProjectModal,
    projectName, setProjectName,
    projectList, setProjectList,
    fetchProjects: _fetchProjects,
    handleSaveProject, handleLoadProject, handleDeleteProject,
  }
}
