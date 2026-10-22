'use client';

import React, { useState, useEffect, useRef, useCallback, KeyboardEvent } from 'react';
import styles from './search.module.css';
import { Search as SearchIcon, MapPin, Map, Navigation, Loader2 } from 'lucide-react';

export interface SearchResult {
  id: string;
  name: string;
  type: string;
  secondaryLabel: string;
  longitude: number;
  latitude: number;
  provider: 'geoapify' | 'nominatim';
  inCoverage?: boolean;
}

interface SearchProps {
  onLocationSelect: (location: {
    lat: number;
    lng: number;
    name: string;
    type: string;
    inCoverage?: boolean;
  }) => void;
  placeholder?: string;
}

export function Search({ onLocationSelect, placeholder = 'Search a locality, road, or landmark in Pune' }: SearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [hintMessage, setHintMessage] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleSearch = useCallback(async (searchQuery: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/geocode?q=${encodeURIComponent(searchQuery)}`);
      if (!res.ok) {
        if (res.status === 429) {
          throw new Error('Search rate limit reached. Please wait a moment.');
        }
        throw new Error('Location search is temporarily unavailable.');
      }
      const data: SearchResult[] = await res.json();
      setResults(data);
      setIsOpen(true);
      setSelectedIndex(-1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Location search is temporarily unavailable.';
      setError(msg);
      setIsOpen(true);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounce query search when length >= 2
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) return;

    const timer = setTimeout(() => {
      handleSearch(trimmed);
    }, 400); // 400ms debounce

    return () => clearTimeout(timer);
  }, [query, handleSearch]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    const trimmed = val.trim();
    if (trimmed.length === 0) {
      setHintMessage('');
      setResults([]);
      setIsOpen(false);
    } else if (trimmed.length === 1) {
      setHintMessage('Type at least 2 characters to search Pune/PCMC.');
      setResults([]);
      setIsOpen(true);
    } else {
      setHintMessage('');
    }
  };

  const handleSelect = (result: SearchResult) => {
    const formattedName = result.name || result.secondaryLabel.split(',')[0] || 'Selected Location';

    onLocationSelect({
      lat: result.latitude,
      lng: result.longitude,
      name: formattedName,
      type: result.type,
      inCoverage: result.inCoverage !== false,
    });
    setQuery(formattedName);
    setIsOpen(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : prev));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0 && selectedIndex < results.length) {
        handleSelect(results[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const getTypeIcon = (type: string) => {
    if (['Locality', 'residential', 'neighbourhood', 'suburb', 'village'].includes(type)) {
      return <Map size={16} className={styles.resultIcon} />;
    }
    if (['Road', 'secondary', 'primary', 'tertiary', 'trunk', 'road'].includes(type)) {
      return <Navigation size={16} className={styles.resultIcon} />;
    }
    return <MapPin size={16} className={styles.resultIcon} />;
  };

  const activeProvider = results.length > 0 ? results[0].provider : 'nominatim';

  return (
    <div className={styles.searchContainer} ref={dropdownRef}>
      <div className={styles.inputWrapper}>
        <SearchIcon size={18} className={styles.searchIcon} />
        <input
          type="text"
          className={styles.searchInput}
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (query.trim().length >= 2) setIsOpen(true); }}
          aria-expanded={isOpen}
          role="combobox"
          aria-controls="search-dropdown"
        />
        {loading && <Loader2 size={16} className={`${styles.loadingIcon} ${styles.spin}`} />}
      </div>

      {hintMessage && !isOpen && (
        <div className={styles.hintState}>{hintMessage}</div>
      )}

      {isOpen && (query.trim().length >= 2) && (
        <div className={styles.dropdown} id="search-dropdown" role="listbox">
          {error ? (
            <div className={styles.errorState}>
              <div>{error}</div>
              <button
                className={styles.retryButton}
                onClick={() => handleSearch(query.trim())}
                type="button"
              >
                Retry Search
              </button>
            </div>
          ) : results.length === 0 && !loading ? (
            <div className={styles.emptyState}>
              No locations found in Pune/PCMC study area
            </div>
          ) : (
            <>
              <ul className={styles.resultList}>
                {results.map((result, index) => {
                  return (
                    <li
                      key={result.id}
                      className={`${styles.resultItem} ${index === selectedIndex ? styles.selected : ''}`}
                      onClick={() => handleSelect(result)}
                      role="option"
                      aria-selected={index === selectedIndex}
                    >
                      {getTypeIcon(result.type)}
                      <div className={styles.resultContent} style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '4px' }}>
                          <span className={styles.resultName}>{result.name}</span>
                          {result.inCoverage === false ? (
                            <span style={{
                              fontSize: '9px',
                              fontFamily: 'var(--font-jetbrains-mono)',
                              color: 'var(--risk-high)',
                              backgroundColor: 'var(--surface-container-high)',
                              padding: '1px 4px',
                              border: '1px solid var(--outline-variant)',
                              whiteSpace: 'nowrap'
                            }}>
                              OUTSIDE EXTENT
                            </span>
                          ) : (
                            <span style={{
                              fontSize: '9px',
                              fontFamily: 'var(--font-jetbrains-mono)',
                              color: 'var(--primary)',
                              backgroundColor: 'var(--green-pale)',
                              padding: '1px 4px',
                              border: '1px solid var(--outline-variant)',
                              whiteSpace: 'nowrap'
                            }}>
                              PMC/PCMC
                            </span>
                          )}
                        </div>
                        <span className={styles.resultType} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {result.type} · {result.secondaryLabel}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>

              {/* Authoritative Attribution adhering to usage policies */}
              <div style={{
                padding: '6px 12px',
                fontSize: '10px',
                fontFamily: 'var(--font-jetbrains-mono)',
                color: 'var(--on-surface-variant)',
                textAlign: 'right',
                borderTop: '1px solid var(--outline-variant)',
                backgroundColor: 'var(--surface-container-low)'
              }}>
                {activeProvider === 'nominatim' ? (
                  <span>
                    Data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'underline' }}>OpenStreetMap contributors, ODbL</a>
                  </span>
                ) : (
                  <span>
                    Powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none' }}>Geoapify</a>
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
