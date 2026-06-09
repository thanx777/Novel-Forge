import { useState, useCallback, useEffect } from 'react'
import { API_BASE } from '../constants'

export default function useNovelReader(folder) {
  const [files, setFiles] = useState([])
  const [activeFile, setActiveFile] = useState('')
  const [fileContent, setFileContent] = useState('')
  const [chapters, setChapters] = useState([])
  const [outline, setOutline] = useState('')
  const [characters, setCharacters] = useState('')
  const [memory, setMemory] = useState('')
  const [loading, setLoading] = useState(false)

  const loadFiles = useCallback(async () => {
    if (!folder) return
    setLoading(true)
    try {
      const resp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(folder)}`)
      if (resp.ok) {
        const data = await resp.json()
        const allFiles = data.files || []
        setFiles(allFiles)

        // Extract chapters
        const chapterFiles = allFiles
          .filter(f => /^第.*?章\.txt$/i.test(f))
          .sort((a, b) => {
            const numA = parseInt(a.replace(/[^0-9]/g, '')) || 0
            const numB = parseInt(b.replace(/[^0-9]/g, '')) || 0
            return numA - numB
          })
        setChapters(chapterFiles)

        // Load outline
        const outlineFile = allFiles.find(f => f.endsWith('outline.md') || f.endsWith('Outline.md'))
        if (outlineFile) {
          const oResp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(outlineFile)}`)
          if (oResp.ok) {
            const oData = await oResp.json()
            setOutline(oData.content || '')
          }
        }

        // Load characters
        const charFile = allFiles.find(f => f.endsWith('characters.md') || f.endsWith('Characters.md'))
        if (charFile) {
          const cResp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(charFile)}`)
          if (cResp.ok) {
            const cData = await cResp.json()
            setCharacters(cData.content || '')
          }
        }

        // Load memory
        const memFile = allFiles.find(f => f.includes('memory') && f.endsWith('novel_memory.md'))
        if (memFile) {
          const mResp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(memFile)}`)
          if (mResp.ok) {
            const mData = await mResp.json()
            setMemory(mData.content || '')
          }
        }

        // Default to first chapter
        if (chapterFiles.length > 0 && !activeFile) {
          const firstChapter = chapterFiles[0]
          setActiveFile(firstChapter)
          const contentResp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(firstChapter)}`)
          if (contentResp.ok) {
            const cData = await contentResp.json()
            setFileContent(cData.content || '')
          }
        }
      }
    } catch (e) {
      console.error('Failed to load files:', e)
    }
    setLoading(false)
  }, [folder, activeFile])

  const saveFile = useCallback(async (fileName, content) => {
    try {
      const resp = await fetch(`${API_BASE}/workspace/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder: folder,
          file: fileName,
          content: content,
        })
      })
      return resp.ok
    } catch (e) {
      console.error('Failed to save file:', e)
      return false
    }
  }, [folder])

  const loadChapter = useCallback(async (fileName) => {
    if (!folder || !fileName) return
    setActiveFile(fileName)
    try {
      const resp = await fetch(`${API_BASE}/workspace/files?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(fileName)}`)
      if (resp.ok) {
        const data = await resp.json()
        setFileContent(data.content || '')
      }
    } catch (e) {
      console.error('Failed to load chapter:', e)
    }
  }, [folder])

  return {
    files, chapters, outline, characters, memory, fileContent,
    activeFile, loading,
    loadFiles, loadChapter, saveFile,
    setFileContent, setOutline, setCharacters, setActiveFile,
  }
}
