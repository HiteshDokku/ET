import { Link } from 'react-router-dom'
import { UserButton } from '@clerk/clerk-react'
import { useTranslation } from '../utils/i18n'

export default function Navbar({ user, profile, sidebarOpen, onToggleSidebar, clerkAvailable, onEditProfile, onEditProfileVoice }) {
  const { t } = useTranslation(profile?.preferred_language || 'English')
  const role = profile?.role || 'reader'
  const displayName = user?.firstName || user?.primaryEmailAddress?.emailAddress?.split('@')[0] || 'User'

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
  const edition = `Global Edition`

  return (
    <nav className="navbar">
      {/* Top Row: Dateline & User Info */}
      <div className="masthead-top">
        <div>{today} | {edition}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {profile && (
            <div className="nav-role">
              {role.charAt(0).toUpperCase() + role.slice(1)}
            </div>
          )}
          <span>{displayName}</span>
          {clerkAvailable && (
            <div style={{ marginLeft: 4 }}>
              <UserButton afterSignOutUrl="/" />
            </div>
          )}
        </div>
      </div>

      {/* Center Row: Massive Logo */}
      <div className="masthead-center">
        <h1 className="masthead-logo">
          <span className="masthead-logo-box">ET</span>
          The Economic Times
        </h1>
      </div>

      {/* Bottom Row: Thin-bordered Nav Links */}
      <div className="masthead-bottom">
        {onEditProfileVoice && (
          <button className="masthead-link" onClick={onEditProfileVoice}>
            {t('nav_refine')}
          </button>
        )}
        {onEditProfile && (
          <button className="masthead-link" onClick={onEditProfile}>
            {t('nav_preferences')}
          </button>
        )}
        <Link to="/dashboard" className="masthead-link">
          {t('nav_dashboard')}
        </Link>
        <Link to="/hub" className="masthead-link active">
          {t('nav_ai_hub')}
        </Link>
        {onToggleSidebar && (
          <button className={`masthead-link ${sidebarOpen ? 'active' : ''}`} onClick={onToggleSidebar}>
            {sidebarOpen ? t('nav_history_close') : t('nav_history')}
          </button>
        )}
      </div>
    </nav>
  )
}
