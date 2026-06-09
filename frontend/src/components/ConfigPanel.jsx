import { NODE_TYPES } from '../constants'
import TestResultCard from './TestResultCard'

export default function ConfigPanel({ selectedNodeData, selectedNode, t, language, agentCatalog, presets, nodes, updateNodeConfig, addPort, removePort, renamePort, removeNode, setSelectedNode, testConnection, testConnResult, runTestConnection, updateNodeActivity }) {
  if (!selectedNodeData) return null

  return (
    <div className="config-panel">
      <div className="config-header">
        <span className="config-title">
          <span className="config-dot" style={{ background: NODE_TYPES[selectedNodeData.type]?.color }} />
          {t('nodeConfig')} - {t(NODE_TYPES[selectedNodeData.type]?.label.toLowerCase())}
        </span>
        <button className="config-close" onClick={() => setSelectedNode(null)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      </div>
      <div className="config-body">
        {/* 小说流水线节点：角色已由阶段 prompt 硬编码，无需选择；非流水线节点才显示角色选择 */}
        {!(selectedNodeData.id && /_\d+$/.test(selectedNodeData.id)) && (
        <div className="config-field">
          <label>{t('agentRole')}</label>
          <select
            value={selectedNodeData.config.agent_role || ''}
            onChange={(e) => updateNodeConfig(selectedNode, { agent_role: e.target.value })}
            style={{ width: '100%', fontSize: '11px' }}
          >
            <option value="">{t('agentRolePlaceholder')}</option>
            {agentCatalog.map((a, i) => (
              <option key={i} value={a.name}>{a.emoji || '🤖'} {a.name} — {a.department}</option>
            ))}
          </select>
          <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>
            {t('agentRoleHint')}
          </div>
        </div>
        )}
        <div className="config-field">
          <label>{t('customPrompt')}</label>
          <textarea
            value={selectedNodeData.config.custom_prompt || ''}
            onChange={(e) => updateNodeConfig(selectedNode, { custom_prompt: e.target.value })}
            placeholder={language === 'zh' ? '自定义系统提示词（覆盖模板），留空则使用上方模板' : 'Custom system prompt (overrides template), leave empty to use template above'}
            rows={4}
            style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text)', fontSize: '11px', boxSizing: 'border-box', fontFamily: 'inherit', resize: 'vertical' }}
          />
        </div>
        <div className="config-field">
          <label>{t('modelInfo')}</label>
          <div className="preset-info-card">
            <div className="preset-info-row"><span className="preset-info-label">{t('currentPreset')}</span><span className="preset-info-value">{selectedNodeData.config.preset_name || '-'}</span></div>
            {selectedNodeData.config.preset_name && (() => {
              const p = presets.find(pr => pr.name === selectedNodeData.config.preset_name)
              if (!p) return null
              return (
                <>
                  <div className="preset-info-row"><span className="preset-info-label">{t('model')}</span><span className="preset-info-value">{p.model}</span></div>
                  <div className="preset-info-row"><span className="preset-info-label">{t('apiFormat')}</span><span className="preset-info-value">{p.api_format === 'claude' ? 'Claude' : 'OpenAI'}</span></div>
                </>
              )
            })()}
          </div>
        </div>
        <div className="config-field">
          <label>{t('selectPreset')}</label>
          <select value={selectedNodeData.config.preset_name || ''} onChange={(e) => updateNodeConfig(selectedNode, { preset_name: e.target.value })}>
            <option value="">{t('noPreset')}</option>
            {presets.map((p, i) => <option key={i} value={p.name}>{p.name} ({p.model})</option>)}
          </select>
        </div>
        <div className="config-field">
          <label>{t('thought')} / {t('response')}</label>
          <div className="node-thought-response">
            {selectedNodeData.thought && (
              <div className="nr-section">
                <div className="nr-label">{t('thought')}</div>
                <div className="nr-content nr-thought">{selectedNodeData.thought}</div>
              </div>
            )}
            {selectedNodeData.response && (
              <div className="nr-section">
                <div className="nr-label">{t('response')}</div>
                <div className="nr-content nr-response">{selectedNodeData.response}</div>
              </div>
            )}
            {!selectedNodeData.thought && !selectedNodeData.response && (
              <div className="nr-empty">{t('clickNodeTip')}</div>
            )}
          </div>
        </div>
        <div className="config-field">
          <label>{language === 'zh' ? '端口管理' : 'Port Management'}</label>
          <div className="port-manager">
            <div className="port-manager-section">
              <div className="port-manager-label">{language === 'zh' ? '输入端口' : 'Inputs'}</div>
              {(selectedNodeData.ports?.inputs || []).map(port => (
                <div key={port.id} className="port-manager-row">
                  <input className="port-manager-input" value={port.name} onChange={(e) => renamePort(selectedNode, port.id, e.target.value)} />
                  <button className="port-manager-remove" onClick={() => removePort(selectedNode, port.id)}>
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                  </button>
                </div>
              ))}
              <button className="port-manager-add" onClick={() => addPort(selectedNode, 'input')}>+ {t('addInputPort')}</button>
            </div>
            <div className="port-manager-section">
              <div className="port-manager-label">{language === 'zh' ? '输出端口' : 'Outputs'}</div>
              {(selectedNodeData.ports?.outputs || []).map(port => (
                <div key={port.id} className="port-manager-row">
                  <input className="port-manager-input" value={port.name} onChange={(e) => renamePort(selectedNode, port.id, e.target.value)} />
                  <button className="port-manager-remove" onClick={() => removePort(selectedNode, port.id)}>
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                  </button>
                </div>
              ))}
              <button className="port-manager-add" onClick={() => addPort(selectedNode, 'output')}>+ {t('addOutputPort')}</button>
            </div>
          </div>
        </div>
        {selectedNodeData.history && selectedNodeData.history.length > 0 && (
          <div className="config-field">
            <label>{t('summary')} ({selectedNodeData.history.length})</label>
            <div className="node-history-list">
              {selectedNodeData.history.slice(-3).map((h, i) => (
                <div key={i} className="history-item">
                  <div className="history-time">{new Date(h.timestamp).toLocaleTimeString()}</div>
                  {h.response && <div className="history-response">{h.response.slice(0, 100)}...</div>}
                </div>
              ))}
            </div>
          </div>
        )}
        <button className="config-test-btn" onClick={() => testConnection(selectedNode)} disabled={false}>
          {t('testConnection')}
        </button>
        {testConnResult && (() => {
          const node = nodes?.find(n => n.id === selectedNode)
          const preset = node && node.config.preset_name ? presets.find(p => p.name === node.config.preset_name) : null
          return <TestResultCard result={testConnResult} onRetry={() => preset && runTestConnection(preset)} />
        })()}
        <button className="config-delete-btn" onClick={() => { removeNode(selectedNode); setSelectedNode(null) }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
          {t('delete')}
        </button>
      </div>
    </div>
  )
}
