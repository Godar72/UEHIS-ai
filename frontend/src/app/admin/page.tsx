import React from 'react';
import { createClient } from '@/lib/supabase/server';
import { redirect } from 'next/navigation';
import { AdminDashboard } from './AdminDashboard';
import styles from './page.module.css';

export const metadata = {
  title: 'Admin Dashboard | UEHIS',
  description: 'UEHIS System Administration',
};

export default async function AdminPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect('/login');
  }

  const { data: role } = await supabase.rpc('get_user_role', { uid: user.id });

  if (role !== 'admin') {
    redirect('/');
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>System Administration</h1>
        <p className={styles.subtitle}>Manage API keys and authorized personnel</p>
      </div>
      <AdminDashboard />
    </div>
  );
}
