'use client';

import React, { useState, useEffect } from 'react';
import styles from './page.module.css';

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
}

export function AdminDashboard() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const res = await fetch('/api/admin/keys');
      if (res.ok) {
        const data = await res.json();
        setKeys(data);
      }
    } catch (error) {
      console.error('Failed to fetch keys', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/admin/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newKeyName })
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedKey(data.plaintext_key);
        setNewKeyName('');
        fetchKeys();
      }
    } catch (error) {
      console.error('Failed to create key', error);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm('Are you sure you want to revoke this key?')) return;
    try {
      await fetch(`/api/admin/keys/${id}`, { method: 'DELETE' });
      fetchKeys();
    } catch (error) {
      console.error('Failed to revoke key', error);
    }
  };

  return (
    <div className={styles.dashboard}>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>API Keys</h2>
        
        {generatedKey && (
          <div className={styles.warningBox}>
            <p className={styles.warningTitle}>⚠️ Key Generated Successfully</p>
            <p>This key will only be shown once. Store it securely.</p>
            <code className={styles.plaintextKey}>{generatedKey}</code>
            <button onClick={() => setGeneratedKey(null)} className={styles.dismissBtn}>Dismiss</button>
          </div>
        )}

        <form onSubmit={handleCreateKey} className={styles.createForm}>
          <input 
            type="text" 
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key Name (e.g. Production Service)"
            className={styles.input}
            required
          />
          <button type="submit" className={styles.createBtn}>Generate Key</button>
        </form>

        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Prefix</th>
                <th>Created</th>
                <th>Last Used</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5}>Loading...</td></tr>
              ) : keys.length === 0 ? (
                <tr><td colSpan={5}>No API keys found.</td></tr>
              ) : keys.map(k => (
                <tr key={k.id}>
                  <td>{k.name}</td>
                  <td className={styles.mono}>{k.key_prefix}</td>
                  <td>{new Date(k.created_at).toLocaleDateString()}</td>
                  <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}</td>
                  <td>
                    <button onClick={() => handleRevoke(k.id)} className={styles.revokeBtn}>Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
