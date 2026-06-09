import { useState, useEffect, useRef, useCallback } from 'react'
import { NODE_TYPES, NODE_W, HEADER_H } from '../constants'

export default function useCanvas({ nodes, setNodes, connections, setConnections, selectedNode, setSelectedNode, selectedConn, setSelectedConn, pan, setPan }) {
  const canvasRef = useRef(null)
  const draggingRef = useRef(null)
  const connectingRef = useRef(null)
  const panningRef = useRef(null)
  const panRef = useRef({ x: 0, y: 0 })
  const [tempConnEnd, setTempConnEnd] = useState(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connContextMenu, setConnContextMenu] = useState(null)
  const [editingAnnotation, setEditingAnnotation] = useState(null)
  const [annotationText, setAnnotationText] = useState('')
  const [hoveredConn, setHoveredConn] = useState(null)

  useEffect(() => { panRef.current = pan }, [pan])

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!canvasRef.current) return
      const rect = canvasRef.current.getBoundingClientRect()
      if (draggingRef.current) {
        const { nodeId, offsetX, offsetY } = draggingRef.current
        const x = e.clientX - rect.left - panRef.current.x - offsetX
        const y = e.clientY - rect.top - panRef.current.y - offsetY
        setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, x, y } : n))
      }
      if (connectingRef.current) {
        setTempConnEnd({
          x: e.clientX - rect.left - panRef.current.x,
          y: e.clientY - rect.top - panRef.current.y
        })
      }
      if (panningRef.current) {
        const { startX, startY, startPanX, startPanY } = panningRef.current
        setPan({ x: startPanX + (e.clientX - startX), y: startPanY + (e.clientY - startY) })
      }
    }
    const handleMouseUp = () => {
      draggingRef.current = null
      panningRef.current = null
      if (connectingRef.current) {
        connectingRef.current = null
        setTempConnEnd(null)
        setIsConnecting(false)
      }
    }
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

  const removeNode = useCallback((id) => {
    setNodes(prev => prev.filter(n => n.id !== id))
    setConnections(prev => prev.filter(c => c.from !== id && c.to !== id))
    if (selectedNode === id) setSelectedNode(null)
  }, [selectedNode, setNodes, setConnections, setSelectedNode])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedConn) {
          setConnections(prev => prev.filter(c => c.id !== selectedConn))
          setSelectedConn(null)
        } else if (selectedNode) {
          removeNode(selectedNode)
        }
      }
      if (e.key === 'Escape') {
        setSelectedNode(null)
        setSelectedConn(null)
        connectingRef.current = null
        setTempConnEnd(null)
        setIsConnecting(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedNode, selectedConn, removeNode, setConnections, setSelectedNode, setSelectedConn])

  const getPortPos = useCallback((nodeId, portId, isOutput) => {
    const node = nodes.find(n => n.id === nodeId)
    if (!node || !node.ports) return { x: 0, y: 0 }
    const ports = isOutput ? node.ports.outputs : node.ports.inputs
    const portIndex = ports.findIndex(p => p.id === portId)
    if (portIndex === -1) return { x: 0, y: 0 }
    const portRowH = 26
    const portYStart = HEADER_H + 14
    return {
      x: isOutput ? node.x + NODE_W : node.x,
      y: node.y + portYStart + portIndex * portRowH
    }
  }, [nodes])

  const renderCurve = useCallback((fromPos, toPos) => {
    const dx = Math.max(Math.abs(toPos.x - fromPos.x) * 0.5, 50)
    return `M ${fromPos.x} ${fromPos.y} C ${fromPos.x + dx} ${fromPos.y}, ${toPos.x - dx} ${toPos.y}, ${toPos.x} ${toPos.y}`
  }, [])

  const addNode = useCallback((type) => {
    const id = 'n' + Date.now()
    const rect = canvasRef.current?.getBoundingClientRect()
    const cx = rect ? rect.width / 2 - panRef.current.x : 400
    const cy = rect ? rect.height / 2 - panRef.current.y : 200
    const nodeType = NODE_TYPES[type]
    const defaultPorts = JSON.parse(JSON.stringify(nodeType.defaultPorts))
    setNodes(prev => [...prev, {
      id, type,
      x: cx - NODE_W / 2 + (Math.random() - 0.5) * 100,
      y: cy - 40 + (Math.random() - 0.5) * 60,
      config: { preset_name: '', agent_role: '', custom_prompt: '' },
      ports: defaultPorts,
      activity: 'idle',
      thought: '',
      response: '',
      history: []
    }])
  }, [setNodes])

  const addPort = useCallback((nodeId, direction) => {
    const portId = (direction === 'input' ? 'inp_' : 'out_') + Date.now()
    const portName = direction === 'input' ? 'input' : 'output'
    setNodes(prev => prev.map(n => {
      if (n.id !== nodeId) return n
      const key = direction === 'input' ? 'inputs' : 'outputs'
      return { ...n, ports: { ...n.ports, [key]: [...n.ports[key], { id: portId, name: portName }] } }
    }))
  }, [setNodes])

  const removePort = useCallback((nodeId, portId) => {
    setNodes(prev => prev.map(n => {
      if (n.id !== nodeId) return n
      return {
        ...n,
        ports: {
          inputs: n.ports.inputs.filter(p => p.id !== portId),
          outputs: n.ports.outputs.filter(p => p.id !== portId)
        }
      }
    }))
    setConnections(prev => prev.filter(c => c.fromPort !== portId && c.toPort !== portId))
  }, [setNodes, setConnections])

  const renamePort = useCallback((nodeId, portId, newName) => {
    setNodes(prev => prev.map(n => {
      if (n.id !== nodeId) return n
      return {
        ...n,
        ports: {
          inputs: n.ports.inputs.map(p => p.id === portId ? { ...p, name: newName } : p),
          outputs: n.ports.outputs.map(p => p.id === portId ? { ...p, name: newName } : p)
        }
      }
    }))
  }, [setNodes])

  const updateConnAnnotation = useCallback((connId, annotation) => {
    setConnections(prev => prev.map(c => c.id === connId ? { ...c, annotation } : c))
  }, [setConnections])

  const handleConnContextMenu = useCallback((e, connId) => {
    e.preventDefault(); e.stopPropagation()
    setConnContextMenu({ connId, x: e.clientX, y: e.clientY })
  }, [])

  const handleNodeMouseDown = useCallback((e, nodeId) => {
    e.stopPropagation()
    if (e.button !== 0) return
    const node = nodes.find(n => n.id === nodeId)
    if (!node) return
    const rect = canvasRef.current.getBoundingClientRect()
    draggingRef.current = { nodeId, offsetX: e.clientX - rect.left - panRef.current.x - node.x, offsetY: e.clientY - rect.top - panRef.current.y - node.y }
    setSelectedNode(nodeId)
    setSelectedConn(null)
  }, [nodes, setSelectedNode, setSelectedConn])

  const handlePortMouseDown = useCallback((e, nodeId, portName, isOutput) => {
    e.stopPropagation(); e.preventDefault()
    connectingRef.current = { nodeId, portName, isOutput }
    setIsConnecting(true)
  }, [])

  const handlePortMouseUp = useCallback((e, nodeId, portName, isOutput) => {
    e.stopPropagation()
    if (!connectingRef.current) return
    const from = connectingRef.current
    let sourceNodeId, sourcePort, targetNodeId, targetPort
    if (from.isOutput && !isOutput) { sourceNodeId = from.nodeId; sourcePort = from.portName; targetNodeId = nodeId; targetPort = portName }
    else if (!from.isOutput && isOutput) { sourceNodeId = nodeId; sourcePort = portName; targetNodeId = from.nodeId; targetPort = from.portName }
    else { connectingRef.current = null; setTempConnEnd(null); setIsConnecting(false); return }
    if (sourceNodeId === targetNodeId) { connectingRef.current = null; setTempConnEnd(null); setIsConnecting(false); return }
    const exists = connections.some(c => c.from === sourceNodeId && c.fromPort === sourcePort && c.to === targetNodeId && c.toPort === targetPort)
    if (!exists) {
      setConnections(prev => [...prev, { id: 'c' + Date.now(), from: sourceNodeId, fromPort: sourcePort, to: targetNodeId, toPort: targetPort }])
    }
    connectingRef.current = null; setTempConnEnd(null); setIsConnecting(false)
  }, [connections, setConnections])

  const handleCanvasMouseDown = useCallback((e) => {
    if (e.button === 1) { e.preventDefault(); panningRef.current = { startX: e.clientX, startY: e.clientY, startPanX: panRef.current.x, startPanY: panRef.current.y }; return }
    if (e.button === 0) {
      const t2 = e.target
      if (t2 === canvasRef.current || t2.classList.contains('canvas-content') || t2.tagName === 'svg' || t2.classList.contains('canvas-grid')) {
        setSelectedNode(null); setSelectedConn(null)
        panningRef.current = { startX: e.clientX, startY: e.clientY, startPanX: panRef.current.x, startPanY: panRef.current.y }
      }
    }
  }, [setSelectedNode, setSelectedConn])

  return {
    canvasRef,
    addNode,
    removeNode,
    addPort,
    removePort,
    renamePort,
    getPortPos,
    renderCurve,
    handleNodeMouseDown,
    handlePortMouseDown,
    handlePortMouseUp,
    handleCanvasMouseDown,
    tempConnEnd,
    isConnecting,
    connectingRef,
    connContextMenu,
    setConnContextMenu,
    editingAnnotation,
    setEditingAnnotation,
    annotationText,
    setAnnotationText,
    hoveredConn,
    setHoveredConn,
    updateConnAnnotation,
    handleConnContextMenu,
  }
}
