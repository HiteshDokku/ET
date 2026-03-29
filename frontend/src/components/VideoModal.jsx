import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from '../utils/i18n'

const STAGE_ORDER = [
  'queued', 'generating_script', 'planning_visuals', 'sourcing_images',
  'generating_charts', 'generating_voice', 'composing_video', 'running_qa',
]

export default function VideoModal({ job, onClose, language = 'English' }) {
  const { t } = useTranslation(language)
  const [status, setStatus] = useState(null)
  const intervalRef = useRef(null)

  const STAGE_LABELS = {
    queued: t('stage_queued'),
    generating_script: t('stage_generating_script'),
    planning_visuals: t('stage_planning_visuals'),
    sourcing_images: t('stage_sourcing_images'),
    generating_charts: t('stage_generating_charts'),
    generating_voice: t('stage_generating_voice'),
    composing_video: t('stage_composing_video'),
    running_qa: t('stage_running_qa'),
    reflecting: t('stage_reflecting'),
    completed: t('stage_completed'),
    failed: t('stage_failed'),
  }

  const pollStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/video/status/${job.job_id}`)
      if (!res.ok) return
      const data = await res.json()
      setStatus(data)

      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(intervalRef.current)
      }
    } catch (e) {
      console.error('Poll error:', e)
    }
  }, [job.job_id])

  useEffect(() => {
    // If the job was served from cache, it's already completed
    if (job.status === 'completed') {
      setStatus({ ...job, status: 'completed', progress: 1 })
      return
    }

    pollStatus()
    intervalRef.current = setInterval(pollStatus, 3000)
    return () => clearInterval(intervalRef.current)
  }, [job, pollStatus])

  const progress = status ? Math.max((status.progress || 0) * 100, 5) : 5
  const currentStageIdx = status ? STAGE_ORDER.indexOf(status.current_stage) : 0
  const isComplete = status?.status === 'completed'
  const isFailed = status?.status === 'failed'
  const videoUrl = status?.video_url || job?.video_url || `/api/video/download/${job.job_id}`

  return (
    <div className="video-modal-overlay" onClick={onClose}>
      <div className="video-modal" onClick={e => e.stopPropagation()}>
        <div className="video-modal__header">
          <h2 className="video-modal__title">
            {isComplete ? t('video_ready') : isFailed ? t('video_failed') : t('video_generating')}
          </h2>
          <button className="video-modal__close" onClick={onClose}>✕</button>
        </div>

        <div className="video-modal__body">
          {isComplete && videoUrl && (
            <>
              <video
                src={videoUrl}
                controls
                autoPlay
                playsInline
                style={{ aspectRatio: '9/16', maxHeight: 400 }}
              />
              <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                <a
                  href={videoUrl}
                  download
                  className="btn-primary"
                  style={{ textAlign: 'center', textDecoration: 'none' }}
                >
                  {t('video_download')}
                </a>
                <button
                  className="btn-refresh"
                  style={{ flex: 1 }}
                  onClick={onClose}
                >
                  {t('video_close')}
                </button>
              </div>
            </>
          )}

          {isFailed && (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>⚠️</div>
              <div>{status?.error || t('video_failed')}</div>
              <button className="btn-refresh" onClick={onClose} style={{ marginTop: 20 }}>
                {t('video_close')}
              </button>
            </div>
          )}

          {!isComplete && !isFailed && (
            <>
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
                <span>{status?.message || t('video_init')}</span>
                <span>{Math.round(progress)}%</span>
              </div>

              <div className="pipeline-stages">
                {STAGE_ORDER.map((stage, idx) => {
                  let cls = ''
                  if (idx < currentStageIdx) cls = 'completed'
                  else if (idx === currentStageIdx) cls = 'active'

                  return (
                    <div key={stage} className={`stage ${cls}`}>
                      <div className="stage__icon">
                        {cls === 'completed' ? '✓' :
                          cls === 'active' ? <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> :
                            '○'}
                      </div>
                      {STAGE_LABELS[stage]}
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
