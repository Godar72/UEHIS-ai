'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import styles from './profile.module.css';

interface UserProfile {
  id: string;
  email: string;
  displayName: string;
  role: 'public' | 'researcher' | 'admin';
  createdAt: string | null;
  lastSignInAt: string | null;
  isOAuthOnly: boolean;
  providers: string[];
}

interface ActivityItem {
  id: string;
  activity_type: string;
  category: 'explore' | 'carbon' | 'analysis' | 'planting';
  action_type: 'viewed' | 'analyzed' | 'saved' | 'exported';
  title: string;
  description: string | null;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, any>;
  created_at: string;
}

export function ProfileDashboard() {
  const router = useRouter();

  // Tab state
  const [activeTab, setActiveTab] = useState<'overview' | 'settings'>('overview');

  // Profile data
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Activity data
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityCategory, setActivityCategory] = useState<string>('all');
  const [activityPage, setActivityPage] = useState(1);
  const activityLimit = 10;

  // Form states: Display name
  const [displayNameInput, setDisplayNameInput] = useState('');
  const [displayNameLoading, setDisplayNameLoading] = useState(false);
  const [displayNameSuccess, setDisplayNameSuccess] = useState<string | null>(null);
  const [displayNameError, setDisplayNameError] = useState<string | null>(null);

  // Form states: Password
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Load profile data
  const loadProfile = useCallback(async () => {
    try {
      setProfileLoading(true);
      setProfileError(null);
      const res = await fetch('/api/profile', { cache: 'no-store' });
      if (!res.ok) {
        if (res.status === 401) {
          router.replace('/login?next=/profile');
          return;
        }
        throw new Error('Failed to load profile record');
      }
      const data = await res.json();
      if (data?.user) {
        setProfile(data.user);
        setDisplayNameInput(data.user.displayName || '');
      }
    } catch (err: any) {
      console.error('Failed to load profile:', err);
      setProfileError(err.message || 'Unable to load profile data');
    } finally {
      setProfileLoading(false);
    }
  }, [router]);

  // Load activity data
  const loadActivities = useCallback(async (cat: string, page: number) => {
    try {
      setActivityLoading(true);
      const params = new URLSearchParams();
      if (cat !== 'all') params.set('category', cat);
      params.set('page', page.toString());
      params.set('limit', activityLimit.toString());

      const res = await fetch(`/api/profile/activity?${params.toString()}`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setActivities(data.activities || []);
        setActivityTotal(data.total || 0);
      } else if (res.status === 403) {
        setActivities([]);
        setActivityTotal(0);
      }
    } catch (err) {
      console.error('Failed to load activities:', err);
    } finally {
      setActivityLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (profile) {
      loadActivities(activityCategory, activityPage);
    }
  }, [profile, activityCategory, activityPage, loadActivities]);

  // Filter change handler
  const handleCategoryFilter = (newCategory: string) => {
    setActivityCategory(newCategory);
    setActivityPage(1);
  };

  // Display Name Update Handler
  const handleUpdateDisplayName = async (e: React.FormEvent) => {
    e.preventDefault();
    setDisplayNameError(null);
    setDisplayNameSuccess(null);

    const trimmed = displayNameInput.trim();
    if (trimmed.length < 2 || trimmed.length > 50) {
      setDisplayNameError('Display name must be between 2 and 50 characters.');
      return;
    }

    setDisplayNameLoading(true);
    try {
      const res = await fetch('/api/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ displayName: trimmed }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to update display name');
      }

      setDisplayNameSuccess('Display name successfully updated.');
      if (profile) {
        setProfile({ ...profile, displayName: trimmed });
      }
    } catch (err: any) {
      setDisplayNameError(err.message || 'Failed to update display name');
    } finally {
      setDisplayNameLoading(false);
    }
  };

  // Password Change Handler
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword.length < 6) {
      setPasswordError('New passphrase must be at least 6 characters in length.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('New passphrase and confirmation do not match.');
      return;
    }

    setPasswordLoading(true);
    try {
      const res = await fetch('/api/profile/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          currentPassword: currentPassword || undefined,
          newPassword,
          confirmPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to update passphrase');
      }

      setPasswordSuccess('Passphrase successfully updated.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordError(err.message || 'Failed to update passphrase');
    } finally {
      setPasswordLoading(false);
    }
  };

  // Sign out handler
  const handleSignOut = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
      console.warn('Logout notice:', e);
    }
    const supabase = createClient();
    await supabase.auth.signOut();
    router.refresh();
    router.push('/login');
  };

  // Initials generator
  const getInitials = (name?: string) => {
    if (!name) return 'UE';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  // Date formatting helpers
  const formatTimestamp = (isoString?: string | null) => {
    if (!isoString) return 'Not available';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      });
    } catch {
      return isoString;
    }
  };

  const formatRelativeTime = (isoString?: string | null) => {
    if (!isoString) return '';
    try {
      const diffMs = Date.now() - new Date(isoString).getTime();
      const diffSec = Math.floor(diffMs / 1000);
      const diffMin = Math.floor(diffSec / 60);
      const diffHour = Math.floor(diffMin / 60);
      const diffDay = Math.floor(diffHour / 24);

      if (diffSec < 60) return 'Just now';
      if (diffMin < 60) return `${diffMin}m ago`;
      if (diffHour < 24) return `${diffHour}h ago`;
      if (diffDay < 30) return `${diffDay}d ago`;
      return '';
    } catch {
      return '';
    }
  };

  // Reopen destination resolver
  const getReopenDestination = (act: ActivityItem): string | null => {
    if (act.metadata?.reopen_url && typeof act.metadata.reopen_url === 'string') {
      return act.metadata.reopen_url;
    }
    if (act.entity_type === 'block' && act.entity_id) {
      return `/explore/block/${act.entity_id}`;
    }
    if (act.category === 'carbon') {
      return '/carbon';
    }
    if (act.category === 'analysis' && act.activity_type === 'viewed_scenario') {
      return '/scenarios';
    }
    if (act.category === 'planting') {
      return '/planting';
    }
    if (act.category === 'explore') {
      return '/explore';
    }
    return null;
  };

  if (profileLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.inner}>
          <div className={styles.headerBlock}>
            <div className={styles.kicker}>SECURE DOSSIER // EPSG:32643</div>
            <h1 className={styles.title}>Loading User Profile...</h1>
            <p className={styles.subtitle}>Authenticating cryptographic credentials from Supabase.</p>
          </div>
        </div>
      </div>
    );
  }

  if (profileError || !profile) {
    return (
      <div className={styles.container}>
        <div className={styles.inner}>
          <div className={styles.headerBlock}>
            <div className={styles.kicker}>SYSTEM ALERT // AUTHORIZATION</div>
            <h1 className={styles.title}>Profile Access Error</h1>
            <p className={styles.subtitle}>{profileError || 'Unable to retrieve authenticated profile.'}</p>
          </div>
          <div className={`${styles.noticeBox} ${styles.noticeError}`}>
            Authentication session could not be established. Please re-authenticate.
          </div>
          <Link href="/login" className={styles.submitBtn}>
            Proceed to Sign In
          </Link>
        </div>
      </div>
    );
  }

  const roleLabels: Record<string, { label: string; class: string; desc: string }> = {
    public: {
      label: 'Public Access',
      class: styles.rolePublic,
      desc: 'Standard ecological exploration across Pune extent.'
    },
    researcher: {
      label: 'Researcher',
      class: styles.roleResearcher,
      desc: 'Authorized for vegetative opportunity planning & biotope analyses.'
    },
    admin: {
      label: 'Administrator',
      class: styles.roleAdmin,
      desc: 'Full administrative access & role delegation authority.'
    }
  };

  const currentRole = roleLabels[profile.role] || roleLabels.public;
  const isPrivileged = profile.role === 'researcher' || profile.role === 'admin';

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        {/* Header Block */}
        <section className={styles.headerBlock}>
          <div className={styles.headerMeta}>
            <div className={styles.kicker}>
              <span>Personnel Dossier</span>
              <span>·</span>
              <span>EPSG:32643 UTM 43N</span>
            </div>
            <div className={styles.telemetryBadge}>
              <span className={styles.liveDot}></span>
              <span>AUTHENTICATED // 5,309 BLOCKS EXTENT</span>
            </div>
          </div>
          <h1 className={styles.title}>User Profile &amp; Research Activity</h1>
          <p className={styles.subtitle}>
            Verified personnel credentials, access tier, and persistent audit record of scientific exploration.
          </p>
        </section>

        {/* Navigation Tabs */}
        <nav className={styles.tabsContainer} aria-label="Profile Sections">
          <button
            className={`${styles.tabBtn} ${activeTab === 'overview' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('overview')}
            aria-selected={activeTab === 'overview'}
          >
            <span>Overview &amp; Research Activity</span>
            <span className={styles.tabCountBadge}>{activityTotal}</span>
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'settings' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('settings')}
            aria-selected={activeTab === 'settings'}
          >
            <span>Account Settings &amp; Security</span>
          </button>
        </nav>

        {activeTab === 'overview' && (
          <>
            {/* Section A: Profile Overview Card */}
            <section className={styles.overviewCard} aria-label="Profile Overview">
              <div className={styles.overviewHeader}>
                <div className={styles.avatarIdentity}>
                  <div className={styles.avatar} aria-hidden="true">
                    {getInitials(profile.displayName)}
                  </div>
                  <div className={styles.identityText}>
                    <div className={styles.nameRow}>
                      <h2 className={styles.displayName}>{profile.displayName}</h2>
                      <span className={`${styles.roleBadge} ${currentRole.class}`}>
                        {currentRole.label}
                      </span>
                    </div>
                    <span className={styles.email}>{profile.email}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    onClick={() => setActiveTab('settings')}
                    className={styles.filterBtn}
                    style={{ textTransform: 'uppercase', fontSize: '0.75rem' }}
                  >
                    Edit Display Name
                  </button>
                  <button onClick={handleSignOut} className={styles.dangerBtn}>
                    Sign Out
                  </button>
                </div>
              </div>

              {/* Metadata Grid */}
              <div className={styles.metaGrid}>
                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Account Role</span>
                  <span className={styles.metaValue}>{currentRole.label}</span>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--color-muted)' }}>
                    {currentRole.desc}
                  </span>
                </div>

                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Authentication Identity</span>
                  <span className={styles.metaValue}>
                    {profile.isOAuthOnly ? 'Google OAuth' : 'Supabase Email/Passphrase'}
                  </span>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--color-muted)' }}>
                    {profile.isOAuthOnly ? 'Federated identity provider' : 'Managed credentials'}
                  </span>
                </div>

                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Account Registered</span>
                  <span className={styles.metaValue}>{formatTimestamp(profile.createdAt)}</span>
                </div>

                <div className={styles.metaItem}>
                  <span className={styles.metaLabel}>Last Session Access</span>
                  <span className={styles.metaValue}>{formatTimestamp(profile.lastSignInAt)}</span>
                </div>
              </div>
            </section>

            {/* Section B: Research Activity */}
            <section className={styles.activitySection} aria-label="My Research Activity">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-seer-navy)', margin: '0 0 4px 0' }}>
                    My Research Activity
                  </h2>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--color-muted)', margin: 0 }}>
                    Chronological record of verified ecological block inspections, study area calculations, and scenario modeling.
                  </p>
                </div>
                <div className={styles.activityCountIndicator}>
                  Showing {activities.length} of {activityTotal} recorded actions
                </div>
              </div>

              {/* Activity Category Filters */}
              <div className={styles.activityControls}>
                <div className={styles.filterGroup}>
                  <span className={styles.filterLabel}>Filter:</span>
                  <button
                    className={`${styles.filterBtn} ${activityCategory === 'all' ? styles.filterBtnActive : ''}`}
                    onClick={() => handleCategoryFilter('all')}
                  >
                    All Activity
                  </button>
                  <button
                    className={`${styles.filterBtn} ${activityCategory === 'explore' ? styles.filterBtnActive : ''}`}
                    onClick={() => handleCategoryFilter('explore')}
                  >
                    Explore
                  </button>
                  <button
                    className={`${styles.filterBtn} ${activityCategory === 'carbon' ? styles.filterBtnActive : ''}`}
                    onClick={() => handleCategoryFilter('carbon')}
                  >
                    Carbon Stock
                  </button>
                  <button
                    className={`${styles.filterBtn} ${activityCategory === 'analysis' ? styles.filterBtnActive : ''}`}
                    onClick={() => handleCategoryFilter('analysis')}
                  >
                    Analysis
                  </button>
                  {isPrivileged && (
                    <button
                      className={`${styles.filterBtn} ${activityCategory === 'planting' ? styles.filterBtnActive : ''}`}
                      onClick={() => handleCategoryFilter('planting')}
                    >
                      Planting Opportunities
                    </button>
                  )}
                </div>

                <button
                  onClick={() => loadActivities(activityCategory, activityPage)}
                  className={styles.filterBtn}
                  disabled={activityLoading}
                >
                  {activityLoading ? 'Refreshing...' : 'Refresh Activity'}
                </button>
              </div>

              {/* Activity Feed */}
              {activityLoading && activities.length === 0 ? (
                <div className={styles.emptyState}>
                  <span className={styles.emptyTitle}>Loading Research Timeline...</span>
                </div>
              ) : activities.length === 0 ? (
                <div className={styles.emptyState}>
                  <span className={`material-symbols-outlined ${styles.emptyIcon}`}>history_toggle_off</span>
                  <h3 className={styles.emptyTitle}>No Activity Recorded in this Category</h3>
                  <p className={styles.emptyText}>
                    {activityCategory === 'all'
                      ? 'No research activity has been recorded yet. Research actions such as examining ecological blocks, analyzing study boundaries, or reviewing scenarios will be saved here automatically as you interact with the system.'
                      : `No activity found under the "${activityCategory}" category. Explore the relevant GIS modules to log verified research events.`}
                  </p>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                    <Link href="/explore" className={styles.submitBtn}>
                      Explore GIS Blocks
                    </Link>
                    <Link href="/carbon" className={styles.filterBtn}>
                      Carbon Stock
                    </Link>
                  </div>
                </div>
              ) : (
                <div className={styles.activityFeed}>
                  {activities.map((act) => {
                    const reopenDest = getReopenDestination(act);
                    const badgeClass =
                      act.action_type === 'analyzed'
                        ? styles.badgeAnalyzed
                        : act.action_type === 'saved'
                        ? styles.badgeSaved
                        : act.action_type === 'exported'
                        ? styles.badgeExported
                        : styles.badgeViewed;

                    return (
                      <article key={act.id} className={styles.activityCard}>
                        <div className={styles.activityCardHeader}>
                          <div className={badgeAndTitleStyle}>
                            <span className={`${styles.actionBadge} ${badgeClass}`}>
                              {act.action_type}
                            </span>
                            <h3 className={styles.activityTitle}>{act.title}</h3>
                          </div>
                          <span className={styles.activityTime} title={formatTimestamp(act.created_at)}>
                            {formatRelativeTime(act.created_at) || formatTimestamp(act.created_at)}
                          </span>
                        </div>

                        {act.description && (
                          <p className={styles.activityDescription}>{act.description}</p>
                        )}

                        <div className={styles.activityCardFooter}>
                          <div className={styles.entityChips}>
                            <span className={styles.entityChip}>
                              Category: {act.category.toUpperCase()}
                            </span>
                            {act.entity_type && act.entity_id && (
                              <span className={styles.entityChip}>
                                {act.entity_type.replace('_', ' ')}: {act.entity_id}
                              </span>
                            )}
                            {act.metadata?.uehi_score !== undefined && (
                              <span className={styles.entityChip}>
                                UEHI: {act.metadata.uehi_score}
                              </span>
                            )}
                            {act.metadata?.risk_level && (
                              <span className={styles.entityChip}>
                                Risk: {act.metadata.risk_level}
                              </span>
                            )}
                          </div>

                          {reopenDest && (
                            <Link href={reopenDest} className={styles.viewAgainBtn}>
                              <span>View again</span>
                              <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>
                                arrow_forward
                              </span>
                            </Link>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}

              {/* Pagination Bar */}
              {activityTotal > activityLimit && (
                <div className={styles.paginationBar}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)', fontFamily: 'var(--font-ibm-plex-mono), monospace' }}>
                    Page {activityPage} of {Math.ceil(activityTotal / activityLimit)}
                  </span>
                  <div className={styles.paginationButtons}>
                    <button
                      className={styles.pageBtn}
                      disabled={activityPage <= 1 || activityLoading}
                      onClick={() => setActivityPage((p) => Math.max(1, p - 1))}
                    >
                      &larr; Previous
                    </button>
                    <button
                      className={styles.pageBtn}
                      disabled={activityPage * activityLimit >= activityTotal || activityLoading}
                      onClick={() => setActivityPage((p) => p + 1)}
                    >
                      Next &rarr;
                    </button>
                  </div>
                </div>
              )}
            </section>
          </>
        )}

        {activeTab === 'settings' && (
          <div className={styles.settingsGrid}>
            {/* Display Name Management */}
            <section className={styles.settingsCard} aria-labelledby="display-name-heading">
              <h2 id="display-name-heading" className={styles.cardTitle}>
                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>badge</span>
                <span>Display Name Management</span>
              </h2>
              <p className={styles.cardDescription}>
                Update the public display identity visible on your dossiers, research activity logs, and collaborative notes.
              </p>

              {displayNameSuccess && (
                <div className={`${styles.noticeBox} ${styles.noticeSuccess}`} role="status">
                  {displayNameSuccess}
                </div>
              )}

              {displayNameError && (
                <div className={`${styles.noticeBox} ${styles.noticeError}`} role="alert">
                  {displayNameError}
                </div>
              )}

              <form onSubmit={handleUpdateDisplayName} className={styles.form}>
                <div className={styles.formGroup}>
                  <label htmlFor="displayName" className={styles.label}>
                    Display Name (2–50 characters)
                  </label>
                  <input
                    id="displayName"
                    type="text"
                    value={displayNameInput}
                    onChange={(e) => setDisplayNameInput(e.target.value)}
                    className={styles.input}
                    required
                    minLength={2}
                    maxLength={50}
                    disabled={displayNameLoading}
                    placeholder="e.g. Dr. A. Godar"
                  />
                  <span className={styles.charCount}>
                    {displayNameInput.trim().length} / 50 characters
                  </span>
                </div>

                <button
                  type="submit"
                  className={styles.submitBtn}
                  disabled={displayNameLoading || displayNameInput.trim() === profile.displayName}
                >
                  {displayNameLoading ? 'Saving...' : 'Save Display Name'}
                </button>
              </form>

              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '14px' }}>
                <span className={styles.label}>Primary Authentication Email</span>
                <p style={{ fontFamily: 'var(--font-ibm-plex-mono), monospace', fontSize: '0.8125rem', color: 'var(--color-muted)', margin: '4px 0 0 0' }}>
                  {profile.email} (Authoritative Supabase Auth Login Identity)
                </p>
              </div>
            </section>

            {/* Passphrase & Credential Security */}
            <section className={styles.settingsCard} aria-labelledby="credential-heading">
              <h2 id="credential-heading" className={styles.cardTitle}>
                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>lock_reset</span>
                <span>Credential Security</span>
              </h2>
              <p className={styles.cardDescription}>
                Manage authentication credentials and cryptographic passphrases.
              </p>

              {profile.isOAuthOnly ? (
                <div className={styles.oauthNotice}>
                  <div className={styles.oauthNoticeTitle}>
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>verified_user</span>
                    <span>Federated Google OAuth Account</span>
                  </div>
                  <p className={styles.oauthNoticeText}>
                    Your account is authenticated exclusively through <strong>Google OAuth</strong> (<code>{profile.email}</code>).
                    Password management, 2-Factor Authentication, and credential rotation are administered directly through your Google Identity Account.
                  </p>
                  <div style={{ marginTop: '8px' }}>
                    <a
                      href="https://myaccount.google.com/security"
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.viewAgainBtn}
                      style={{ display: 'inline-flex' }}
                    >
                      Manage Google Security Settings &rarr;
                    </a>
                  </div>
                </div>
              ) : (
                <>
                  {passwordSuccess && (
                    <div className={`${styles.noticeBox} ${styles.noticeSuccess}`} role="status">
                      {passwordSuccess}
                    </div>
                  )}

                  {passwordError && (
                    <div className={`${styles.noticeBox} ${styles.noticeError}`} role="alert">
                      {passwordError}
                    </div>
                  )}

                  <form onSubmit={handleChangePassword} className={styles.form}>
                    <div className={styles.formGroup}>
                      <label htmlFor="currentPassword" className={styles.label}>
                        Current Passphrase (Verification)
                      </label>
                      <input
                        id="currentPassword"
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className={styles.input}
                        autoComplete="current-password"
                        disabled={passwordLoading}
                        placeholder="Current passphrase"
                      />
                    </div>

                    <div className={styles.formGroup}>
                      <label htmlFor="newPassword" className={styles.label}>
                        New Passphrase (Min. 6 characters)
                      </label>
                      <input
                        id="newPassword"
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className={styles.input}
                        required
                        minLength={6}
                        maxLength={256}
                        autoComplete="new-password"
                        disabled={passwordLoading}
                        placeholder="New passphrase"
                      />
                    </div>

                    <div className={styles.formGroup}>
                      <label htmlFor="confirmPassword" className={styles.label}>
                        Confirm New Passphrase
                      </label>
                      <input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className={styles.input}
                        required
                        minLength={6}
                        maxLength={256}
                        autoComplete="new-password"
                        disabled={passwordLoading}
                        placeholder="Confirm new passphrase"
                      />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                      <button
                        type="submit"
                        className={styles.submitBtn}
                        disabled={passwordLoading}
                      >
                        {passwordLoading ? 'Updating Passphrase...' : 'Update Passphrase'}
                      </button>

                      <Link href="/reset-password" style={{ fontSize: '0.75rem', color: 'var(--color-seer-navy)', textDecoration: 'underline' }}>
                        Forgot passphrase?
                      </Link>
                    </div>
                  </form>
                </>
              )}

              {/* Session Termination Card */}
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span className={styles.label}>Cryptographic Session Termination</span>
                <p style={{ fontSize: '0.8125rem', color: 'var(--color-muted)', margin: 0 }}>
                  Revoke active session tokens across this device.
                </p>
                <button onClick={handleSignOut} className={styles.dangerBtn} style={{ marginTop: '4px' }}>
                  Terminate Session &amp; Sign Out
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

const badgeAndTitleStyle = styles.badgeAndTitle;
