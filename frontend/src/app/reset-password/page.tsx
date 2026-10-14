import React, { Suspense } from 'react';
import { BrandLogo } from '@/components/Brand/BrandLogo';
import { ResetPasswordForm } from './ResetPasswordForm';
import styles from '../login/page.module.css';

export const metadata = {
  title: 'Passphrase Recovery | UEHIS',
  description: 'Recover access credentials for the Urban Ecosystem Health Intelligence System',
};

export default function ResetPasswordPage() {
  return (
    <div className={styles.container}>
      <div className={styles.authCard}>
        <div className={styles.brandHeader}>
          <span className={styles.classificationBadge}>ACCOUNT RECOVERY // CREDENTIAL ROTATION</span>
          <BrandLogo width={120} height={40} withLink={true} />
          <h1 className={styles.title}>Passphrase Recovery</h1>
          <p className={styles.subtitle}>Dispatch an authorized recovery token or update credentials.</p>
        </div>
        
        <Suspense fallback={<div className={styles.form}>Loading recovery options...</div>}>
          <ResetPasswordForm />
        </Suspense>

        <div className={styles.securityNote}>
          Protected by Supabase Auth with TLS 1.3 encryption &amp; rate-limiting.
        </div>
      </div>
    </div>
  );
}
