import { useState, useEffect } from "react"

export default function CharacterPanel({ t, language, characters, onSave, showNotification }) {
  const [editMode, setEditMode] = useState(false)
  const [text, setText] = useState(characters || "")

  useEffect(() => { setText(characters || "") }, [characters])

  const handleSave = async () => {
    if (onSave) {
      await onSave(text)
      showNotification(language === "zh" ? "人物设定已保存" : "Characters saved", "success")
    }
    setEditMode(false)
  }

  return (
    <div className="side-panel character-panel">
      <div className="side-panel-header">
        <span> {language === "zh" ? "人物设定" : "Characters"}</span>
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
            placeholder={language === "zh" ? "人物姓名、性格、外貌、关系..." : "Character names, traits, appearance, relationships..."}
            rows={12}
          />
        ) : (
          <div className="side-panel-readonly">
            {text ? (
              text.split("\n").map((line, i) => (
                <p key={i} className="character-line">{line || "\u00A0"}</p>
              ))
            ) : (
              <p className="side-panel-empty">{language === "zh" ? "暂无人物设定" : "No character profiles yet"}</p>
            )}
          </div>
        )}
      </div>
      {editMode && (
        <div className="side-panel-footer">
          <button className="side-panel-btn cancel" onClick={() => { setText(characters || ""); setEditMode(false) }}>
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
