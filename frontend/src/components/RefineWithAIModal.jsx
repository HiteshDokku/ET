import { useState, useRef, useEffect } from 'react'

export default function RefineWithAIModal({ open, onClose, getAuthHeaders, onRefineComplete }) {
  const [isRecording, setIsRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [message, setMessage] = useState('Tap the microphone to speak your interests.')
  const [error, setError] = useState(null)
  
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioRef = useRef(null)

  // Cleanup on unmount
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
      delete fetchHeaders['Content-Type'] // Let browser set multipart boundary

      const formData = new FormData()
      formData.append('audio', audioBlob, 'input.webm')

      const res = await fetch('/api/auth/voice-to-agent', {
        method: 'POST',
        headers: fetchHeaders,
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        
        // Display confirmation text
        setMessage(data.extracted?.confirmation_message || "Done!")
        
        // Wait 2 seconds for the user to read the message before refreshing
        setTimeout(() => {
          if (data.trigger_scrape) {
            onRefineComplete(data.extracted.interests)
          } else {
            setProcessing(false) // Let user read the clarification request
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
      <div className="profile-setup" style={{ textAlign: 'center', maxWidth: 450 }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
             <button onClick={onClose} style={{ background: 'transparent', border: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-secondary)' }}>✕</button>
        </div>
        
        <div className="profile-setup__title">Refine with AI</div>
        <div className="profile-setup__sub">
          Tell the agent exactly what you want to read about right now.
        </div>

        <div style={{ marginTop: 32, marginBottom: 32 }}>
          {processing ? (
             <div>
                <div className="feed-agent-loading__spinner" style={{ margin: '0 auto 16px' }} />
                <div style={{ color: 'var(--text-secondary)' }}>{message}</div>
             </div>
          ) : (
            <>
               <button 
                  onClick={isRecording ? stopRecording : startRecording}
                  style={{
                    width: '90px', height: '90px', borderRadius: '50%', margin: '0 auto',
                    background: isRecording ? '#ef4444' : 'linear-gradient(135deg, #10b981, #059669)',
                    border: 'none', color: 'white', fontSize: '36px', cursor: 'pointer',
                    boxShadow: isRecording ? '0 0 25px #ef4444' : '0 10px 20px -3px rgba(16,185,129,0.3)',
                    transition: 'all 0.2s ease',
                    display: 'flex', alignItems: 'center', alignContent: 'center', justifyContent: 'center'
                  }}
                >
                  {isRecording ? '⏹️' : '🎙️'}
                </button>
                <div style={{ fontWeight: 600, marginTop: 24, color: isRecording ? '#ef4444' : 'var(--text-primary)' }}>
                  {message}
                </div>
            </>
          )}
        </div>

        {error && (
            <div style={{ color: '#ef4444', fontSize: 13, background: 'rgba(239, 68, 68, 0.1)', paddingStr: 12, borderRadius: 8 }}>
                 {error}
            </div>
        )}
      </div>
    </div>
  )
}
