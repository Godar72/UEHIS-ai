import styles from './explore.module.css';

export default function ExploreLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.layout}>
      <main className={styles.main}>
        {children}
      </main>
    </div>
  );
}
