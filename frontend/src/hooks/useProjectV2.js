import { useState, useCallback, useEffect } from "react"
import { API_BASE } from "../constants"

/**
 * v2 Project Hook — SQLite 驱动的项目中心。
 * 核心功能：
 * 1. 拉取所有项目（list）/ 单个项目详情（with chapters, memory, chat）
 * 2. 创建 / 删除项目
 * 3. 阶段执行（outline / writing / polish）
 * 4. 大纲人工审核推进或驳回
 * 5. 人工编辑章节、添加记忆
 * 6. AI 助理对话
 * 7. 项目文件读写（outline / characters）
 */
export default function useProjectV2({ showNotification, presets = [], t }) {
  const [projects, setProjects] = useState([])
  const [activeProject, setActiveProject] = useState(null)
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [isRunning, setIsRunning] = useState(false)

  // ---------- 列表 ----------
  const fetchProjects = useCallback(async () => {
    setLoadingList(true)
    try {
      const resp = await fetch(`${API_BASE}/v2/projects`)
      if (resp.ok) {
        const data = await resp.json()
        setProjects(data.projects || [])
      }
    } catch (e) {
      console.error("[v2] fetch projects failed:", e)
    } finally {
      setLoadingList(false)
    }
  }, [])

  // ---------- 详情 ----------
  const loadProject = useCallback(async (name) => {
    if (!name) return
    setLoadingDetail(true)
    try {
      const [projResp, chaptersResp, memoryResp, chatResp] = await Promise.all([
        fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}`),
        fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/chapters`),
        fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/memory`),
        fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/chat`),
      ])

      const project = projResp.ok ? await projResp.json() : null
      const chapters = chaptersResp.ok ? (await chaptersResp.json()).chapters || [] : []
      const memory = memoryResp.ok ? (await memoryResp.json()).memory || [] : []
      const chat = chatResp.ok ? (await chatResp.json()).chat || [] : []

      setActiveProject({
        ...(project || { name }),
        chapters,
        memory,
        chat,
      })
    } catch (e) {
      console.error("[v2] load project failed:", e)
    } finally {
      setLoadingDetail(false)
    }
  }, [])

  // ---------- 创建 ----------
  const createProject = useCallback(async (payload) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      showNotification && showNotification(t?.("projectCreated") || "项目已创建", "success")
      await fetchProjects()
      return data
    } catch (e) {
      showNotification && showNotification((t?.("createFailed") || "创建失败: ") + e.message, "error")
      return null
    }
  }, [showNotification, fetchProjects, t])

  // ---------- 删除 ----------
  const deleteProject = useCallback(async (name) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}`, {
        method: "DELETE",
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      showNotification && showNotification(t?.("projectDeleted") || "项目已删除", "success")
      if (activeProject?.name === name) setActiveProject(null)
      await fetchProjects()
      return true
    } catch (e) {
      showNotification && showNotification("删除失败: " + e.message, "error")
      return false
    }
  }, [showNotification, fetchProjects, activeProject, t])

  // ---------- 更新章节 ----------
  const updateChapter = useCallback(async (name, chapterIndex, body) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/chapters/${chapterIndex}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadProject(name)
      return true
    } catch (e) {
      showNotification && showNotification("更新失败: " + e.message, "error")
      return false
    }
  }, [showNotification, loadProject])

  // ---------- 添加记忆 ----------
  const addMemory = useCallback(async (name, content, memType = "note", chapterRef = 0) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/memory`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: memType, content, chapter_ref: chapterRef }),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadProject(name)
      return true
    } catch (e) {
      showNotification && showNotification("添加记忆失败: " + e.message, "error")
      return false
    }
  }, [showNotification, loadProject])

  // ---------- 大纲审核 ----------
  const confirmOutline = useCallback(async (name) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/confirm-outline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadProject(name)
      showNotification && showNotification("大纲已确认，推进至写作阶段", "success")
      return true
    } catch (e) {
      showNotification && showNotification("确认失败: " + e.message, "error")
      return false
    }
  }, [showNotification, loadProject])

  const rejectOutline = useCallback(async (name) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/reject-outline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadProject(name)
      showNotification && showNotification("大纲已驳回", "info")
      return true
    } catch (e) {
      showNotification && showNotification("驳回失败: " + e.message, "error")
      return false
    }
  }, [showNotification, loadProject])

  // ---------- 停止 ----------
  const stopTask = useCallback(async (name) => {
    try {
      await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/stop`, { method: "POST" })
      setIsRunning(false)
      showNotification && showNotification(t?.("taskStopped") || "已停止", "info")
      await loadProject(name)
    } catch (e) {
      showNotification && showNotification("停止失败: " + e.message, "error")
    }
  }, [showNotification, loadProject, t])

  // ---------- 启动阶段（流式 SSE） ----------
  const runStage = useCallback(async ({
    projectName, stage, task = "", executionMode = "standard", outlineReviewMode = "auto",
  }) => {
    if (!projectName) return
    setIsRunning(true)
    const presetsPayload = (presets || []).map(p => ({
      name: p.name || "", api_key: p.api_key || "",
      base_url: p.base_url || "", model: p.model || "",
      api_format: p.api_format || "openai",
      chat_template_kwargs: p.chat_template_kwargs || null,
    }))

    try {
      const resp = await fetch(`${API_BASE}/v2/projects/run-stage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: projectName, stage, task,
          execution_mode: executionMode,
          outline_review_mode: outlineReviewMode,
          presets: presetsPayload,
        }),
      })

      if (!resp.ok) {
        const err = await resp.text()
        throw new Error(`HTTP ${resp.status}: ${err}`)
      }
      const reader = resp.body?.getReader()
      if (!reader) throw new Error("No stream reader")
      const decoder = new TextDecoder()
      let receivedEvents = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split("\n")) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6))
              receivedEvents.push(data)
              if (data.status === "finished" || data.status === "done") {
                showNotification && showNotification("阶段完成", "success")
              }
              if (data.status === "error") {
                showNotification && showNotification(data.message || "出错", "error")
              }
            } catch (e) {
              // 忽略格式错误的数据行
            }
          }
        }
      }

      await loadProject(projectName)
      return receivedEvents
    } catch (e) {
      console.error("[v2] run stage failed:", e)
      showNotification && showNotification("执行失败: " + e.message, "error")
      return []
    } finally {
      setIsRunning(false)
    }
  }, [showNotification, presets, loadProject])

  // ---------- AI 助理对话 ----------
  const assistantChat = useCallback(async (name, message) => {
    try {
      const presetsPayload = (presets || []).map(p => ({
        name: p.name || "", api_key: p.api_key || "",
        base_url: p.base_url || "", model: p.model || "",
        api_format: p.api_format || "openai",
        chat_template_kwargs: p.chat_template_kwargs || null,
      }))
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, presets: presetsPayload }),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      await loadProject(name)
      return data.reply || ""
    } catch (e) {
      showNotification && showNotification("AI 助理失败: " + e.message, "error")
      return ""
    }
  }, [showNotification, presets, loadProject])

  // ---------- 写入文件 ----------
  const putFile = useCallback(async (name, file, content) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/file/${encodeURIComponent(file)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      await loadProject(name)
      showNotification && showNotification("文件已保存", "success")
      return true
    } catch (e) {
      showNotification && showNotification("保存失败: " + e.message, "error")
      return false
    }
  }, [showNotification, loadProject])

  // ---------- 读取文件 ----------
  const getFile = useCallback(async (name, file) => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/${encodeURIComponent(name)}/file/${encodeURIComponent(file)}`)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      return data.content || ""
    } catch (e) {
      return ""
    }
  }, [])

  // ---------- 迁移旧项目 ----------
  const migrateOld = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/v2/projects/migrate-old`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      const data = resp.ok ? await resp.json() : {}
      await fetchProjects()
      return data
    } catch (e) {
      return { success: false, error: e.message }
    }
  }, [fetchProjects])

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  return {
    // state
    projects, setProjects,
    activeProject, setActiveProject,
    loadingList, loadingDetail,
    isRunning, setIsRunning,

    // actions
    fetchProjects, loadProject,
    createProject, deleteProject,
    updateChapter, addMemory,
    confirmOutline, rejectOutline,
    stopTask, runStage,
    assistantChat,
    putFile, getFile,
    migrateOld,
  }
}
