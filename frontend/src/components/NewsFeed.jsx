import { useState, useEffect } from 'react'
import ArticleCard from './ArticleCard'
import { useTranslation } from '../utils/i18n'

const API = '/api'

export default function NewsFeed({ profile, getAuthHeaders, onVideoGenerate, onProfileSetupRequired }) {
  const { t } = useTranslation(profile?.preferred_language || 'English')
  
  const AGENT_STEPS = [
    { icon: '🔍', text: t('agent_step_1') },
    { icon: '📡', text: t('agent_step_2') },
    { icon: '🧠', text: t('agent_step_3') },
    { icon: '🔄', text: t('agent_step_4') },
    { icon: '✍️', text: t('agent_step_5') },
  ]

  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [agentStep, setAgentStep] = useState(0)
  const [elapsed, setElapsed] = useState(null)

  const fetchFeed = async (forceRefresh = false) => {
    setLoading(true)
    setError(null)
    setAgentStep(0)
    try {
      const headers = await getAuthHeaders()
      const url = forceRefresh
        ? `${API}/news/feed?force_refresh=true`
        : `${API}/news/feed`
      const res = await fetch(url, { headers })
      if (!res.ok) {
        if (res.status === 400 && onProfileSetupRequired) {
          onProfileSetupRequired();
          return;
        }
        throw new Error(`Server error: ${res.status}`)
      }
      const data = await res.json()
      setArticles(data.articles || [])
      setElapsed(data.elapsed_seconds || null)
    } catch (e) {
      console.error('Feed error:', e)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { 
    if (profile) fetchFeed() 
  }, [profile?.role])

  // Animate through agent steps during loading
  useEffect(() => {
    if (!loading) return
    const interval = setInterval(() => {
      setAgentStep(prev => (prev + 1) % AGENT_STEPS.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [loading])

  if (loading) {
    return (
      <>
        <div className="feed-header">
          <div>
            <h1 className="feed-title">{t('feed_title')}</h1>
            <div className="feed-count">{t('feed_loading')}</div>
          </div>
        </div>

        {/* ── Agentic Loading UI ─────────────────────────── */}
        <div className="feed-agent-loading">
          <div className="feed-agent-loading__spinner" />
          <div className="feed-agent-loading__step">
            <span className="feed-agent-loading__icon">
              {AGENT_STEPS[agentStep].icon}
            </span>
            <span className="feed-agent-loading__text">
              {AGENT_STEPS[agentStep].text}
            </span>
          </div>
          <div className="feed-agent-loading__pipeline">
            {AGENT_STEPS.map((step, i) => (
              <div
                key={i}
                className={`feed-agent-loading__dot ${i <= agentStep ? 'active' : ''} ${i === agentStep ? 'current' : ''}`}
                title={step.text}
              />
            ))}
          </div>
          {profile?.interests && (
            <div className="feed-agent-loading__interests">
              {profile.interests.map((interest, i) => (
                <span key={i} className="feed-agent-loading__chip">{interest}</span>
              ))}
            </div>
          )}
        </div>

        {[1, 2, 3, 4].map(i => (
          <div key={i} className="skeleton-card">
            <div className="skeleton skeleton--sm" />
            <div className="skeleton skeleton--lg" />
            <div className="skeleton skeleton--md" />
            <div className="skeleton skeleton--block" />
          </div>
        ))}
      </>
    )
  }

  if (error) {
    return (
      <>
        <div className="feed-header">
          <div>
            <h1 className="feed-title">{t('feed_title')}</h1>
          </div>
        </div>
        <div style={{
          padding: 40,
          textAlign: 'center',
          color: 'var(--text-secondary)',
        }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>📰</div>
          <div style={{ marginBottom: 8 }}>Unable to load your feed</div>
          <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginBottom: 20 }}>{error}</div>
          <button className="btn-refresh" onClick={fetchFeed}>↻ Try Again</button>
        </div>
      </>
    )
  }

  // Check if feed was agent-curated
  const isAgentCurated = articles.length > 0 && articles[0]?.agent_curated

  // Compute interest distribution
  const interestCounts = {}
  articles.forEach(a => {
    if (a.matched_interest) {
      interestCounts[a.matched_interest] = (interestCounts[a.matched_interest] || 0) + 1
    }
  })
  const matchedInterests = Object.keys(interestCounts)
  const hasInterestData = matchedInterests.length > 0

  return (
    <>
      <div className="feed-header">
        <div>
          <h1 className="feed-title">{t('feed_title')}</h1>
          <div className="feed-count">
            {articles.length} {t('feed_articles_for')} {profile?.role || 'you'}
            {isAgentCurated && ` · ${t('feed_agent_curated')}`}
            {elapsed && ` · ${elapsed}s`}
          </div>
        </div>
        <button className="btn-refresh" onClick={() => fetchFeed(true)}>
          {t('feed_refresh')}
        </button>
      </div>

      {/* ── Interest Coverage Banner ─────────────────────── */}
      {hasInterestData && (
        <div className="feed-agent-banner">
          <div className="feed-agent-banner__header">
            <span className="feed-agent-dot" />
            <span className="feed-agent-label">
              {isAgentCurated ? t('feed_agent') : t('feed_personal')}
            </span>
            <span className="feed-agent-sublabel">
              {isAgentCurated
                ? t('feed_agent_sub')
                : t('feed_personal_sub')}
            </span>
          </div>
          <div className="feed-agent-banner__interests">
            {matchedInterests.map((interest, i) => (
              <span key={i} className="feed-interest-chip">
                🎯 {interest}
                <span className="feed-interest-count">{interestCounts[interest]}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {articles.length === 0 ? (
        <div style={{
          padding: 60,
          textAlign: 'center',
          color: 'var(--text-secondary)',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🗞️</div>
          <div>{t('feed_empty')}</div>
          <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 8 }}>
            Try refreshing or updating your interests in the profile.
          </div>
        </div>
      ) : (
        articles.map((article, i) => (
          <ArticleCard
            key={i}
            article={article}
            onVideoGenerate={onVideoGenerate}
            language={profile?.preferred_language || 'English'}
          />
        ))
      )}
    </>
  )
}
