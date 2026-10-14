import React, { Suspense } from 'react';
import { BrandLogo } from '@/components/Brand/BrandLogo';
import { RegisterForm } from './RegisterForm';
import styles from '../login/page.module.css';

export const metadata = {
  title: 'Registration | UEHIS',
  description: 'Register for access to the Urban Ecosystem Health Intelligence System',
};

export default function RegisterPage() {
  return (
    <div className={styles.container}>
      <div className={styles.authCard}>
        <div className={styles.brandHeader}>
          <span className={styles.classificationBadge}>SYSTEM ACCESS ONBOARDING // PUBLIC NODE</span>
          <BrandLogo width={120} height={40} withLink={true} />
          <h1 className={styles.title}>Institutional Registration</h1>
          <p className={styles.subtitle}>Register for access to the Urban Ecosystem Health Intelligence System.</p>
        </div>
        
        <Suspense fallback={<div className={styles.form}>Loading registration form...</div>}>
          <RegisterForm />
        </Suspense>

        <div className={styles.securityNote}>
          Protected by Supabase Auth with TLS 1.3 encryption &amp; rate-limiting.
        </div>
      </div>
    </div>
  );
}
