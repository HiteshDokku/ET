import { useState, useRef, useEffect } from 'react'

export default function RefineWithAIModal({ open, onClose, getAuthHeaders, onRefineComplete }) {
  const [isRecording, setIsRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [message, setMessage] = useState('Tap to dictate your interests.')
  const [error, setError] = useState(null)
  
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioRef = useRef(null)

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop()
        mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop())
      }
    }
  }, [isRecording])

  if (!open) return null

  const startRecording = async () => {
    try {
      setError(null)
      setMessage('Listening... (Tap to Stop)')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []

      mediaRecorderRef.current.ondataavailable = e => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(t => t.stop())
        await processVoice(audioBlob)
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Mic access denied', err)
      setError('Microphone access denied or unavailable.')
      setMessage('Cannot record.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processVoice = async (audioBlob) => {
    setProcessing(true)
    setMessage('Synthesizing profile & generating agent queries...')
    try {
      const headers = await getAuthHeaders()
      const fetchHeaders = { ...headers }
      delete fetchHeaders['Content-Type']

      const formData = new FormData()
      formData.append('audio', audioBlob, 'input.webm')

      const res = await fetch('/api/auth/voice-to-agent', {
        method: 'POST',
        headers: fetchHeaders,
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        setMessage(data.extracted?.confirmation_message || "Done!")
        
        setTimeout(() => {
          if (data.trigger_scrape) {
            onRefineComplete(data.extracted.interests)
          } else {
            setProcessing(false) 
          }
        }, 2500)
        
      } else {
        const errData = await res.json()
        setError(errData.detail || 'Failed to process voice.')
        setMessage('Try again.')
      }
    } catch (err) {
      console.error(err)
      setError('An error occurred communicating with the AI.')
      setMessage('Try again.')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="profile-setup-overlay">
      <div className="profile-setup" style={{ border: '1px solid var(--border)', background: 'var(--bg-secondary)', textAlign: 'center', maxWidth: 450, borderRadius: 0, boxShadow: 'none' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
             <button onClick={onClose} style={{ background: 'transparent', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-secondary)' }}>✕</button>
        </div>
        
        <div className="profile-setup__title" style={{ fontFamily: 'var(--font-headline)', color: 'var(--text)' }}>Refine with AI</div>
        <div className="profile-setup__sub" style={{ fontFamily: 'var(--font-mono)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Tell the agent exactly what you want to read.
        </div>

        <div style={{ marginTop: 32, marginBottom: 32 }}>
          {processing ? (
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ 
                  fontFamily: 'var(--font-mono)', 
                  fontSize: 14, 
                  color: 'var(--text-secondary)',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                  borderRight: '2px solid var(--text)',
                  animation: 'typing 1.5s steps(40, end), blink 0.75s step-end infinite'
                }}>
                  {message}
                </div>
                <style>
                  {`
                    @keyframes typing { from { width: 0 } to { width: 100% } }
                    @keyframes blink { from, to { border-color: transparent } 50% { border-color: var(--text) } }
                  `}
                </style>
             </div>
          ) : (
            <>
               <button 
                  onClick={isRecording ? stopRecording : startRecording}
                  style={{
                    width: '90px', height: '90px', borderRadius: '0', margin: '0 auto',
                    background: isRecording ? 'var(--et-red)' : 'transparent',
                    border: '1px solid var(--border-strong)', color: 'var(--text)', fontSize: '36px', cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex', alignItems: 'center', alignContent: 'center', justifyContent: 'center'
                  }}
                >
                  {isRecording ? '⏹️' : '🎙️'}
                </button>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, marginTop: 24, textTransform: 'uppercase', color: isRecording ? 'var(--et-red)' : 'var(--text-secondary)' }}>
                  {message}
                </div>
            </>
          )}
        </div>

        {error && (
            <div style={{ color: 'var(--et-red)', fontSize: 13, background: 'var(--et-red-light)', border: '1px solid var(--et-red)', padding: 12, borderRadius: 0 }}>
                 {error}
            </div>
        )}
      </div>
    </div>
  )
}
