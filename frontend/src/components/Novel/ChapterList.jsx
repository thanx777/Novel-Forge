export default function ChapterList({
  t, language,
  chapters, activeFile, onSelectChapter, outline, characters, memory,
  showOutline, setShowOutline, showCharacters, setShowCharacters, showMemory, setShowMemory,
  taskStatus
}) {
  const chapterCount = chapters?.length || 0

  return (
    <div className="chapter-list-panel">
      <div className="chapter-list-header">
        <span className="chapter-list-title"> {t('chapterList')}</span>
        <span className="chapter-count-badge">{chapterCount}</span>
      </div>

      <div className="chapter-list-actions">
        <button
          className={`list-action-btn ${showOutline ? 'active' : ''}`}
          onClick={() => { setShowMemory(false); setShowCharacters(false); setShowOutline(!showOutline) }}
          title={t('outline')}
        >
           {t('outline')}
        </button>
        <button
          className={`list-action-btn ${showCharacters ? 'active' : ''}`}
          onClick={() => { setShowOutline(false); setShowMemory(false); setShowCharacters(!showCharacters) }}
          title={t('characters')}
        >
           {t('characters')}
        </button>
        <button
          className={`list-action-btn ${showMemory ? 'active' : ''}`}
          onClick={() => { setShowOutline(false); setShowCharacters(false); setShowMemory(!showMemory) }}
          title={t('memory')}
        >
           {t('memory')}
        </button>
      </div>

      <div className="chapter-list-body">
        {showOutline && outline && (
          <div className="outline-view">
            <pre className="outline-text">{outline}</pre>
          </div>
        )}
        {showCharacters && characters && (
          <div className="outline-view">
            <pre className="outline-text">{characters}</pre>
          </div>
        )}
        {showMemory && memory && (
          <div className="outline-view">
            <pre className="outline-text">{memory}</pre>
          </div>
        )}
        {!showOutline && !showCharacters && !showMemory && (
          <div className="chapter-items">
            {chapters?.length === 0 ? (
              <div className="chapter-list-empty">
                {taskStatus === 'running' ? (
                  <span className="chapter-list-loading">
                    {t('loading')}...
                  </span>
                ) : (
                  <span>{t('noOutlineYet')}</span>
                )}
              </div>
            ) : (
              chapters.map((f, i) => {
                const chNum = parseInt(f.replace(/[^0-9]/g, '')) || (i + 1)
                return (
                  <div
                    key={f}
                    className={`chapter-item ${f === activeFile ? 'active' : ''}`}
                    onClick={() => onSelectChapter(f)}
                  >
                    <span className="chapter-item-num">{chNum}</span>
                    <span className="chapter-item-name">
                      {t('chapter').replace('{n}', chNum)}
                    </span>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>
    </div>
  )
}
