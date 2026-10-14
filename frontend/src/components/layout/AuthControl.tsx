'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import styles from './Header.module.css';

export function AuthControl() {
  const [user, setUser] = useState<{ email?: string; id?: string } | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const supabase = createClient();
    const fetchSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUser({ email: session.user.email, id: session.user.id });
        const { data: roleData } = await supabase.rpc('get_my_role');
        setRole(roleData || 'public');
      } else {
        setUser(null);
        setRole(null);
      }
    };

    fetchSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser({ email: session.user.email, id: session.user.id });
        supabase.rpc('get_my_role').then(({ data }) => setRole(data || 'public'));
      } else {
        setUser(null);
        setRole(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // Close account menu on route change
  useEffect(() => {
    setAccountMenuOpen(false);
  }, [pathname]);

  // Lock background scroll and hide bottom navigation while drawer is open
  useEffect(() => {
    if (accountMenuOpen) {
      document.body.setAttribute('data-account-drawer-open', 'true');
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.removeAttribute('data-account-drawer-open');
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [accountMenuOpen]);

  // Dismiss on Escape key
  useEffect(() => {
    if (!accountMenuOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setAccountMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [accountMenuOpen]);

  const handleSignOut = async () => {
    if (isSigningOut) return;
    setIsSigningOut(true);
    try {
      try {
        await fetch('/api/auth/logout', { method: 'POST' });
      } catch (e) {
        console.warn('Server logout notice:', e);
      }
      const supabase = createClient();
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Supabase sign-out error:', error);
      }
      setAccountMenuOpen(false);
      router.refresh();
      router.push('/login');
    } catch (err) {
      console.error('Sign-out execution error:', err);
    } finally {
      setIsSigningOut(false);
    }
  };

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U';

  return (
    <>
      {/* Desktop Controls (hidden on mobile via CSS) */}
      <div className={styles.desktopAuth}>
        {!user ? (
          <div className={styles.authGroup}>
            <Link href="/login" className={styles.signInLink}>
              Sign In
            </Link>
            <Link href="/register" className={styles.registerBtn}>
              Register
            </Link>
          </div>
        ) : (
          <div className={styles.authControl}>
            <Link href="/profile" className={styles.userInfo} title={user.email}>
              <span className={styles.userEmail}>{user.email}</span>
              {role && <span className={styles.userRole}>{role}</span>}
            </Link>
            <Link href="/profile" className={styles.profileBtn}>
              Profile
            </Link>
            {role === 'admin' && (
              <Link href="/admin" className={styles.adminBtn}>
                Admin
              </Link>
            )}
            <button
              onClick={handleSignOut}
              className={styles.signOutBtn}
              aria-label="Sign out"
              disabled={isSigningOut}
            >
              {isSigningOut ? 'Signing out...' : 'Sign out'}
            </button>
          </div>
        )}
      </div>

      {/* Mobile Avatar Button (visible only on mobile via CSS) */}
      <div className={styles.mobileAuthContainer}>
        <button
          id="mobile-account-btn"
          data-testid="mobile-account-button"
          type="button"
          onClick={() => setAccountMenuOpen(!accountMenuOpen)}
          className={styles.mobileAvatarBtn}
          aria-label={user ? `Account menu for ${user.email}` : "Sign In or Register"}
          aria-expanded={accountMenuOpen}
        >
          {user ? (
            <span className={styles.avatarInitial}>{userInitial}</span>
          ) : (
            <span className="material-symbols-outlined text-[18px]">person</span>
          )}
        </button>
      </div>

      {/* Mobile Account Drawer / Modal (Portaled to document.body for pristine stacking context) */}
      {mounted && accountMenuOpen && createPortal(
        <div
          className={styles.accountOverlay}
          onClick={() => setAccountMenuOpen(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className={styles.accountDrawer} onClick={(e) => e.stopPropagation()}>
            <div className={styles.accountHeader}>
              <div className={styles.accountUserMeta}>
                <div className={styles.drawerAvatarBadge}>
                  {user ? userInitial : <span className="material-symbols-outlined">person</span>}
                </div>
                <div className={styles.drawerUserInfo}>
                  {user ? (
                    <>
                      <span className={styles.drawerEmail} title={user.email}>{user.email}</span>
                      <div className={styles.drawerRoleBadge}>
                        <span className={styles.roleDot}></span>
                        <span>{role ? role.toUpperCase() : 'PUBLIC RESEARCHER'}</span>
                      </div>
                    </>
                  ) : (
                    <>
                      <span className={styles.drawerEmail}>Anonymous Visitor</span>
                      <span className={styles.drawerSubtext}>Sign in to access research tools</span>
                    </>
                  )}
                </div>
              </div>
              <button
                type="button"
                className={styles.accountCloseBtn}
                onClick={() => setAccountMenuOpen(false)}
                aria-label="Close Account Menu"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className={styles.accountActionsList}>
              {user ? (
                <>
                  <Link
                    href="/profile"
                    className={styles.accountActionItem}
                    onClick={() => setAccountMenuOpen(false)}
                  >
                    <span className="material-symbols-outlined">badge</span>
                    <div className={styles.actionText}>
                      <span className={styles.actionTitle}>Profile Dashboard</span>
                      <span className={styles.actionDesc}>Manage personal identity &amp; credentials</span>
                    </div>
                  </Link>

                  <Link
                    href="/profile?tab=overview#activity"
                    className={styles.accountActionItem}
                    onClick={() => setAccountMenuOpen(false)}
                  >
                    <span className="material-symbols-outlined">history</span>
                    <div className={styles.actionText}>
                      <span className={styles.actionTitle}>Research Activity</span>
                      <span className={styles.actionDesc}>View logged analyses and GIS history</span>
                    </div>
                  </Link>

                  <Link
                    href="/profile?tab=settings"
                    className={styles.accountActionItem}
                    onClick={() => setAccountMenuOpen(false)}
                  >
                    <span className="material-symbols-outlined">settings</span>
                    <div className={styles.actionText}>
                      <span className={styles.actionTitle}>Account Settings</span>
                      <span className={styles.actionDesc}>Update password and security options</span>
                    </div>
                  </Link>

                  {role === 'admin' && (
                    <Link
                      href="/admin"
                      className={styles.accountActionItem}
                      onClick={() => setAccountMenuOpen(false)}
                    >
                      <span className="material-symbols-outlined">admin_panel_settings</span>
                      <div className={styles.actionText}>
                        <span className={styles.actionTitle}>Administration Console</span>
                        <span className={styles.actionDesc}>Manage system keys and policies</span>
                      </div>
                    </Link>
                  )}

                  <button
                    type="button"
                    onClick={handleSignOut}
                    className={`${styles.accountActionItem} ${styles.signOutAction}`}
                    disabled={isSigningOut}
                  >
                    <span className="material-symbols-outlined">logout</span>
                    <div className={styles.actionText}>
                      <span className={styles.actionTitle}>{isSigningOut ? 'Signing out...' : 'Sign Out'}</span>
                      <span className={styles.actionDesc}>Securely terminate session</span>
                    </div>
                  </button>
                </>
              ) : (
                <div className={styles.anonActions}>
                  <Link
                    href="/login"
                    className={styles.primaryAuthBtn}
                    onClick={() => setAccountMenuOpen(false)}
                  >
                    <span className="material-symbols-outlined">login</span>
                    <span>Sign In to Account</span>
                  </Link>
                  <Link
                    href="/register"
                    className={styles.secondaryAuthBtn}
                    onClick={() => setAccountMenuOpen(false)}
                  >
                    <span>Register New Account</span>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
