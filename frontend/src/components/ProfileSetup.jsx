import { useState } from 'react'

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

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'bn', name: 'Bengali' },
  { code: 'te', name: 'Telugu' },
  { code: 'mr', name: 'Marathi' },
  { code: 'ta', name: 'Tamil' },
  { code: 'gu', name: 'Gujarati' },
  { code: 'ur', name: 'Urdu' },
  { code: 'kn', name: 'Kannada' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'pa', name: 'Punjabi' }
]

export default function ProfileSetup({ onComplete }) {
  const [role, setRole] = useState('student')
  const [language, setLanguage] = useState('en')
  const [interests, setInterests] = useState([])
  const [level, setLevel] = useState('beginner')
  const [saving, setSaving] = useState(false)

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
    await onComplete({ role, interests, level, preferred_language: language })
    setSaving(false)
  }

  return (
    <div className="profile-setup-overlay">
      <div className="profile-setup">
        <div className="profile-setup__title">Welcome to ET</div>
        <div className="profile-setup__sub">
          Tell us about yourself to personalize your newsroom
        </div>

        {/* Language Selection */}
        <div className="form-group">
          <label className="form-label">Preferred Language</label>
          <select
            className="form-select"
            value={language}
            onChange={e => setLanguage(e.target.value)}
          >
            {LANGUAGES.map(l => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
        </div>

        {/* Role Selection */}
        <div className="form-group">
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

        <button
          className="btn-primary"
          onClick={handleSave}
          disabled={interests.length < 3 || saving}
        >
          {saving ? 'Setting up...' : `Start Reading (${interests.length} interests)`}
        </button>

        {interests.length < 3 && (
          <div className="form-hint" style={{ textAlign: 'center', marginTop: 8 }}>
            Select at least 3 interests to continue
          </div>
        )}
      </div>
    </div>
  )
}
