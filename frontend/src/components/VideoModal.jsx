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
    <div className="video-modal-overlay" onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 400
    }}>
      <div className="video-modal" onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-strong)', padding: 32, width: '90%', maxWidth: 500, fontFamily: 'var(--font-mono)'
      }}>
        <div className="video-modal__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
          <h2 className="video-modal__title" style={{ fontFamily: 'var(--font-mono)', fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0, color: 'var(--text)' }}>
            [ {isComplete ? t('video_ready') : isFailed ? t('video_failed') : "SYSTEM_RENDER"} ]
          </h2>
          <button className="video-modal__close" onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}>[ X ]</button>
        </div>

        <div className="video-modal__body">
          {isComplete && videoUrl && (
            <>
              <video
                src={videoUrl}
                controls
                autoPlay
                playsInline
                style={{ aspectRatio: '9/16', maxHeight: 400, width: '100%', objectFit: 'contain', border: '1px solid var(--border)' }}
              />
              <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
                <a
                  href={videoUrl}
                  download
                  className="btn-primary"
                  style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, fontFamily: 'var(--font-mono)', fontSize: 13, textTransform: 'uppercase', borderRadius: 0 }}
                >
                  [ {t('video_download')} ]
                </a>
              </div>
            </>
          )}

          {isFailed && (
            <div style={{ textAlign: 'center', padding: 40, border: '1px solid var(--et-red)', background: 'var(--et-red-light)' }}>
              <div style={{ fontSize: 24, marginBottom: 16, color: 'var(--et-red)' }}>[ ERR ]</div>
              <div style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--text)' }}>{status?.error || t('video_failed')}</div>
            </div>
          )}

          {!isComplete && !isFailed && (
            <>
              <div className="progress-bar" style={{ height: 2, background: 'var(--border-strong)', marginBottom: 12, position: 'relative' }}>
                <div className="progress-bar__fill" style={{ width: `${progress}%`, height: '100%', background: 'var(--et-red)', transition: 'width 0.5s ease' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)', marginBottom: 32, textTransform: 'uppercase' }}>
                <span>{status?.message || t('video_init')}</span>
                <span>[{Math.round(progress)}%]</span>
              </div>

              <div className="pipeline-stages" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {STAGE_ORDER.map((stage, idx) => {
                  let cls = ''
                  if (idx < currentStageIdx) cls = 'completed'
                  else if (idx === currentStageIdx) cls = 'active'

                  return (
                    <div key={stage} className={`stage ${cls}`} style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: cls === 'active' ? 'var(--et-red)' : cls === 'completed' ? 'var(--text-secondary)' : 'var(--text-tertiary)', textTransform: 'uppercase' }}>
                      <div className="stage__icon" style={{ width: 16 }}>
                        {cls === 'completed' ? '[+]' :
                          cls === 'active' ? '[*]' : '[-]'}
                      </div>
                      <span style={{ fontWeight: cls === 'active' ? 700 : 400 }}>{STAGE_LABELS[stage]}</span>
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
