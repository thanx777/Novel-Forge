import { useState, useEffect } from "react"

export default function OutlinePanel({ t, language, outline, onSave, showNotification }) {
  const [editMode, setEditMode] = useState(false)
  const [text, setText] = useState(outline || "")

  useEffect(() => { setText(outline || "") }, [outline])

  const handleSave = async () => {
    if (onSave) {
      await onSave(text)
      showNotification(language === "zh" ? "大纲已保存" : "Outline saved", "success")
    }
    setEditMode(false)
  }

  return (
    <div className="side-panel outline-panel">
      <div className="side-panel-header">
        <span> {language === "zh" ? "大纲" : "Outline"}</span>
        <button className="side-panel-action" onClick={() => setEditMode(!editMode)}>
          {editMode ? "" : ""}
        </button>
      </div>
      <div className="side-panel-body">
        {editMode ? (
          <textarea
            className="side-panel-textarea"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder={language === "zh" ? "输入大纲内容，每章一句话..." : "Enter outline, one sentence per chapter..."}
            rows={15}
          />
        ) : (
          <div className="side-panel-readonly">
            {text ? (
              text.split("\n").map((line, i) => (
                <p key={i} className="outline-line">{line || "\u00A0"}</p>
              ))
            ) : (
              <p className="side-panel-empty">{language === "zh" ? "暂无大纲" : "No outline yet"}</p>
            )}
          </div>
        )}
      </div>
      {editMode && (
        <div className="side-panel-footer">
          <button className="side-panel-btn cancel" onClick={() => { setText(outline || ""); setEditMode(false) }}>
            {t("cancel")}
          </button>
          <button className="side-panel-btn save" onClick={handleSave}>
             {t("savePreset")}
          </button>
        </div>
      )}
    </div>
  )
}
