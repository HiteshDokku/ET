import { useState, useEffect, useCallback } from 'react'
import { useUser, useAuth, SignInButton, UserButton } from '@clerk/clerk-react'
import Navbar from '../components/Navbar'
import NewsFeed from '../components/NewsFeed'
import AISidebar from '../components/AISidebar'
import VideoModal from '../components/VideoModal'
import ProfileSetup from '../components/ProfileSetup'
import { useTranslation } from '../utils/i18n'

const API = '/api'

export default function DashboardPage() {
  const clerkAvailable = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
  let user = null, isSignedIn = false, isLoaded = true

  let getTokenFn = async () => null

  if (clerkAvailable) {
    try {
      const clerkUser = useUser()
      const clerkAuth = useAuth()
      user = clerkUser.user
      isSignedIn = clerkUser.isSignedIn
      isLoaded = clerkUser.isLoaded
      getTokenFn = clerkAuth.getToken
    } catch {
      // Graceful fallback if Clerk fails to initialize at runtime
      isLoaded = true
      isSignedIn = true
      user = { id: 'demo_user_001', firstName: 'Demo', primaryEmailAddress: { emailAddress: 'demo@et.com' } }
    }
  } else {
    isSignedIn = true
    user = { id: 'demo_user_001', firstName: 'Demo', primaryEmailAddress: { emailAddress: 'demo@et.com' } }
  }

  const [profile, setProfile] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [videoJob, setVideoJob] = useState(null)
  const [showSetup, setShowSetup] = useState(false)
  const [setupMode, setSetupMode] = useState(null)
  
  const { t } = useTranslation(profile?.preferred_language || 'English')

  const getAuthHeaders = useCallback(async () => {
    const headers = { 'Content-Type': 'application/json' }
    if (clerkAvailable && isSignedIn) {
      const token = await getTokenFn()
      if (token) headers['Authorization'] = `Bearer ${token}`
    } else if (!clerkAvailable) {
      headers['X-User-Id'] = 'demo_user_001'
    }
    return headers
  }, [clerkAvailable, isSignedIn, getTokenFn])

  // Load user profile
  useEffect(() => {
    if (!isSignedIn) return

    const loadProfile = async () => {
      try {
        const headers = await getAuthHeaders()
        const res = await fetch(`${API}/auth/profile`, { headers })
        if (res.ok) {
          const data = await res.json()
          setProfile(data)
          localStorage.setItem('et_user_profile', JSON.stringify(data))
          if (data.REQUIRED_ONBOARDING || data.needs_setup) {
            setSetupMode('voice')
            setShowSetup(true)
          }
        } else {
          // If 401 or 404, we must require setup or wait for token propagation
          if (res.status === 404) setShowSetup(true)
        }
      } catch (e) {
        console.error('Failed to load profile:', e)
        if (!clerkAvailable) {
          setProfile({ role: 'student', interests: ['AI', 'startups'], level: 'beginner' })
        }
      }
    }
    loadProfile()
  }, [isSignedIn, getAuthHeaders])

  const handleProfileSetup = async (setupData) => {
    try {
      const headers = await getAuthHeaders()
      await fetch(`${API}/auth/profile`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(setupData),
      })
      const updatedProfile = { ...profile, ...setupData, needs_setup: false }
      setProfile(updatedProfile)
      // Persist profile so HubPage can access it for personalized feed
      localStorage.setItem('et_user_profile', JSON.stringify(updatedProfile))
      setShowSetup(false)
    } catch (e) {
      console.error('Profile setup failed:', e)
    }
  }

  const handleVideoGenerate = async (topic, sourceUrl) => {
    try {
      const headers = await getAuthHeaders()
      const lang = profile?.preferred_language || 'English'
      const res = await fetch(`${API}/video/generate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ topic, source_url: sourceUrl, language: lang }),
      })
      const data = await res.json()
      setVideoJob(data)
    } catch (e) {
      console.error('Video generation failed:', e)
    }
  }

  if (!isLoaded) {
    return (
      <div className="dashboard">
        <div className="feed-loading">
          <div className="spinner" />
          <div>Loading...</div>
        </div>
      </div>
    )
  }

  if (!isSignedIn && clerkAvailable) {
    return (
      <div className="dashboard">
        <div className="feed-loading" style={{ gap: 24 }}>
          <div style={{ fontFamily: 'var(--font-editorial)', fontSize: 32, fontWeight: 800 }}>
            {t('login_title')}
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 16 }}>
            {t('login_sub')}
          </div>
          <SignInButton mode="modal">
            <button className="landing-cta">{t('login_btn')}</button>
          </SignInButton>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <Navbar
        user={user}
        profile={profile}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        clerkAvailable={clerkAvailable}
        onEditProfile={() => { setSetupMode('manual'); setShowSetup(true); }}
        onEditProfileVoice={() => { setSetupMode('voice'); setShowSetup(true); }}
      />

      <div className="dashboard-body">
        <div className="dashboard-main">
          <NewsFeed
            key={profile?.preferred_language || 'English'}
            profile={profile}
            getAuthHeaders={getAuthHeaders}
            onVideoGenerate={handleVideoGenerate}
            onProfileSetupRequired={() => { setSetupMode('voice'); setShowSetup(true); }}
          />
        </div>

        <AISidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          getAuthHeaders={getAuthHeaders}
        />
      </div>

      {videoJob && (
        <VideoModal
          job={videoJob}
          onClose={() => setVideoJob(null)}
          language={profile?.preferred_language || 'English'}
        />
      )}

      {showSetup && (
        <ProfileSetup
          initialMode={setupMode}
          initialProfile={profile}
          onComplete={handleProfileSetup}
          onCancel={() => setShowSetup(false)}
          getAuthHeaders={getAuthHeaders}
          onVoiceComplete={(updatedProfile) => {
            const newProf = { ...profile, ...updatedProfile, needs_setup: false };
            setProfile(newProf);
            localStorage.setItem('et_user_profile', JSON.stringify(newProf));
            setShowSetup(false);
          }}
        />
      )}
    </div>
  )
}
