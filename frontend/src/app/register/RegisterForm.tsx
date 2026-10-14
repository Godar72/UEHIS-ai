'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { isSafeRedirect, isValidEmail } from '@/lib/auth-utils';
import { GoogleButton } from '@/components/auth/GoogleButton';
import styles from '../login/page.module.css';

export function RegisterForm() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  // Determine safe redirect destination
  const nextParam = searchParams.get('next');
  const safeNext = (nextParam && isSafeRedirect(nextParam)) ? nextParam : '/explore';

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    // Client-side validations
    const trimmedEmail = email.trim();
    if (!isValidEmail(trimmedEmail)) {
      setError('Please provide a valid email identity.');
      return;
    }

    if (password.length < 6) {
      setError('Passphrase must be at least 6 characters in length.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passphrases do not match. Please verify.');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: trimmedEmail,
          password,
          confirmPassword,
        }),
      });

      if (response.status === 429) {
        throw new Error('Too many registration attempts. Please try again later.');
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || 'Failed to complete registration');
      }

      if (data.confirmationRequired) {
        setSuccessMessage(
          'Registration initiated successfully. A verification link has been dispatched to your email address. Please confirm your email before signing in.'
        );
        return;
      }

      // If auto-confirmed, sign in with Supabase client to sync session
      const supabase = createClient();
      await supabase.auth.signInWithPassword({
        email: trimmedEmail,
        password,
      });

      router.refresh();
      router.push(safeNext);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to complete registration';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.formContainer}>
      {successMessage ? (
        <div className={styles.successNotice} role="status">
          <strong>VERIFICATION REQUIRED</strong>
          <p style={{ marginTop: '6px' }}>{successMessage}</p>
          <div style={{ marginTop: '14px' }}>
            <Link href="/login" className={styles.footerLink}>
              Proceed to Sign In &rarr;
            </Link>
          </div>
        </div>
      ) : (
        <>
          <form className={styles.form} onSubmit={handleRegister}>
            {error && <div className={styles.error} role="alert">{error}</div>}

            <div className={styles.inputGroup}>
              <label htmlFor="name" className={styles.label}>Full Name (Optional)</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={styles.input}
                placeholder="Dr. Anand Deshmukh"
                autoComplete="name"
                disabled={loading}
              />
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="email" className={styles.label}>Email Identity</label>
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

            <div className={styles.inputGroup}>
              <label htmlFor="password" className={styles.label}>Passphrase (Min. 6 chars)</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={styles.input}
                required
                autoComplete="new-password"
                disabled={loading}
              />
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="confirmPassword" className={styles.label}>Confirm Passphrase</label>
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

            <button
              type="submit"
              className={styles.submitBtn}
              disabled={loading}
            >
              {loading ? 'Registering...' : 'Create Account'}
            </button>
          </form>

          <div className={styles.divider}>
            <span className={styles.dividerText}>OR ONBOARD WITH GOOGLE</span>
          </div>

          <GoogleButton
            label="Continue with Google"
            nextUrl={safeNext}
            onError={(msg) => setError(msg)}
            disabled={loading}
          />

          <div className={styles.footerLinks}>
            <Link href={`/login${safeNext !== '/explore' ? `?next=${encodeURIComponent(safeNext)}` : ''}`} className={styles.footerLink}>
              Already registered? Sign in here
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
