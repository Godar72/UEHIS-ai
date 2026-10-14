'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import styles from './MobileBottomNav.module.css';

export function MobileBottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [role, setRole] = useState<string | null>(null);
  const [moreDrawerOpen, setMoreDrawerOpen] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    const updateRole = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        const { data } = await supabase.rpc('get_my_role');
        setRole(data || 'public');
      } else {
        setRole(null);
      }
    };
    updateRole();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        supabase.rpc('get_my_role').then(({ data }) => setRole(data || 'public'));
      } else {
        setRole(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const isAuthorizedForPlanting = role === 'researcher' || role === 'admin';

  const handleStudyAreaClick = (e: React.MouseEvent) => {
    if (pathname?.startsWith('/explore')) {
      e.preventDefault();
      window.dispatchEvent(new CustomEvent('uehis:open-study-area'));
    }
  };

  return (
    <>
      <nav className={styles.bottomNav} role="navigation" aria-label="Mobile Bottom Navigation">
        <div className={styles.navGrid}>
          {/* 1. Explore */}
          <Link
            href="/explore"
            className={`${styles.navItem} ${pathname === '/explore' && !pathname?.includes('action=study_area') ? styles.navItemActive : ''}`}
            aria-current={pathname === '/explore' ? 'page' : undefined}
          >
            <span className={`material-symbols-outlined ${styles.navIcon}`}>map</span>
            <span className={styles.navLabel}>Explore</span>
          </Link>

          {/* 2. Study Area */}
          <Link
            href="/explore?action=study_area"
            onClick={handleStudyAreaClick}
            className={`${styles.navItem} ${pathname?.includes('study_area') ? styles.navItemActive : ''}`}
          >
            <span className={`material-symbols-outlined ${styles.navIcon}`}>adjust</span>
            <span className={styles.navLabel}>Study Area</span>
          </Link>

          {/* 3. Carbon */}
          <Link
            href="/carbon"
            className={`${styles.navItem} ${pathname?.startsWith('/carbon') ? styles.navItemActive : ''}`}
            aria-current={pathname?.startsWith('/carbon') ? 'page' : undefined}
          >
            <span className={`material-symbols-outlined ${styles.navIcon}`}>eco</span>
            <span className={styles.navLabel}>Carbon</span>
          </Link>

          {/* 4. Planting (if authorized) or Scenarios */}
          {isAuthorizedForPlanting ? (
            <Link
              href="/planting"
              className={`${styles.navItem} ${pathname?.startsWith('/planting') ? styles.navItemActive : ''}`}
              aria-current={pathname?.startsWith('/planting') ? 'page' : undefined}
            >
              <span className={`material-symbols-outlined ${styles.navIcon}`}>forest</span>
              <span className={styles.navLabel}>Planting</span>
            </Link>
          ) : (
            <Link
              href="/scenarios"
              className={`${styles.navItem} ${pathname?.startsWith('/scenarios') ? styles.navItemActive : ''}`}
              aria-current={pathname?.startsWith('/scenarios') ? 'page' : undefined}
            >
              <span className={`material-symbols-outlined ${styles.navIcon}`}>stacked_line_chart</span>
              <span className={styles.navLabel}>Scenarios</span>
            </Link>
          )}

          {/* 5. Scenarios (if authorized) or More menu */}
          {isAuthorizedForPlanting ? (
            <Link
              href="/scenarios"
              className={`${styles.navItem} ${pathname?.startsWith('/scenarios') ? styles.navItemActive : ''}`}
              aria-current={pathname?.startsWith('/scenarios') ? 'page' : undefined}
            >
              <span className={`material-symbols-outlined ${styles.navIcon}`}>stacked_line_chart</span>
              <span className={styles.navLabel}>Scenarios</span>
            </Link>
          ) : (
            <button
              type="button"
              className={`${styles.navItem} ${moreDrawerOpen ? styles.navItemActive : ''}`}
              onClick={() => setMoreDrawerOpen(true)}
              aria-label="Open More Destinations Menu"
              aria-expanded={moreDrawerOpen}
            >
              <span className={`material-symbols-outlined ${styles.navIcon}`}>menu</span>
              <span className={styles.navLabel}>More</span>
            </button>
          )}
        </div>
      </nav>

      {/* Secondary Destination Drawer */}
      {moreDrawerOpen && (
        <div className={styles.drawerOverlay} onClick={() => setMoreDrawerOpen(false)} role="dialog" aria-modal="true">
          <div className={styles.drawerContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.drawerHeader}>
              <span className={styles.drawerTitle}>UEHIS Intelligence System</span>
              <button
                className={styles.drawerCloseBtn}
                onClick={() => setMoreDrawerOpen(false)}
                aria-label="Close menu"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className={styles.drawerList}>
              <Link
                href="/methodology"
                className={`${styles.drawerLink} ${pathname === '/methodology' ? styles.drawerLinkActive : ''}`}
                onClick={() => setMoreDrawerOpen(false)}
              >
                <span className={`material-symbols-outlined ${styles.drawerLinkIcon}`}>menu_book</span>
                <span>Technical Methodology</span>
              </Link>
              <Link
                href="/about"
                className={`${styles.drawerLink} ${pathname === '/about' ? styles.drawerLinkActive : ''}`}
                onClick={() => setMoreDrawerOpen(false)}
              >
                <span className={`material-symbols-outlined ${styles.drawerLinkIcon}`}>help_outline</span>
                <span>User Manual &amp; Guidelines</span>
              </Link>
              <Link
                href="/privacy"
                className={`${styles.drawerLink} ${pathname === '/privacy' ? styles.drawerLinkActive : ''}`}
                onClick={() => setMoreDrawerOpen(false)}
              >
                <span className={`material-symbols-outlined ${styles.drawerLinkIcon}`}>shield</span>
                <span>Privacy Policy</span>
              </Link>
              <Link
                href="/terms"
                className={`${styles.drawerLink} ${pathname === '/terms' ? styles.drawerLinkActive : ''}`}
                onClick={() => setMoreDrawerOpen(false)}
              >
                <span className={`material-symbols-outlined ${styles.drawerLinkIcon}`}>gavel</span>
                <span>Terms of Use</span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
