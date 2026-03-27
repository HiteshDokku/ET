import React, { useState } from 'react'

export default function TopicForm({ onSubmit, error }) {
    const [topic, setTopic] = useState('')
    const [sourceUrl, setSourceUrl] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!topic.trim() && !sourceUrl.trim()) return
        
        let finalTopic = topic.trim()
        if (!finalTopic && sourceUrl.trim()) {
            finalTopic = "the provided news article link"
        }
        
        setLoading(true)
        await onSubmit(finalTopic, sourceUrl)
        setLoading(false)
    }

    return (
        <form className="form-card" onSubmit={handleSubmit}>
            <div className="form-group">
                <label className="form-label" htmlFor="source">
                    Source News Article URL <span style={{ color: "var(--accent-red)", fontWeight: "bold" }}>(Recommended)</span>
                </label>
                <input
                    id="source"
                    className="form-input"
                    type="url"
                    placeholder="https://example.com/breaking-news-article"
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                />
                <div className="form-hint">
                    Directly scrapes the article text and images to generate a 100% accurate video.
                </div>
            </div>

            <div className="form-group">
                <label className="form-label" htmlFor="topic">
                    Custom Topic / Prompt <span style={{ opacity: 0.5 }}>(Optional)</span>
                </label>
                <textarea
                    id="topic"
                    className="form-input"
                    placeholder="e.g., Focus specifically on the financial impact of the event..."
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    maxLength={500}
                />
                <div className="form-hint">
                    Add specific instructions, or use this instead of a URL to let the AI research it from scratch.
                </div>
            </div>

            <button
                type="submit"
                className="submit-btn"
                disabled={loading || (!topic.trim() && !sourceUrl.trim())}
            >
                {loading ? 'Submitting...' : '⚡ Generate News Video'}
            </button>

            {error && <div className="error-msg">{error}</div>}
        </form>
    )
}
