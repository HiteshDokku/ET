import React, { useState } from 'react'
import TopicForm from './components/TopicForm'
import JobStatus from './components/JobStatus'
import VideoPlayer from './components/VideoPlayer'

const API_BASE = '/api'

export default function App() {
    const [jobId, setJobId] = useState(null)
    const [status, setStatus] = useState(null)
    const [error, setError] = useState(null)

    const handleSubmit = async (topic, sourceUrl) => {
        setError(null)
        setStatus(null)
        setJobId(null)

        try {
            const res = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, source_url: sourceUrl || null }),
            })

            const contentType = res.headers.get('content-type') || ''
            if (!contentType.includes('application/json')) {
                throw new Error('Server is temporarily unavailable. Please try again in a few seconds.')
            }

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || 'Failed to start generation')
            }

            const data = await res.json()
            setJobId(data.job_id)
        } catch (err) {
            setError(err.message)
        }
    }

    const handleStatusUpdate = (newStatus) => {
        setStatus(newStatus)
    }

    const handleReset = () => {
        setJobId(null)
        setStatus(null)
        setError(null)
    }

    const isCompleted = status?.status === 'completed'
    const isFailed = status?.status === 'failed'

    return (
        <div className="app">
            <header className="header">
                <div className="logo">
                    <div className="logo-icon">▶</div>
                    <span className="logo-text">NewsAgent</span>
                    <span className="logo-badge">Pro</span>
                </div>
                <div className="header-status">
                    <div className="status-dot"></div>
                    System Online
                </div>
            </header>

            <main className="main">
                <div className="hero">
                    <h1>AI News Video Generator</h1>
                    <p>
                        Generate broadcast-quality news videos from any topic.
                        Powered by Gemini AI, ElevenLabs, and cinematic composition.
                    </p>
                </div>

                {!jobId && (
                    <TopicForm onSubmit={handleSubmit} error={error} />
                )}

                {jobId && !isCompleted && !isFailed && (
                    <JobStatus
                        jobId={jobId}
                        apiBase={API_BASE}
                        onStatusUpdate={handleStatusUpdate}
                    />
                )}

                {isCompleted && status?.video_url && (
                    <VideoPlayer
                        videoUrl={status.video_url}
                        qaReport={status.qa_report}
                        onNewVideo={handleReset}
                    />
                )}

                {isFailed && (
                    <div className="status-card">
                        <div className="status-header">
                            <span className="status-title">Generation Failed</span>
                            <span className="status-badge failed">Failed</span>
                        </div>
                        <div className="error-msg">
                            {status?.error || status?.message || 'An unexpected error occurred'}
                        </div>
                        <button
                            className="new-btn"
                            style={{ marginTop: 20, width: '100%' }}
                            onClick={handleReset}
                        >
                            Try Again
                        </button>
                    </div>
                )}
            </main>
        </div>
    )
}
