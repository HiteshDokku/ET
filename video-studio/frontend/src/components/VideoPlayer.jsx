import React from 'react'

export default function VideoPlayer({ videoUrl, qaReport, onNewVideo }) {
    const getScoreColor = (score) => {
        if (score >= 0.9) return 'var(--success)'
        if (score >= 0.7) return 'var(--warning)'
        return 'var(--accent-red)'
    }

    return (
        <div className="video-card">
            <div className="status-header">
                <span className="status-title">Video Ready</span>
                <span className="status-badge completed">Complete</span>
            </div>

            <div className="video-wrapper">
                <video
                    src={videoUrl}
                    controls
                    autoPlay
                    playsInline
                    style={{ aspectRatio: '9/16' }}
                />
            </div>

            <div className="video-actions">
                <a
                    href={videoUrl}
                    download
                    className="download-btn"
                >
                    ↓ Download MP4
                </a>
                <button className="new-btn" onClick={onNewVideo}>
                    + New Video
                </button>
            </div>

            {qaReport && (
                <div className="qa-report">
                    <div className="qa-title">Quality Report</div>
                    <div className={`qa-score ${qaReport.passed ? 'pass' : 'fail'}`}>
                        {(qaReport.overall_score * 100).toFixed(1)}%
                    </div>

                    <div className="qa-dimensions">
                        {qaReport.dimension_scores?.map((dim) => (
                            <div key={dim.dimension} className="qa-dim">
                                <span className="qa-dim-name">
                                    {dim.dimension.replace('_', ' ')}
                                </span>
                                <div className="qa-dim-bar">
                                    <div
                                        className="qa-dim-fill"
                                        style={{
                                            width: `${dim.score * 100}%`,
                                            background: getScoreColor(dim.score),
                                        }}
                                    />
                                </div>
                                <span className="qa-dim-value">
                                    {(dim.score * 100).toFixed(0)}%
                                </span>
                            </div>
                        ))}
                    </div>

                    {qaReport.hard_fail_triggered?.length > 0 && (
                        <div className="error-msg" style={{ marginTop: 16 }}>
                            ⚠ Issues: {qaReport.hard_fail_triggered.join(', ')}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
