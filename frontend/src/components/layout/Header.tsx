'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { AuthControl } from './AuthControl';
import styles from './Header.module.css';

export function Header() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [role, setRole] = useState<string | null>(null);

  // Close drawer on navigation
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Determine user role to conditionally expose researcher/admin links
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

  const links = [
    { label: 'Explore', href: '/explore' },
    { label: 'Carbon Stock', href: '/carbon' },
    ...(role === 'researcher' || role === 'admin'
      ? [{ label: 'Planting Opportunities', href: '/planting' }]
      : []),
    { label: 'Scenarios', href: '/scenarios' },
    { label: 'Methodology', href: '/methodology' },
    { label: 'User Manual', href: '/about' },
  ];

  const getSectionTitle = (path: string) => {
    if (path === '/') return 'Atlas';
    if (path.startsWith('/explore')) return 'Explore';
    if (path.startsWith('/carbon')) return 'Carbon';
    if (path.startsWith('/planting')) return 'Planting';
    if (path.startsWith('/scenarios')) return 'Scenarios';
    if (path.startsWith('/methodology')) return 'Methodology';
    if (path.startsWith('/about')) return 'User Manual';
    if (path.startsWith('/profile')) return 'Profile';
    if (path.startsWith('/login')) return 'Sign In';
    if (path.startsWith('/register')) return 'Register';
    if (path.startsWith('/admin')) return 'Admin';
    return 'Atlas';
  };

  const currentSection = getSectionTitle(pathname || '/');

  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        {/* Desktop Brand Identity */}
        <div className={styles.desktopBrand}>
          <Link href="/" className={styles.brandLink} aria-label="UEHIS Homepage">
            <div className={styles.logoWrapper}>
              <Image
                src="/logo.png"
                alt="UEHIS Logo"
                width={48}
                height={32}
                className={styles.logoImage}
                priority
              />
            </div>
            <div className={styles.brandText}>
              <div className={styles.brandTitle}>
                <span className={styles.brandOrg}>SEER BHARAT FOUNDATION</span>
                <span className={styles.brandDot}>·</span>
                <span className={styles.brandAcronym}>UEHIS</span>
              </div>
              <div className={styles.brandSubtitle}>
                Urban Ecosystem Health Intelligence System
              </div>
            </div>
          </Link>
          <div className={styles.telemetryTag}>
            <span className={styles.livePulse}></span>
            <span>PUNE EXTENT | 5,309 BLOCKS (250m) | EPSG:32643</span>
          </div>
        </div>

        {/* Mobile Brand Identity with Actual UEHIS Logo */}
        <div className={styles.mobileBrand}>
          <Link href="/" className={styles.mobileBrandLink} aria-label="UEHIS Homepage">
            <div className={styles.mobileLogoWrapper}>
              <Image
                src="/logo.png"
                alt="UEHIS Logo"
                width={42}
                height={28}
                className={styles.mobileLogoImage}
                priority
              />
            </div>
            <div className={styles.mobileBrandMeta}>
              <div className={styles.mobileBrandTop}>
                <span className={styles.mobileBrandAcronym}>UEHIS</span>
                <span className={styles.mobileBrandSeparator}>|</span>
                <span className={styles.mobileBrandSection}>{currentSection}</span>
              </div>
              <span className={styles.mobileTelemetrySubline}>5,309 BLOCKS · EPSG:32643</span>
            </div>
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav className={styles.nav} aria-label="Main Navigation">
          {links.map((link) => {
            const isActive = pathname === link.href || (link.href !== '/' && pathname?.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`${styles.navLink} ${isActive ? styles.active : ''}`}
                aria-current={isActive ? 'page' : undefined}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Section: Auth & Mobile Menu */}
        <div className={styles.rightSection}>
          {/* Quick Manual Link for Mobile */}
          <Link
            href="/methodology"
            className={styles.mobileQuickDoc}
            title="Technical Methodology &amp; Documentation"
            aria-label="Technical Methodology"
          >
            <span className="material-symbols-outlined text-[18px]">menu_book</span>
          </Link>

          {/* Account Controls & Mobile Avatar */}
          <AuthControl />

          {/* Mobile Secondary Menu Toggle */}
          <button
            className={styles.mobileMenuToggle}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
            aria-expanded={mobileMenuOpen}
          >
            <span className="material-symbols-outlined">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className={styles.mobileDrawer} role="dialog" aria-modal="true">
          <div className={styles.mobileTelemetry}>
            <span className={styles.livePulse}></span>
            <span>PUNE STUDY EXTENT · 5,309 BLOCKS · EPSG:32643</span>
          </div>
          <nav className={styles.mobileNav}>
            {links.map((link) => {
              const isActive = pathname === link.href || (link.href !== '/' && pathname?.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`${styles.mobileNavLink} ${isActive ? styles.mobileActive : ''}`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {link.label}
                </Link>
              );
            })}
            <div className={styles.mobileSublinks}>
              <Link href="/privacy" className={styles.mobileSublink} onClick={() => setMobileMenuOpen(false)}>Privacy Policy</Link>
              <Link href="/terms" className={styles.mobileSublink} onClick={() => setMobileMenuOpen(false)}>Terms of Use</Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
