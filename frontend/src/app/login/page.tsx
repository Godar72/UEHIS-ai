import React, { Suspense } from 'react';
import { BrandLogo } from '@/components/Brand/BrandLogo';
import { LoginForm } from './LoginForm';
import styles from './page.module.css';

export const metadata = {
  title: 'Authentication | UEHIS',
  description: 'Sign in to the Urban Ecosystem Health Intelligence System',
};

export default function LoginPage() {
  return (
    <div className={styles.container}>
      <div className={styles.authCard}>
        <div className={styles.brandHeader}>
          <span className={styles.classificationBadge}>RESTRICTED ACCESS // SEER BHARAT NODE</span>
          <BrandLogo width={120} height={40} withLink={true} />
          <h1 className={styles.title}>System Authentication</h1>
          <p className={styles.subtitle}>Institutional access for authorized personnel only.</p>
        </div>
        
        <Suspense fallback={<div className={styles.form}>Loading authentication provider...</div>}>
          <LoginForm />
        </Suspense>

        <div className={styles.securityNote}>
          Protected by Supabase Auth with TLS 1.3 encryption &amp; IP rate-limiting.
        </div>
      </div>
    </div>
  );
}
