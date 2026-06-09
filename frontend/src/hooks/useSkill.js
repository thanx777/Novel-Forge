import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '../constants'

export default function useSkill({ showNotification }) {
  const [skills, setSkills] = useState([])
  const [selectedSkills, setSelectedSkills] = useState([])
  const [activeSkillCount, setActiveSkillCount] = useState(0)
  const [showSkillPanel, setShowSkillPanel] = useState(false)
  const [showSkillManager, setShowSkillManager] = useState(false)
  const [skillSearch, setSkillSearch] = useState('')
  const [creatingSkill, setCreatingSkill] = useState(false)
  const [newSkill, setNewSkill] = useState({ name: '', description: '', category: 'custom' })
  const [editingSkillName, setEditingSkillName] = useState(null)
  const [editSkillContent, setEditSkillContent] = useState('')
  const [skillGenPreset, setSkillGenPreset] = useState(null)

  const fetchSkills = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/skills`)
      const data = await r.json()
      if (data.skills) setSkills(data.skills)
    } catch { /* silent */ }
  }, [])

  useEffect(() => { fetchSkills() }, [fetchSkills])

  const toggleSkill = useCallback((skillName) => {
    setSelectedSkills(prev =>
      prev.includes(skillName) ? prev.filter(s => s !== skillName) : [...prev, skillName]
    )
  }, [])

  const handleCreateSkill = useCallback(async (t) => {
    if (!newSkill.name.trim()) return
    const body = {
      name: newSkill.name.trim(),
      description: newSkill.description.trim(),
      category: newSkill.category,
      user_prompt: ''
    }
    if (skillGenPreset) {
      body.preset = {
        api_key: skillGenPreset.api_key, base_url: skillGenPreset.base_url,
        model: skillGenPreset.model, api_format: skillGenPreset.api_format || 'openai',
        chat_template_kwargs: skillGenPreset.chat_template_kwargs || null
      }
      body.user_prompt = newSkill.description.trim() || `Create a skill for: ${newSkill.name}`
    }
    try {
      const r = await fetch(`${API_BASE}/skills/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      })
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail) }
      showNotification(t('skillCreated'), 'success')
      setCreatingSkill(false)
      setNewSkill({ name: '', description: '', category: 'custom' })
      setSkillGenPreset(null)
      fetchSkills()
    } catch (err) { showNotification(t('optimizeFailed') + ': ' + err.message, 'error') }
  }, [newSkill, skillGenPreset, showNotification, fetchSkills])

  const handleDeleteSkill = useCallback(async (skillName, t) => {
    try {
      await fetch(`${API_BASE}/skills/${encodeURIComponent(skillName)}`, { method: 'DELETE' })
      showNotification(t('skillDeleted'), 'success')
      setSelectedSkills(prev => prev.filter(s => s !== skillName))
      fetchSkills()
    } catch (err) { showNotification('Delete failed: ' + err.message, 'error') }
  }, [showNotification, fetchSkills])

  const handleEditSkill = useCallback(async (skillName) => {
    try {
      const r = await fetch(`${API_BASE}/skills/${encodeURIComponent(skillName)}`)
      const data = await r.json()
      if (data.skill) {
        setEditingSkillName(skillName)
        setEditSkillContent(data.skill.content || '')
      }
    } catch { /* silent */ }
  }, [])

  const handleSaveSkill = useCallback(async (t) => {
    if (!editingSkillName) return
    try {
      const r = await fetch(`${API_BASE}/skills/${encodeURIComponent(editingSkillName)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editSkillContent })
      })
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail) }
      showNotification(t('skillUpdated'), 'success')
      setEditingSkillName(null)
      setEditSkillContent('')
      fetchSkills()
    } catch (err) { showNotification('Update failed: ' + err.message, 'error') }
  }, [editingSkillName, editSkillContent, showNotification, fetchSkills])

  const filteredSkills = skillSearch
    ? skills.filter(s => s.name.toLowerCase().includes(skillSearch.toLowerCase()) ||
                         s.description.toLowerCase().includes(skillSearch.toLowerCase()) ||
                         (s.tags || []).some(t => t.toLowerCase().includes(skillSearch.toLowerCase())))
    : skills

  return {
    skills, selectedSkills, setSelectedSkills, activeSkillCount, setActiveSkillCount,
    showSkillPanel, setShowSkillPanel, showSkillManager, setShowSkillManager,
    skillSearch, setSkillSearch, creatingSkill, setCreatingSkill,
    newSkill, setNewSkill, editingSkillName, setEditingSkillName,
    editSkillContent, setEditSkillContent, skillGenPreset, setSkillGenPreset,
    fetchSkills, toggleSkill, handleCreateSkill, handleDeleteSkill,
    handleEditSkill, handleSaveSkill, filteredSkills,
  }
}
