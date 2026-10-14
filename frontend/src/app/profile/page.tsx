import React, { Suspense } from 'react';
import { Metadata } from 'next';
import { ProfileDashboard } from './ProfileDashboard';

export const metadata: Metadata = {
  title: 'Personnel Dossier & Research Activity | UEHIS',
  description: 'Manage user credentials, display name, and inspect actual ecological research activity on the Urban Ecosystem Health Intelligence System.',
};

export default function ProfilePage() {
  return (
    <Suspense fallback={
      <div style={{
        minHeight: 'calc(100vh - 48px)',
        marginTop: '48px',
        padding: '32px 24px',
        fontFamily: 'var(--font-ibm-plex-sans), sans-serif',
        backgroundColor: 'var(--color-warm-white, #F7F6F1)',
        color: 'var(--color-seer-navy, #172B5C)'
      }}>
        <div style={{ maxWidth: '1140px', margin: '0 auto' }}>
          Loading personnel dossier...
        </div>
      </div>
    }>
      <ProfileDashboard />
    </Suspense>
  );
}
