import React, { useEffect, useRef, useState } from 'react'

const STAGE_LABELS = {
    queued: 'Queued',
    generating_script: 'Writing Script',
    planning_visuals: 'Planning Visuals',
    sourcing_images: 'Fetching Images',
    generating_charts: 'Creating Charts',
    generating_voice: 'Generating Narration',
    composing_video: 'Composing Video',
    running_qa: 'Quality Check',
    reflecting: 'Improving Quality',
    completed: 'Complete',
    failed: 'Failed',
}

const STAGE_ORDER = [
    'queued',
    'generating_script',
    'planning_visuals',
    'sourcing_images',
    'generating_charts',
    'generating_voice',
    'composing_video',
    'running_qa',
]

export default function JobStatus({ jobId, apiBase, onStatusUpdate }) {
    const [status, setStatus] = useState(null)
    const intervalRef = useRef(null)

    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch(`${apiBase}/status/${jobId}`)
                if (!res.ok) return
                const data = await res.json()
                setStatus(data)
                onStatusUpdate(data)

                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(intervalRef.current)
                }
            } catch (err) {
                console.error('Polling error:', err)
            }
        }

        poll()
        intervalRef.current = setInterval(poll, 3000)

        return () => clearInterval(intervalRef.current)
    }, [jobId, apiBase, onStatusUpdate])

    if (!status) {
        return (
            <div className="status-card">
                <div className="status-header">
                    <span className="status-title">Initializing...</span>
                    <span className="status-badge processing">Starting</span>
                </div>
                <div className="progress-bar">
                    <div className="progress-fill" style={{ width: '5%' }} />
                </div>
            </div>
        )
    }

    const currentStageIdx = STAGE_ORDER.indexOf(status.current_stage)
    const progress = Math.max(status.progress * 100, 5)

    return (
        <div className="status-card">
            <div className="status-header">
                <span className="status-title">Generating Video</span>
                <span className="status-badge processing">
                    {status.iteration > 0 ? `Iteration ${status.iteration + 1}` : 'Processing'}
                </span>
            </div>

            <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>

            <div className="progress-text">{status.message}</div>
            <div className="progress-percent">{Math.round(progress)}%</div>

            <div className="pipeline-stages">
                {STAGE_ORDER.map((stage, idx) => {
                    let stageClass = ''
                    if (idx < currentStageIdx) stageClass = 'completed'
                    else if (idx === currentStageIdx) stageClass = 'active'

                    return (
                        <div key={stage} className={`stage ${stageClass}`}>
                            <div className="stage-icon">
                                {stageClass === 'completed' ? '✓' :
                                    stageClass === 'active' ? <div className="spinner" /> :
                                        '○'}
                            </div>
                            {STAGE_LABELS[stage]}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
