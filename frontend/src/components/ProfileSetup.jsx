import { useState, useRef, useEffect } from 'react'

const ROLES = [
  { id: 'student', icon: '🎓', label: 'Student' },
  { id: 'investor', icon: '💼', label: 'Investor' },
  { id: 'founder', icon: '🚀', label: 'Founder' },
]

const LEVELS = ['beginner', 'intermediate', 'advanced']

const INTEREST_SUGGESTIONS = [
  'AI & Machine Learning', 'Startups', 'Stock Markets', 'Crypto',
  'Banking', 'Real Estate', 'Electric Vehicles', 'Fintech',
  'Global Economy', 'Indian Economy', 'Technology', 'IPOs',
  'Government Policy', 'Climate & ESG', 'Healthcare',
]

export default function ProfileSetup({ initialProfile, initialMode, onComplete, onCancel, getAuthHeaders, onVoiceComplete }) {
  const isUpdate = (initialProfile?.interests && initialProfile.interests.length > 0)
  const [mode, setMode] = useState(initialMode || (isUpdate ? 'manual' : 'landing'))

  // Manual state
  const [role, setRole] = useState(initialProfile?.role || 'student')
  const [interests, setInterests] = useState(initialProfile?.interests || [])
  const [level, setLevel] = useState(initialProfile?.level || 'beginner')
  const [saving, setSaving] = useState(false)

  // Voice AI Interview state
  const [isRecording, setIsRecording] = useState(false)
  const [processingVoice, setProcessingVoice] = useState(false)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [aiQuestion, setAiQuestion] = useState('')
  const [interviewHistory, setInterviewHistory] = useState([])
  const [interviewInitialized, setInterviewInitialized] = useState(false)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioRef = useRef(null)

  // Cleanup audio on unmount
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


  const toggleInterest = (interest) => {
    setInterests(prev =>
      prev.includes(interest)
        ? prev.filter(i => i !== interest)
        : [...prev, interest]
    )
  }

  const handleSave = async () => {
    if (interests.length === 0) return
    setSaving(true)
    await onComplete({ role, interests, level })
    setSaving(false)
  }

  const sendInterviewTurn = async (audioBlob) => {
    setProcessingVoice(true)
    try {
      const headers = await getAuthHeaders()
      const fetchHeaders = { ...headers }
      delete fetchHeaders['Content-Type'] // Let browser set multipart boundary

      const formData = new FormData()
      if (audioBlob) {
        formData.append('audio', audioBlob, 'turn.webm')
      }

      const statePayload = {
        history: interviewHistory,
        role,
        level,
        interests
      }
      formData.append('state', JSON.stringify(statePayload))

      const res = await fetch('/api/auth/interview/next', {
        method: 'POST',
        headers: fetchHeaders,
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()

        // Sync local explicit state context for next turns
        if (data.extracted) {
          if (data.extracted.role && data.extracted.role !== "null") setRole(data.extracted.role)
          if (data.extracted.level && data.extracted.level !== "null") setLevel(data.extracted.level)
          if (data.extracted.interests && data.extracted.interests.length > 0) setInterests(data.extracted.interests)
        }

        if (data.status === 'COMPLETE') {
          if (onVoiceComplete) onVoiceComplete(data.extracted)
          return
        }

        // It is CONTINUE.
        setInterviewHistory(data.history || [])
        setAiQuestion(data.question || '')

        if (data.audio_base64) {
          setIsPlayingAudio(true)
          const audio = new Audio(`data:audio/mp3;base64,${data.audio_base64}`)
          audioRef.current = audio
          audio.onended = () => {
            setIsPlayingAudio(false)
            startRecording() // Autostart the microphone immediately after the AI stops talking
          }
          const playPromise = audio.play()
          if (playPromise !== undefined) {
            playPromise.catch(e => {
              console.warn('Autoplay prevented:', e)
              setIsPlayingAudio(false)
              startRecording()
            })
          }
        } else {
          // Fallback if no audio was generated for some reason
          startRecording()
        }

      } else {
        console.error('Interview turn failed')
        setMode('manual')
      }
    } catch (err) {
      console.error(err)
      setMode('manual')
    } finally {
      setProcessingVoice(false)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []

      mediaRecorderRef.current.ondataavailable = e => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' })
        // Clean up the stream tracks
        stream.getTracks().forEach(t => t.stop())
        // Immediately trigger next turn
        sendInterviewTurn(audioBlob)
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Mic access denied', err)
      setMode('manual')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  return (
    <div className="profile-setup-overlay">
      <div className="profile-setup">
        <div className="profile-setup__title">Welcome to ET</div>
        <div className="profile-setup__sub">
          Tell us about yourself to personalize your newsroom
        </div>

        {mode === 'landing' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 24 }}>
            <button 
              className="btn-primary" 
              onClick={() => setMode('manual')}
              style={{ padding: '16px', fontSize: '18px' }}
            >
              📝 Fast Manual Setup
            </button>
            <button 
              className="btn-primary" 
              onClick={() => setMode('voice')}
              style={{ padding: '16px', fontSize: '18px', background: 'linear-gradient(135deg, #10b981, #059669)' }}
            >
              🎙️ Talk to AI Assistant
            </button>
          </div>
        )}

        {mode === 'voice' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 32, gap: 24 }}>
            {!interviewInitialized ? (
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
                  Ensure your audio is unmuted. The AI will speak first and guide you through setting up your profile.
                </div>
                <button 
                  className="btn-primary" 
                  onClick={() => {
                    setInterviewInitialized(true)
                    sendInterviewTurn(null)
                  }}
                  style={{ background: 'linear-gradient(135deg, #10b981, #059669)', fontSize: "18px", padding: '16px' }}
                >
                  ▶️ Start Interview
                </button>
              </div>
            ) : !processingVoice ? (
              <>
                {isPlayingAudio ? (
                  <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <div style={{ fontSize: 24, marginBottom: 8 }}>🔊</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>AI is speaking...</div>
                    <div style={{ fontSize: 14, fontStyle: 'italic', marginTop: 12 }}>"{aiQuestion}"</div>
                  </div>
                ) : (
                  <>
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                      <div style={{ fontSize: 14, fontStyle: 'italic', marginBottom: 12 }}>"{aiQuestion}"</div>
                      <div>It is your turn to speak.</div>
                    </div>
                    <button 
                      onClick={isRecording ? stopRecording : startRecording}
                      style={{
                        width: '80px', height: '80px', borderRadius: '50%',
                        background: isRecording ? '#ef4444' : 'linear-gradient(135deg, #10b981, #059669)',
                        border: 'none', color: 'white', fontSize: '32px', cursor: 'pointer',
                        boxShadow: isRecording ? '0 0 20px #ef4444' : '0 10px 15px -3px rgba(16,185,129,0.3)',
                        transition: 'all 0.2s ease',
                        display: 'flex', alignItems: 'center', alignContent: 'center', justifyContent: 'center'
                      }}
                    >
                      {isRecording ? '⏹️' : '🎙️'}
                    </button>
                    <div style={{ fontWeight: 600, color: isRecording ? '#ef4444' : 'var(--text-primary)' }}>
                      {isRecording ? 'Listening (Tap to Stop)...' : 'Tap to Record'}
                    </div>
                  </>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center' }}>
                <div className="spinner" style={{ margin: '0 auto 16px' }} />
                <div>AI is thinking...</div>
              </div>
            )}
            
            <div style={{ background: 'var(--bg-secondary)', padding: '12px 24px', borderRadius: 8, fontSize: 12, marginTop: 12, display: 'flex', gap: 16 }}>
              <div><strong>Role:</strong> {role}</div>
              <div><strong>Level:</strong> {level}</div>
              <div><strong>Interests:</strong> {interests.length} set</div>
            </div>

            <button 
              className="btn-secondary" 
              onClick={() => {
                 if (audioRef.current) audioRef.current.pause()
                 stopRecording()
                 setMode('manual')
              }}
              style={{ marginTop: 16, border: 'none', background: 'transparent' }}
              disabled={processingVoice}
            >
              Switch to Manual Setup
            </button>
          </div>
        )}

        {mode === 'manual' && (
          <>
            {/* Role Selection */}
            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label">I am a</label>
              <div className="role-cards">
                {ROLES.map(r => (
                  <button
                    key={r.id}
                    className={`role-card ${role === r.id ? 'selected' : ''}`}
                    onClick={() => setRole(r.id)}
                  >
                    <div className="role-card__icon">{r.icon}</div>
                    <div className="role-card__label">{r.label}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Interests */}
            <div className="form-group">
              <label className="form-label">I'm interested in (select 3+)</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {INTEREST_SUGGESTIONS.map(interest => (
                  <button
                    key={interest}
                    className={`badge ${interests.includes(interest) ? 'badge--relevance' : 'badge--source'}`}
                    style={{ cursor: 'pointer', padding: '6px 12px', fontSize: 12 }}
                    onClick={() => toggleInterest(interest)}
                  >
                    {interest}
                  </button>
                ))}
              </div>
            </div>

            {/* Experience Level */}
            <div className="form-group">
              <label className="form-label">My experience level</label>
              <select
                className="form-select"
                value={level}
                onChange={e => setLevel(e.target.value)}
              >
                {LEVELS.map(l => (
                  <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
              {isUpdate && onCancel && (
                <button
                  className="btn-secondary"
                  onClick={onCancel}
                  disabled={saving}
                  style={{ flex: 1, padding: '12px', border: '1px solid var(--border-color)', borderRadius: '8px', background: 'transparent', color: 'var(--text-primary)', cursor: 'pointer', fontWeight: 600 }}
                >
                  Cancel
                </button>
              )}
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={interests.length < 3 || saving}
                style={{ flex: 2 }}
              >
                {saving ? (isUpdate ? 'Saving...' : 'Setting up...') : (isUpdate ? 'Save Changes' : `Start Reading (${interests.length} interests)`)}
              </button>
            </div>

            {interests.length < 3 && (
              <div className="form-hint" style={{ textAlign: 'center', marginTop: 8 }}>
                Select at least 3 interests to continue
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
