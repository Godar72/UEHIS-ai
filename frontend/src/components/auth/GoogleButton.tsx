'use client';

import React, { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { isSafeRedirect } from '@/lib/auth-utils';
import styles from './GoogleButton.module.css';

interface GoogleButtonProps {
  label?: string;
  nextUrl?: string;
  onError?: (error: string) => void;
  disabled?: boolean;
}

export function GoogleButton({
  label = 'Continue with Google',
  nextUrl = '/explore',
  onError,
  disabled = false,
}: GoogleButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleGoogleSignIn = async () => {
    if (loading || disabled) return;
    setLoading(true);

    try {
      const supabase = createClient();
      const safeDestination = isSafeRedirect(nextUrl) ? nextUrl : '/explore';
      const origin = typeof window !== 'undefined' ? window.location.origin : '';
      const callbackUrl = `${origin}/auth/callback?next=${encodeURIComponent(safeDestination)}`;

      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: callbackUrl,
          skipBrowserRedirect: true,
          queryParams: {
            access_type: 'offline',
            prompt: 'consent',
          },
        },
      });

      if (error) {
        // Distinguish provider configuration error from other errors
        if (
          error.message?.toLowerCase().includes('unsupported provider') ||
          error.message?.toLowerCase().includes('not enabled') ||
          error.message?.toLowerCase().includes('configuration')
        ) {
          throw new Error('Google OAuth is not configured in this environment. Please authenticate with email and passphrase.');
        }
        throw error;
      }

      if (!data?.url) {
        throw new Error('Failed to initialize Google authentication URL');
      }

      // Preflight probe the authorization URL to check if provider is enabled
      // Prevents redirecting the user to a raw JSON backend error page (HTTP 400 Unsupported provider)
      try {
        const probeResponse = await fetch(data.url, {
          method: 'GET',
          redirect: 'manual',
        });

        if (probeResponse.status === 400) {
          const errData = await probeResponse.json().catch(() => null);
          const msg = errData?.msg || '';
          if (
            msg.toLowerCase().includes('unsupported provider') ||
            msg.toLowerCase().includes('not enabled') ||
            errData?.error_code === 'validation_failed'
          ) {
            throw new Error('Google OAuth is not configured in this environment. Please authenticate with email and passphrase.');
          }
          throw new Error(msg || 'Google OAuth provider rejected authorization request.');
        }

        // If probe returned an unexpected HTTP failure
        if (!probeResponse.ok && probeResponse.type !== 'opaqueredirect' && probeResponse.status !== 0 && probeResponse.status !== 302 && probeResponse.status !== 303) {
          throw new Error(`Google OAuth service returned HTTP ${probeResponse.status}.`);
        }
      } catch (probeErr: unknown) {
        if (probeErr instanceof Error) {
          throw probeErr;
        }
        throw new Error('Unable to connect to Google OAuth provider. Please authenticate with email and passphrase.');
      }

      // Provider is enabled and ready to redirect to Google accounts
      window.location.href = data.url;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to initiate Google sign-in';
      console.warn('Google OAuth initiation notice:', message);
      if (onError) {
        onError(message);
      }
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleGoogleSignIn}
      disabled={disabled || loading}
      className={styles.googleBtn}
      aria-label={label}
    >
      {loading ? (
        <span className={styles.loadingSpinner} aria-hidden="true" />
      ) : (
        <svg
          className={styles.googleIcon}
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
          />
        </svg>
      )}
      <span>{loading ? 'Connecting to Google...' : label}</span>
    </button>
  );
}
