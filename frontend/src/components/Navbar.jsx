import { Link } from 'react-router-dom'
import { UserButton } from '@clerk/clerk-react'
import { useTranslation } from '../utils/i18n'

export default function Navbar({ user, profile, sidebarOpen, onToggleSidebar, clerkAvailable, onEditProfile, onEditProfileVoice }) {
  const { t } = useTranslation(profile?.preferred_language || 'English')
  const role = profile?.role || 'reader'
  const displayName = user?.firstName || user?.primaryEmailAddress?.emailAddress?.split('@')[0] || 'User'

  const roleEmoji = { student: '🎓', investor: '💼', founder: '🚀', journalist: '📝', analyst: '📊' }

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <div className="nav-logo">ET</div>
        <div>
          <div className="nav-title">{t('nav_title')}</div>
          <div className="nav-subtitle">{t('nav_subtitle')}</div>
        </div>
      </div>

      <div className="nav-spacer" />

      {profile && (
        <div className="nav-role">
          <span>{roleEmoji[role] || '📰'}</span>
          <span>{role.charAt(0).toUpperCase() + role.slice(1)}</span>
        </div>
      )}

      <div className="nav-user">
        <span className="nav-avatar">{displayName[0]?.toUpperCase()}</span>
        <span>{displayName}</span>
      </div>

      {clerkAvailable && (
        <div style={{ marginLeft: 4 }}>
          <UserButton afterSignOutUrl="/" />
        </div>
      )}

      <div className="nav-actions">
        {onEditProfileVoice && (
          <button className="btn-sidebar-toggle" onClick={onEditProfileVoice} style={{ marginRight: 8, whiteSpace: 'nowrap', background: 'linear-gradient(135deg, #10b981, #059669)', color: 'white' }}>
            {t('nav_refine')}
          </button>
        )}
        {onEditProfile && (
          <button className="btn-sidebar-toggle" onClick={onEditProfile} style={{ marginRight: 8, whiteSpace: 'nowrap' }}>
            {t('nav_preferences')}
          </button>
        )}
        <Link to="/dashboard" className="btn-sidebar-toggle" style={{ textDecoration: 'none', marginRight: 8, whiteSpace: 'nowrap' }}>
          {t('nav_dashboard')}
        </Link>
        <Link to="/hub" className="btn-sidebar-toggle active" style={{ textDecoration: 'none', marginRight: 8, whiteSpace: 'nowrap' }}>
          {t('nav_ai_hub')}
        </Link>
        {onToggleSidebar && (
          <button
            className={`btn-sidebar-toggle ${sidebarOpen ? 'active' : ''}`}
            onClick={onToggleSidebar}
            id="btn-toggle-ai-sidebar"
            style={{ whiteSpace: 'nowrap' }}
          >
            {sidebarOpen ? t('nav_history_close') : t('nav_history')}
          </button>
        )}
      </div>
    </nav>
  )
}
