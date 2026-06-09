export default function MemoryPanel({ t, language, memory }) {
  const content = memory || ""
  const summaryMatch = content.match(/\[SUMMARY:\s*(.+?)\]/gs)

  return (
    <div className="side-panel memory-panel">
      <div className="side-panel-header">
        <span> {language === "zh" ? "全局记忆" : "Memory"}</span>
      </div>
      <div className="side-panel-body">
        {content ? (
          <div className="side-panel-readonly">
            {summaryMatch && summaryMatch.length > 0 && (
              <div className="memory-summaries">
                <p className="memory-label"> {language === "zh" ? "摘要" : "Summaries"}:</p>
                {summaryMatch.map((s, i) => (
                  <p key={i} className="memory-summary">{s.replace("[SUMMARY: ", "").replace("]", "").substring(0, 200)}</p>
                ))}
              </div>
            )}
            <div className="memory-full">
              <pre className="memory-text">{content.substring(0, 3000)}{content.length > 3000 ? "..." : ""}</pre>
            </div>
          </div>
        ) : (
          <p className="side-panel-empty">
            {language === "zh" ? "AI 将在写作过程中自动积累全局记忆" : "AI will accumulate global memory during writing"}
          </p>
        )}
      </div>
    </div>
  )
}
