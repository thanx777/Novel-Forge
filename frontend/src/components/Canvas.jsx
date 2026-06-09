import { NODE_TYPES } from '../constants'

export function ConnectionLayer({ connections, selectedConn, setSelectedConn, setSelectedNode, setConnContextMenu, hoveredConn, setHoveredConn, getPortPos, renderCurve, isConnecting, tempConnEnd, connectingRef }) {
  return (
    <svg className="connections-layer" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="var(--accent)" opacity="0.8" />
        </marker>
        <marker id="arrowhead-selected" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="var(--red)" opacity="0.9" />
        </marker>
      </defs>
      {connections.map(conn => {
        const fromPos = getPortPos(conn.from, conn.fromPort, true)
        const toPos = getPortPos(conn.to, conn.toPort, false)
        const isSelected = selectedConn === conn.id
        const isHovered = hoveredConn === conn.id
        const midX = (fromPos.x + toPos.x) / 2
        const midY = (fromPos.y + toPos.y) / 2
        return (
          <g key={conn.id}
            onClick={(e) => { e.stopPropagation(); setSelectedConn(conn.id); setSelectedNode(null); setConnContextMenu(null) }}
            onDoubleClick={(e) => { e.stopPropagation(); e.preventDefault() }}
            onContextMenu={(e) => setConnContextMenu(e, conn.id)}
            onMouseEnter={() => setHoveredConn(conn.id)}
            onMouseLeave={() => setHoveredConn(null)}
            style={{ cursor: 'pointer' }}>
            <path d={renderCurve(fromPos, toPos)} fill="none" stroke="transparent" strokeWidth="14" />
            <path d={renderCurve(fromPos, toPos)} fill="none" stroke={isSelected ? 'var(--red)' : 'var(--accent)'} strokeWidth={isSelected ? 2.5 : 2} markerEnd={`url(#${isSelected ? 'arrowhead-selected' : 'arrowhead'})`} className="connection-line" />
            {conn.annotation && (
              <g transform={`translate(${midX}, ${midY - 16})`} opacity={isHovered || isSelected ? 1 : 0.7}>
                <rect rx="3" ry="3" fill="var(--bg-elevated)" stroke="var(--border)" strokeWidth="1" x={-conn.annotation.length * 3.2 - 5} y={-9} width={conn.annotation.length * 6.4 + 10} height={18} />
                <text textAnchor="middle" fill="var(--accent)" fontSize="9.5" fontFamily="inherit" fontWeight="500">{conn.annotation}</text>
              </g>
            )}
            {((isHovered || isSelected)) && (
              <g transform={`translate(${midX}, ${midY})`}>
                <circle r="4" fill="var(--accent)" opacity="0.5" />
              </g>
            )}
          </g>
        )
      })}
      {isConnecting && tempConnEnd && connectingRef.current && (() => {
        const { nodeId, portName, isOutput } = connectingRef.current
        const portPos = getPortPos(nodeId, portName, isOutput)
        const fromPos = isOutput ? portPos : tempConnEnd
        const toPos = isOutput ? tempConnEnd : portPos
        return <path d={renderCurve(fromPos, toPos)} fill="none" stroke="var(--accent)" strokeWidth="2" strokeDasharray="6 3" opacity="0.7" markerEnd="url(#arrowhead)" />
      })()}
    </svg>
  )
}

export function NodeCanvas({ nodes, selectedNode, agentCatalog, presets, handleNodeMouseDown, handlePortMouseDown, handlePortMouseUp, removeNode, t, getNodeActivityColor, getNodeGlowStyle }) {
  return (
    <div className="nodes-layer">
      {nodes.map(node => {
        const nodeType = NODE_TYPES[node.type]
        const isSelected = selectedNode === node.id
        const activity = node.activity || 'idle'
        const glowStyle = getNodeGlowStyle(activity)
        const agentInfo = agentCatalog.find(a => a.name === node.config?.agent_role) || {}
        return (
          <div key={node.id} className={`node ${isSelected ? 'selected' : ''} node-activity-${activity}`}
            style={{ left: node.x, top: node.y, '--node-color': nodeType.color, ...glowStyle }}
            onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
            onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); removeNode(node.id) }}>
            <div className="node-header">
              <span className="node-type-indicator" style={{ background: nodeType.color }} />
              <span className="node-label">{t(nodeType.label.toLowerCase())}</span>
              {agentInfo.emoji && <span style={{ marginLeft: '4px', fontSize: '11px' }}>{agentInfo.emoji}</span>}
              {activity !== 'idle' && (
                <span className="node-activity-badge" style={{ background: getNodeActivityColor(activity), fontSize: '9px', padding: '1px 4px', borderRadius: '3px', marginLeft: '4px' }}>
                  {activity === 'thinking' ? t('thinking') : activity === 'responding' ? t('responding') : t('completed')}
                </span>
              )}
              <button className="node-delete" onMouseDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); removeNode(node.id) }}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="node-body">
              <div className="node-ports">
                <div className="node-inputs">
                  {(node.ports?.inputs || []).map(port => (
                    <div key={port.id} className="port-row input-port">
                      <div className="port-dot" onMouseDown={(e) => handlePortMouseDown(e, node.id, port.id, false)} onMouseUp={(e) => handlePortMouseUp(e, node.id, port.id, false)} />
                      <span className="port-name">{port.name}</span>
                    </div>
                  ))}
                </div>
                <div className="node-outputs">
                  {(node.ports?.outputs || []).map(port => (
                    <div key={port.id} className="port-row output-port">
                      <span className="port-name">{port.name}</span>
                      <div className="port-dot" onMouseDown={(e) => handlePortMouseDown(e, node.id, port.id, true)} onMouseUp={(e) => handlePortMouseUp(e, node.id, port.id, true)} />
                    </div>
                  ))}
                </div>
              </div>
              <div className="node-footer">
                <span className="node-model">{node.config.preset_name ? (presets.find(p => p.name === node.config.preset_name)?.model || node.config.preset_name) : t('notConfigured')}</span>
                <span className={`node-status ${node.config.preset_name ? 'ready' : 'no-key'}`}>{node.config.preset_name ? t('ready') : t('noKey')}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
