import { useState, useCallback } from 'react'
import { API_BASE } from '../constants'

export default function usePreset({ language, showNotification, setNodes }) {
  const [presets, setPresets] = useState([])
  const [showAddPreset, setShowAddPreset] = useState(false)
  const [newPresetName, setNewPresetName] = useState('')
  const [newPresetConfig, setNewPresetConfig] = useState({ api_key: '', base_url: '', model: '', api_format: 'openai', thinking_mode: 'disabled' })
  const [editingPreset, setEditingPreset] = useState(null)
  const [editPresetConfig, setEditPresetConfig] = useState({ api_key: '', base_url: '', model: '', api_format: 'openai', name: '', thinking_mode: 'disabled' })
  const [testConnState, setTestConnState] = useState(null)
  const [testConnResult, setTestConnResult] = useState(null)

  const fetchPresets = useCallback(() => {
    fetch(`${API_BASE}/presets`)
      .then(r => r.json())
      .then(d => setPresets(d.presets || []))
      .catch(err => { console.error('fetchPresets error:', err) })
  }, [])

  const handleAddPreset = useCallback(() => {
    if (!newPresetName.trim()) return
    if (!newPresetConfig.api_key.trim() || !newPresetConfig.model.trim() || !newPresetConfig.base_url.trim()) {
      showNotification(language === 'zh' ? '请填写完整的预设信息' : 'Please fill in all preset fields', 'error')
      return
    }
    fetch(`${API_BASE}/presets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newPresetName.trim(), base_url: newPresetConfig.base_url.trim(),
        model: newPresetConfig.model.trim(), api_key: newPresetConfig.api_key.trim(),
        api_format: newPresetConfig.api_format,
        thinking_mode: newPresetConfig.thinking_mode || 'disabled'
      })
    })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((data) => {
        if (data.presets) setPresets(data.presets)
        else fetchPresets()
        setShowAddPreset(false)
        setNewPresetName('')
        setNewPresetConfig({ api_key: '', base_url: '', model: '', api_format: 'openai', thinking_mode: 'disabled' })
        showNotification(language === 'zh' ? '预设已添加' : 'Preset added', 'success')
      })
      .catch(err => { showNotification(language === 'zh' ? '添加预设失败: ' : 'Add preset failed: ' + err.message, 'error') })
  }, [newPresetName, newPresetConfig, language, showNotification, fetchPresets])

  const handleDeletePreset = useCallback((presetName, t) => {
    return new Promise((resolve) => {
      fetch(`${API_BASE}/presets?name=${encodeURIComponent(presetName)}`, { method: 'DELETE' })
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
        .then((data) => {
          if (data.presets) setPresets(data.presets)
          else fetchPresets()
          setNodes(prev => prev.map(n =>
            n.config.preset_name === presetName ? { ...n, config: { ...n.config, preset_name: '' } } : n
          ))
          if (editingPreset === presetName) setEditingPreset(null)
          showNotification(language === 'zh' ? `预设「${presetName}」已删除` : `Preset "${presetName}" deleted`, 'success')
          resolve()
        })
        .catch(err => { showNotification(language === 'zh' ? '删除预设失败: ' : 'Delete preset failed: ' + err.message, 'error'); resolve() })
    })
  }, [language, showNotification, fetchPresets, editingPreset, setNodes])

  const openEditPreset = useCallback((presetName) => {
    const preset = presets.find(p => p.name === presetName)
    if (!preset) return
    setEditingPreset(presetName)
    setEditPresetConfig({ name: preset.name, api_key: preset.api_key || '', base_url: preset.base_url || '', model: preset.model || '', api_format: preset.api_format || 'openai', chat_template_kwargs: preset.chat_template_kwargs || null, thinking_mode: preset.thinking_mode || 'disabled' })
  }, [presets])

  const handleUpdatePreset = useCallback((t) => {
    if (!editPresetConfig.name.trim() || !editPresetConfig.model.trim() || !editPresetConfig.base_url.trim()) {
      showNotification(language === 'zh' ? '请填写完整信息' : 'Please fill in all fields', 'error')
      return
    }
    fetch(`${API_BASE}/presets`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        original_name: editingPreset, name: editPresetConfig.name.trim(),
        base_url: editPresetConfig.base_url.trim(), model: editPresetConfig.model.trim(),
        api_key: editPresetConfig.api_key.trim(), api_format: editPresetConfig.api_format,
        thinking_mode: editPresetConfig.thinking_mode || null
      })
    })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((data) => {
        if (data.presets) setPresets(data.presets)
        else fetchPresets()
        const oldName = editingPreset, newName = editPresetConfig.name.trim()
        if (oldName !== newName) {
          setNodes(prev => prev.map(n =>
            n.config.preset_name === oldName ? { ...n, config: { ...n.config, preset_name: newName } } : n
          ))
        }
        setEditingPreset(newName)
        showNotification(t('presetUpdated'), 'success')
      })
      .catch(err => { showNotification(language === 'zh' ? '更新预设失败: ' : 'Update preset failed: ' + err.message, 'error') })
  }, [editPresetConfig, editingPreset, language, showNotification, fetchPresets, setNodes])

  const runTestConnection = useCallback(async (config, t) => {
    if (!config || !config.api_key || !config.api_key.trim()) {
      showNotification(t('testConnNoKey'), 'warning')
      return
    }
    setTestConnState('testing')
    setTestConnResult(null)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 50000)

    try {
      const response = await fetch(`${API_BASE}/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: config.api_key,
          base_url: config.base_url,
          model: config.model,
          api_format: config.api_format || 'openai',
          chat_template_kwargs: config.chat_template_kwargs || null,
          thinking_mode: config.thinking_mode || null
        }),
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      const result = await response.json()
      setTestConnState(result.success ? 'success' : 'fail')
      setTestConnResult(result)
      if (result.success) {
        showNotification(`${t('testConnSuccess')} (${result.elapsed_ms}ms)`, 'success')
      } else {
        showNotification(`${t('testConnFail')}: ${result.suggestion || result.message}`, 'error')
      }
    } catch (e) {
      clearTimeout(timeoutId)
      setTestConnState('fail')
      const isTimeout = e.name === 'AbortError'
      setTestConnResult({
        success: false,
        message: isTimeout ? '连接测试超时' : e.message,
        hint: isTimeout ? 'timeout' : 'network_error',
        suggestion: isTimeout ? '后端或 API 服务无响应，请检查网络和 Base URL' : '网络请求失败，请检查后端是否运行'
      })
      showNotification(`${t('testConnFail')}: ${isTimeout ? '连接超时' : e.message}`, 'error')
    }
    setTimeout(() => setTestConnState(null), 5000)
  }, [showNotification])

  const testConnection = useCallback((nodeId, nodes, t) => {
    const node = nodes.find(n => n.id === nodeId)
    if (!node || !node.config.preset_name) return
    const preset = presets.find(p => p.name === node.config.preset_name)
    if (preset) runTestConnection(preset, t)
  }, [presets, runTestConnection])

  const resolveConfig = useCallback((node) => {
    if (!node.config.preset_name) return null
    const p = presets.find(pr => pr.name === node.config.preset_name)
    if (!p) return null
    return { api_key: p.api_key, base_url: p.base_url, model: p.model, api_format: p.api_format || 'openai', chat_template_kwargs: p.chat_template_kwargs || null, thinking_mode: p.thinking_mode || null }
  }, [presets])

  return {
    presets, setPresets, fetchPresets,
    showAddPreset, setShowAddPreset,
    newPresetName, setNewPresetName,
    newPresetConfig, setNewPresetConfig,
    editingPreset, setEditingPreset,
    editPresetConfig, setEditPresetConfig,
    testConnState, testConnResult,
    handleAddPreset, handleDeletePreset, openEditPreset, handleUpdatePreset,
    runTestConnection, testConnection, resolveConfig,
  }
}
