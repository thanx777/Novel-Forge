import { useState } from "react"
import { API_BASE } from "../constants"

export default function TaskDetailModal({
  t, language, presets,
  taskFolder, taskDetail, onClose, onResume, isRunning, showNotification
}) {
  const [editTask, setEditTask] = useState(taskDetail.task || "")
  const [editNodes, setEditNodes] = useState(
    () => (taskDetail.nodes || []).map(n => ({ ...n, config: { ...n.config } }))
  )
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      const nodesPayload = editNodes.map(n => ({
        id: n.id, type: n.type,
        config: { preset_name: n.config?.preset_name || "", custom_prompt: n.config?.custom_prompt || "", agent_role: n.config?.agent_role || "", label: n.config?.label || "" }
      }))
      // Collect unique preset names used by nodes, and build presets payload from global presets
      const usedPresetNames = [...new Set(nodesPayload.map(n => n.config.preset_name).filter(Boolean))]
      const presetsPayload = usedPresetNames.map(name => {
        const p = presets.find(pr => pr.name === name)
        return p ? { name: p.name, api_key: p.api_key, base_url: p.base_url, model: p.model, api_format: p.api_format || 'openai', chat_template_kwargs: p.chat_template_kwargs || null, thinking_mode: p.thinking_mode || null } : null
      }).filter(Boolean)
      const resp = await fetch(`${API_BASE}/tasks/${encodeURIComponent(taskFolder)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: editTask, nodes: nodesPayload, presets: presetsPayload })
      })
      if (resp.ok) {
        showNotification(language === "zh" ? "已保存" : "Saved", "success")
        onClose()
      } else {
        showNotification(language === "zh" ? "保存失败" : "Save failed", "error")
      }
    } catch (e) {
      showNotification(language === "zh" ? "保存失败" : "Save failed", "error")
    }
    setSaving(false)
  }

  const updateNodePreset = (idx, presetName) => {
    setEditNodes(prev => {
      const next = [...prev]
      next[idx] = { ...next[idx], config: { ...next[idx].config, preset_name: presetName } }
      return next
    })
  }

  const updateNodeLabel = (idx, label) => {
    setEditNodes(prev => {
      const next = [...prev]
      next[idx] = { ...next[idx], config: { ...next[idx].config, label } }
      return next
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content novel-modal" onClick={e => e.stopPropagation()}>
        <div className="novel-modal-header">
          <h2>{language === "zh" ? "任务配置" : "Task Config"}</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="novel-modal-body">
          {/* Task name */}
          <div className="form-group">
            <label>{language === "zh" ? "任务" : "Task"}</label>
            <input
              type="text" value={editTask}
              onChange={e => setEditTask(e.target.value)}
              className="form-input"
            />
          </div>

          {/* Read-only info row */}
          <div className="form-row">
            <div className="form-group form-group-half">
              <label>{language === "zh" ? "执行模式" : "Mode"}</label>
              <div className="task-detail-value">{taskDetail.execution_mode || "standard"}</div>
            </div>
            <div className="form-group form-group-half">
              <label>{language === "zh" ? "阶段" : "Stage"}</label>
              <div className="task-detail-value">{taskDetail.novel_stage || "-"}</div>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group form-group-half">
              <label>{language === "zh" ? "已完成章节" : "Chapters Done"}</label>
              <div className="task-detail-value">{taskDetail.chapters_done}</div>
            </div>
            <div className="form-group form-group-half">
              <label>{language === "zh" ? "更新时间" : "Updated"}</label>
              <div className="task-detail-value">{taskDetail.updated || "-"}</div>
            </div>
          </div>

          {/* Node / model assignment - editable */}
          {editNodes.length > 0 && (
            <div className="form-group">
              <label>{language === "zh" ? "节点配置" : "Node Config"}</label>
              <div className="role-preset-grid">
                {editNodes.map((node, i) => (
                  <div key={i} className="role-preset-row">
                    <div className="role-preset-info">
                      <input
                        type="text"
                        value={node.config?.label || ""}
                        onChange={e => updateNodeLabel(i, e.target.value)}
                        className="form-input task-node-label-input"
                        placeholder={node.type}
                      />
                      <span className="role-preset-desc">{node.id} ({node.type})</span>
                    </div>
                    <select
                      value={node.config?.preset_name || ""}
                      onChange={e => updateNodePreset(i, e.target.value)}
                      className="form-select role-preset-select"
                    >
                      <option value="">{language === "zh" ? "— 选择模型 —" : "— Select model —"}</option>
                      {presets.map((p, j) => (
                        <option key={j} value={p.name}>{p.name} ({p.model})</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="novel-modal-footer">
          <button className="btn btn-cancel" onClick={onClose}>
            {language === "zh" ? "取消" : "Cancel"}
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "⏳ ..." : (language === "zh" ? "💾 保存" : "💾 Save")}
          </button>
          <button className="btn btn-primary btn-start" onClick={onResume} disabled={isRunning}>
            {isRunning ? "⏳ ..." : (language === "zh" ? "▶ 继续执行" : "▶ Resume")}
          </button>
        </div>
      </div>
    </div>
  )
}
