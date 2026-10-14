'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { isSafeRedirect } from '@/lib/auth-utils';
import { GoogleButton } from '@/components/auth/GoogleButton';
import styles from './page.module.css';

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();
  const errorParam = searchParams.get('error');
  const [error, setError] = useState<string | null>(errorParam ? decodeURIComponent(errorParam) : null);
  const [loading, setLoading] = useState(false);

  // Determine safe redirect destination
  const nextParam = searchParams.get('next');
  const safeNext = (nextParam && isSafeRedirect(nextParam)) ? nextParam : '/explore';

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return; // Prevent concurrent submissions
    setError(null);
    setLoading(true);

    try {
      // Use server-side login route with account-aware and network-aware rate limiting
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      if (response.status === 429) {
        const retryHeader = response.headers.get('Retry-After');
        const data = await response.json().catch(() => ({}));
        const retrySec = data.retryAfter || (retryHeader ? parseInt(retryHeader, 10) : null);
        if (retrySec && !isNaN(retrySec) && retrySec > 0) {
          throw new Error(`Too many login attempts. Please try again in ${retrySec} second${retrySec === 1 ? '' : 's'}.`);
        }
        throw new Error(data.error || 'Too many login attempts. Please try again later.');
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Invalid credentials');
      }

      // Sync browser client state
      const supabase = createClient();
      const { error: clientError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (clientError) {
        console.warn('Client-side auth sync notice:', clientError.message);
      }

      // Flush router cache so new session cookie is recognized
      router.refresh();
      router.push(safeNext);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Invalid credentials';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.formContainer}>
      <form className={styles.form} onSubmit={handleLogin}>
        {error && <div className={styles.error} role="alert">{error}</div>}
        
        <div className={styles.inputGroup}>
          <label htmlFor="email" className={styles.label}>Email Identity</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (error) setError(null);
            }}
            className={styles.input}
            required
            placeholder="personnel@uehis.org"
            autoComplete="email"
            disabled={loading}
          />
        </div>

        <div className={styles.inputGroup}>
          <label htmlFor="password" className={styles.label}>Passphrase</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (error) setError(null);
            }}
            className={styles.input}
            required
            autoComplete="current-password"
            disabled={loading}
          />
        </div>

        <button 
          type="submit" 
          className={styles.submitBtn}
          disabled={loading}
        >
          {loading ? 'Authenticating...' : 'Sign In'}
        </button>
      </form>

      <div className={styles.divider}>
        <span className={styles.dividerText}>OR FEDERATED ACCESS</span>
      </div>

      <GoogleButton
        label="Continue with Google"
        nextUrl={safeNext}
        onError={(msg) => setError(msg)}
        disabled={loading}
      />

      <div className={styles.footerLinks}>
        <Link href={`/register${safeNext !== '/explore' ? `?next=${encodeURIComponent(safeNext)}` : ''}`} className={styles.footerLink}>
          Need an account? Register for access
        </Link>
        <Link href="/reset-password" className={styles.footerLink}>
          Forgot passphrase? Request recovery
        </Link>
      </div>
    </div>
  );
}
