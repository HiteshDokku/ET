const CATEGORY_BADGE_CLASS = {
  markets: 'badge--markets',
  technology: 'badge--tech',
  tech: 'badge--tech',
  startups: 'badge--startups',
  finance: 'badge--finance',
  economy: 'badge--finance',
  crypto: 'badge--crypto',
  healthcare: 'badge--healthcare',
}

export default function ArticleCard({ article, onVideoGenerate }) {
  const {
    title,
    url,
    source,
    category,
    tags,
    relevance_score,
    matched_interest,
    reason_for_selection,
    query_used,
    personalized,
    ai_generated,
    agent_curated,
    published,
  } = article

  const badgeClass = CATEGORY_BADGE_CLASS[category?.toLowerCase()] || 'badge--general'
  const score = relevance_score ? Math.round(relevance_score * 100) / 100 : null

  const handleVideoClick = (e) => {
    e.stopPropagation()
    onVideoGenerate(title, url)
  }

  return (
    <div className="article-card" id={`article-${title?.substring(0, 20)?.replace(/\s/g, '-')}`}>
      <div className="article-card__header">
        {source && <span className="badge badge--source">{source}</span>}
        {category && <span className={`badge ${badgeClass}`}>{category}</span>}

        {/* ── Matched Interest Badge (proves agent selected for this interest) ── */}
        {matched_interest && (
          <span className="badge badge--matched-interest" title="Selected based on your profile">
            🎯 {matched_interest}
          </span>
        )}

        {tags?.filter(t => t && t !== category && t !== matched_interest).slice(0, 2).map((tag, i) => (
          <span key={i} className="badge badge--source">{tag}</span>
        ))}

        {score !== null && (
          <span className="badge badge--relevance">{score.toFixed(1)}</span>
        )}
      </div>

      <h2 className="article-card__title">{title}</h2>

      {published && (
        <div className="article-card__time">{published}</div>
      )}

      {/* ── Agent Query Context ── */}
      {query_used && agent_curated && (
        <div className="article-card__agent-context">
          <span className="agent-context-label">🔍 Found via:</span>
          <span className="agent-context-query">{query_used}</span>
        </div>
      )}

      {/* ── LLM Selection Reason ── */}
      {reason_for_selection && (
        <div className="article-card__reason">
          <span className="reason-icon">💡</span>
          <span className="reason-text">{reason_for_selection}</span>
        </div>
      )}

      {personalized && Object.keys(personalized).length > 0 && (
        <div className="article-card__insights">
          {/* Dynamic insight rendering — handles all role-based keys */}
          {Object.entries(personalized).map(([key, value]) => {
            if (!value || key === 'headline' || key === 'error' || key === 'raw_output') return null
            
            // Map keys to icons and styles
            const keyConfig = getInsightConfig(key)
            return (
              <div key={key} className={`insight ${keyConfig.className}`}>
                <span className="insight__icon">{keyConfig.icon}</span>
                <div className="insight__content">
                  <div className="insight__label">{keyConfig.label}</div>
                  <div className="insight__text">{value}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="article-card__footer">
        <div className="article-card__footer-left">
          {ai_generated && (
            <div className="ai-indicator">
              <div className="ai-dot" />
              AI Personalized
            </div>
          )}
          {agent_curated && (
            <div className="ai-indicator agent-indicator">
              <div className="ai-dot agent-dot" />
              Agent Curated
            </div>
          )}
        </div>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="read-more">
            Read full article →
          </a>
        )}
      </div>

      <button className="video-trigger" onClick={handleVideoClick}>
        🎬 Create Video Summary
      </button>
    </div>
  )
}


/**
 * Maps personalized insight keys to display config.
 * Handles all role variants (student, investor, founder).
 */
function getInsightConfig(key) {
  const configs = {
    // Common
    summary: { icon: '📋', label: 'AI Summary', className: 'insight--summary' },
    why_this_article: { icon: '🎯', label: 'Why This Article', className: 'insight--highlight' },

    // Student
    simple_explanation: { icon: '📖', label: 'Simple Explanation', className: 'insight--summary' },
    why_it_matters: { icon: '💡', label: 'Why It Matters', className: 'insight--highlight' },
    key_takeaway: { icon: '🎯', label: 'Key Takeaway', className: 'insight--action' },
    key_insight: { icon: '💡', label: 'Key Insight', className: 'insight--highlight' },

    // Investor
    market_impact: { icon: '📊', label: 'Market Impact', className: 'insight--market' },
    stocks_to_watch: { icon: '📈', label: 'Stocks to Watch', className: 'insight--action' },
    investor_action: { icon: '🎯', label: 'Investor Action', className: 'insight--action' },

    // Founder
    startup_relevance: { icon: '🚀', label: 'Startup Relevance', className: 'insight--highlight' },
    opportunity_or_threat: { icon: '⚡', label: 'Opportunity / Threat', className: 'insight--market' },
    action_for_founders: { icon: '🎯', label: 'Action for Founders', className: 'insight--action' },
    action_item: { icon: '🎯', label: 'For You', className: 'insight--action' },
  }

  return configs[key] || {
    icon: '📌',
    label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    className: 'insight--summary',
  }
}
