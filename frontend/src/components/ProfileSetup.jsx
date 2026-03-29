import { useState, useRef, useEffect } from 'react'

const ROLES = [
  { id: 'student', icon: '—', label: 'Student' },
  { id: 'investor', icon: '—', label: 'Investor' },
  { id: 'founder', icon: '—', label: 'Founder' },
]

const LEVELS = ['beginner', 'intermediate', 'advanced']

const INTEREST_SUGGESTIONS = [
  'AI & Machine Learning', 'Startups', 'Stock Markets', 'Crypto',
  'Banking', 'Real Estate', 'Electric Vehicles', 'Fintech',
  'Global Economy', 'Indian Economy', 'Technology', 'IPOs',
  'Government Policy', 'Climate & ESG', 'Healthcare',
]

const LANGUAGES = [
  { id: 'English', label: 'English' },
  { id: 'Hindi', label: 'Hindi' },
  { id: 'Marathi', label: 'Marathi' },
  { id: 'Telugu', label: 'Telugu' },
  { id: 'Kannada', label: 'Kannada' },
]

export default function ProfileSetup({ initialProfile, initialMode, onComplete, onCancel, getAuthHeaders, onVoiceComplete }) {
  const isUpdate = (initialProfile?.interests && initialProfile.interests.length > 0)
  const [mode, setMode] = useState(initialMode || (isUpdate ? 'manual' : 'landing'))

  const [role, setRole] = useState(initialProfile?.role || 'student')
  const [interests, setInterests] = useState(initialProfile?.interests || [])
  const [level, setLevel] = useState(initialProfile?.level || 'beginner')
  const [preferredLanguage, setPreferredLanguage] = useState(initialProfile?.preferred_language || 'English')
  const [saving, setSaving] = useState(false)

  const [isRecording, setIsRecording] = useState(false)
  const [processingVoice, setProcessingVoice] = useState(false)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [aiQuestion, setAiQuestion] = useState('')
  const [interviewHistory, setInterviewHistory] = useState([])
  const [interviewInitialized, setInterviewInitialized] = useState(false)

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
    await onComplete({ role, interests, level, preferred_language: preferredLanguage })
    setSaving(false)
  }

  const sendInterviewTurn = async (audioBlob) => {
    setProcessingVoice(true)
    try {
      const headers = await getAuthHeaders()
      const fetchHeaders = { ...headers }
      delete fetchHeaders['Content-Type']

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

        if (data.extracted) {
          if (data.extracted.role && data.extracted.role !== "null") setRole(data.extracted.role)
          if (data.extracted.level && data.extracted.level !== "null") setLevel(data.extracted.level)
          if (data.extracted.interests && data.extracted.interests.length > 0) setInterests(data.extracted.interests)
        }

        if (data.status === 'COMPLETE') {
          if (onVoiceComplete) onVoiceComplete(data.extracted)
          return
        }

        setInterviewHistory(data.history || [])
        setAiQuestion(data.question || '')

        if (data.audio_base64) {
          setIsPlayingAudio(true)
          const audio = new Audio(`data:audio/mp3;base64,${data.audio_base64}`)
          audioRef.current = audio
          audio.onended = () => {
            setIsPlayingAudio(false)
            startRecording()
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
        stream.getTracks().forEach(t => t.stop())
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

  // Common input/select style simulating printed form line
  const formStyle = {
    width: '100%',
    padding: '8px 0',
    background: 'transparent',
    border: 'none',
    borderBottom: '1px solid var(--border-strong)',
    borderRadius: 0,
    color: 'var(--text)',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    outline: 'none',
    marginBottom: '24px'
  }

  return (
    <div className="profile-setup-overlay">
      <div className="profile-setup" style={{ border: '1px solid var(--border)', background: 'var(--bg)', borderRadius: 0, boxShadow: 'none' }}>
        <div className="profile-setup__title" style={{ fontFamily: 'var(--font-headline)', color: 'var(--text)', textTransform: 'uppercase' }}>Configuration</div>
        <div className="profile-setup__sub" style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Please set your editorial preferences
        </div>

        {mode === 'landing' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 24 }}>
            <button 
              onClick={() => setMode('manual')}
              style={{ padding: '16px', fontSize: '14px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text)', cursor: 'pointer' }}
            >
              [ MANUAL INPUT ]
            </button>
            <button 
              onClick={() => setMode('voice')}
              style={{ padding: '16px', fontSize: '14px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', background: 'var(--et-red)', border: '1px solid var(--et-red)', color: '#fff', cursor: 'pointer' }}
            >
              [ VOICE INTERFACE ]
            </button>
          </div>
        )}

        {mode === 'voice' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: 32, gap: 24 }}>
            {!interviewInitialized ? (
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: 'var(--text-secondary)', marginBottom: 24, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                  Voice agent initialized. Please enable microphone.
                </div>
                <button 
                  onClick={() => {
                    setInterviewInitialized(true)
                    sendInterviewTurn(null)
                  }}
                  style={{ background: 'var(--et-red)', color: 'white', border: 'none', fontSize: "14px", fontFamily: 'var(--font-mono)', padding: '16px 24px', cursor: 'pointer', textTransform: 'uppercase' }}
                >
                  [ INITIATE CONNECTION ]
                </button>
              </div>
            ) : !processingVoice ? (
              <>
                {isPlayingAudio ? (
                  <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>SYS: TRANSMITTING</div>
                    <div style={{ fontSize: 13, fontStyle: 'italic', fontFamily: 'var(--font-headline)' }}>"{aiQuestion}"</div>
                  </div>
                ) : (
                  <>
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                      <div style={{ fontSize: 13, fontStyle: 'italic', fontFamily: 'var(--font-headline)', marginBottom: 12 }}>"{aiQuestion}"</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>AWAITING RESPONSE...</div>
                    </div>
                    <button 
                      onClick={isRecording ? stopRecording : startRecording}
                      style={{
                        width: '80px', height: '80px', borderRadius: '0',
                        background: isRecording ? 'var(--et-red)' : 'transparent',
                        border: '1px solid var(--border)', color: 'var(--text)', fontSize: '24px', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', alignContent: 'center', justifyContent: 'center'
                      }}
                    >
                      {isRecording ? '⏹' : 'REC'}
                    </button>
                  </>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                <div>PROCESSING SIGNAL...</div>
              </div>
            )}
            
            <div style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: '12px 24px', fontSize: 11, marginTop: 12, display: 'flex', gap: 16, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              <div>ROLE: {role}</div>
              <div>LEVEL: {level}</div>
              <div>TAGS: {interests.length}</div>
            </div>

            <button 
              onClick={() => {
                 if (audioRef.current) audioRef.current.pause()
                 stopRecording()
                 setMode('manual')
              }}
              style={{ marginTop: 16, border: 'none', background: 'transparent', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer', textTransform: 'uppercase' }}
              disabled={processingVoice}
            >
              [ ABORT VOICE / MANUAL EDIT ]
            </button>
          </div>
        )}

        {mode === 'manual' && (
          <>
            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label" style={{ fontFamily: 'var(--font-mono)' }}>LANGUAGE EDITION</label>
              <select style={formStyle} value={preferredLanguage} onChange={e => setPreferredLanguage(e.target.value)}>
                {LANGUAGES.map(lang => (
                  <option key={lang.id} value={lang.id} style={{ background: 'var(--bg)', color: 'var(--text)' }}>
                    {lang.id} - {lang.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label" style={{ fontFamily: 'var(--font-mono)' }}>PROFILE CLASS</label>
              <select style={formStyle} value={role} onChange={e => setRole(e.target.value)}>
                {ROLES.map(r => (
                  <option key={r.id} value={r.id} style={{ background: 'var(--bg)', color: 'var(--text)' }}>
                    {r.label.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label" style={{ fontFamily: 'var(--font-mono)' }}>EXPERIENCE LEVEL</label>
              <select style={formStyle} value={level} onChange={e => setLevel(e.target.value)}>
                {LEVELS.map(l => (
                  <option key={l} value={l} style={{ background: 'var(--bg)', color: 'var(--text)' }}>
                    {l.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontFamily: 'var(--font-mono)' }}>TRACKED ENTITIES (MIN 3)</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                {INTEREST_SUGGESTIONS.map(interest => {
                  const isSelected = interests.includes(interest);
                  return (
                    <button
                      key={interest}
                      style={{ 
                        cursor: 'pointer', 
                        padding: '6px 12px', 
                        fontSize: 11, 
                        fontFamily: 'var(--font-mono)', 
                        textTransform: 'uppercase',
                        background: isSelected ? 'var(--et-red)' : 'transparent',
                        color: isSelected ? '#fff' : 'var(--text-secondary)',
                        border: `1px solid ${isSelected ? 'var(--et-red)' : 'var(--border)'}`,
                        borderRadius: 0
                      }}
                      onClick={() => toggleInterest(interest)}
                    >
                      {interest}
                    </button>
                  )
                })}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12, marginTop: 32 }}>
              {isUpdate && onCancel && (
                <button
                  onClick={onCancel}
                  disabled={saving}
                  style={{ flex: 1, padding: '12px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', fontSize: 13 }}
                >
                  [ CANCEL ]
                </button>
              )}
              <button
                onClick={handleSave}
                disabled={interests.length < 3 || saving}
                style={{ flex: 2, padding: '12px', background: 'var(--text)', color: 'var(--bg)', border: 'none', cursor: interests.length < 3 ? 'not-allowed' : 'pointer', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', fontSize: 13, opacity: interests.length < 3 ? 0.5 : 1 }}
              >
                [ {saving ? 'CONFIRMING...' : 'SAVE CONFIGURATION'} ]
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
