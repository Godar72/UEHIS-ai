'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { isValidEmail } from '@/lib/auth-utils';
import styles from '../login/page.module.css';

export function ResetPasswordForm() {
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isUpdateMode, setIsUpdateMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Check if user is in an active recovery session
    const supabase = createClient();
    supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setIsUpdateMode(true);
      }
    });

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setIsUpdateMode(true);
      }
    });
  }, []);

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStatusMessage(null);

    const trimmed = email.trim();
    if (!isValidEmail(trimmed)) {
      setError('Please provide a valid email address.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: trimmed }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Failed to dispatch reset request');
      }

      setStatusMessage(
        data.message || 'If an account exists with this email address, password reset instructions have been dispatched.'
      );
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to dispatch reset request';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStatusMessage(null);

    if (newPassword.length < 6) {
      setError('New passphrase must be at least 6 characters in length.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passphrases do not match.');
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();
      const { error: updateError } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (updateError) {
        throw updateError;
      }

      setStatusMessage('Passphrase updated successfully. Redirecting to workspace...');
      setTimeout(() => {
        router.refresh();
        router.push('/explore');
      }, 1500);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update passphrase';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.formContainer}>
      {statusMessage && (
        <div className={styles.successNotice} role="status">
          <strong>RECOVERY NOTICE</strong>
          <p style={{ marginTop: '6px' }}>{statusMessage}</p>
        </div>
      )}

      {error && <div className={styles.error} role="alert">{error}</div>}

      {isUpdateMode ? (
        <form className={styles.form} onSubmit={handleUpdatePassword}>
          <div className={styles.inputGroup}>
            <label htmlFor="newPassword" className={styles.label}>New Passphrase (Min. 6 chars)</label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={styles.input}
              required
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          <div className={styles.inputGroup}>
            <label htmlFor="confirmPassword" className={styles.label}>Confirm New Passphrase</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={styles.input}
              required
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? 'Updating...' : 'Set New Passphrase'}
          </button>
        </form>
      ) : (
        <form className={styles.form} onSubmit={handleRequestReset}>
          <div className={styles.inputGroup}>
            <label htmlFor="email" className={styles.label}>Registered Email Identity</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={styles.input}
              required
              placeholder="personnel@uehis.org"
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? 'Dispatching...' : 'Request Recovery Link'}
          </button>
        </form>
      )}

      <div className={styles.footerLinks}>
        <Link href="/login" className={styles.footerLink}>
          &larr; Return to Sign In
        </Link>
      </div>
    </div>
  );
}
