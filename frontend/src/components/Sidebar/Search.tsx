'use client';

import React, { useState, useEffect, useRef, KeyboardEvent } from 'react';
import styles from './search.module.css';
import { Search as SearchIcon, MapPin, Map, Navigation, Loader2 } from 'lucide-react';

// Additional state for hint message when query is too short


interface SearchResult {
  id: string;
  name: string;
  type: string;
  secondaryLabel: string;
  longitude: number;
  latitude: number;
  provider: string;
}

interface SearchProps {
  onLocationSelect: (location: { lat: number; lng: number; name: string; type: string }) => void;
}

export function Search({ onLocationSelect }: SearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [hintMessage, setHintMessage] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounce query
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length === 0) {
      setHintMessage('');
      setResults([]);
      setIsOpen(false);
      return;
    }
    if (trimmed.length === 1) {
      setHintMessage('Type at least 2 characters.');
      setResults([]);
      setIsOpen(true);
      return;
    }
    setHintMessage('');
    const timer = setTimeout(() => {
      handleSearch(trimmed);
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSearch = async (searchQuery: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/geocode?q=${encodeURIComponent(searchQuery)}`);
      if (!res.ok) {
        throw new Error('Search unavailable');
      }
      const data = await res.json();
      setResults(data);
      setIsOpen(true);
      setSelectedIndex(-1);
    } catch (err) {
      setError('Location search is temporarily unavailable.');
      setIsOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (result: SearchResult) => {
    let formattedName = result.name || result.secondaryLabel.split(',')[0];

    let resultType = result.type;
    // Map internal types to user-friendly types
    if (['residential', 'neighbourhood', 'suburb', 'village'].includes(result.type)) {
      resultType = 'Locality';
    } else if (['secondary', 'primary', 'tertiary', 'trunk', 'road', 'street'].includes(result.type)) {
      resultType = 'Road';
    } else if (['historic', 'attraction', 'museum', 'monument', 'ruins', 'tourism'].includes(result.type)) {
      resultType = 'Landmark';
    } else if (['city', 'town', 'county', 'state'].includes(result.type)) {
      resultType = 'Area';
    } else {
      resultType = result.type.charAt(0).toUpperCase() + result.type.slice(1);
    }

    onLocationSelect({
      lat: result.latitude,
      lng: result.longitude,
      name: formattedName,
      type: resultType
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
    if (['residential', 'neighbourhood', 'suburb', 'village', 'Locality'].includes(type)) return <Map size={16} className={styles.resultIcon} />;
    if (['secondary', 'primary', 'tertiary', 'trunk', 'road', 'Road'].includes(type)) return <Navigation size={16} className={styles.resultIcon} />;
    return <MapPin size={16} className={styles.resultIcon} />;
  };

  return (
    <div className={styles.searchContainer} ref={dropdownRef}>
      <div className={styles.inputWrapper}>
        <SearchIcon size={18} className={styles.searchIcon} />
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search a locality, road, or landmark"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (query.length >= 2) setIsOpen(true); }}
          aria-expanded={isOpen}
          role="combobox"
          aria-controls="search-dropdown"
        />
        {loading && <Loader2 size={16} className={`${styles.loadingIcon} ${styles.spin}`} />}
      </div>

      {hintMessage && !isOpen && (
        <div className={styles.hintState}>{hintMessage}</div>
      )}

      {isOpen && (query.length >= 2) && (
        <div className={styles.dropdown} id="search-dropdown" role="listbox">
          {error ? (
            <div className={styles.errorState}>
              {error}
              <button
                className={styles.retryButton}
                onClick={() => handleSearch(query)}
                type="button"
              >Retry</button>
            </div>
          ) : results.length === 0 && !loading ? (
            <div className={styles.emptyState}>No locations found</div>
          ) : (
            <>
              <ul className={styles.resultList}>
                {results.map((result, index) => {
                  let resultType = result.type;
                  if (['residential', 'neighbourhood', 'suburb', 'village'].includes(result.type)) {
                    resultType = 'Locality';
                  } else if (['secondary', 'primary', 'tertiary', 'trunk', 'road', 'street'].includes(result.type)) {
                    resultType = 'Road';
                  } else if (['historic', 'attraction', 'museum', 'monument', 'ruins', 'tourism'].includes(result.type)) {
                    resultType = 'Landmark';
                  } else if (['city', 'town', 'county', 'state'].includes(result.type)) {
                    resultType = 'Area';
                  } else {
                    resultType = result.type.charAt(0).toUpperCase() + result.type.slice(1);
                  }

                  // Add 'Pune' context if available
                  const contextName = result.secondaryLabel.includes('Pune') ? 'Pune' : 'India';

                  return (
                    <li
                      key={result.id}
                      className={`${styles.resultItem} ${index === selectedIndex ? styles.selected : ''}`}
                      onClick={() => handleSelect(result)}
                      role="option"
                      aria-selected={index === selectedIndex}
                    >
                      {getTypeIcon(resultType)}
                      <div className={styles.resultContent}>
                        <span className={styles.resultName}>{result.name || result.secondaryLabel.split(',')[0]}</span>
                        <span className={styles.resultType}>{resultType} · {contextName}</span>
                      </div>
                    </li>
                  );
                })}
              </ul>
              {results.length > 0 && (
                <div style={{ padding: '8px 12px', fontSize: '0.7rem', color: '#65706B', textAlign: 'right', borderTop: '1px solid #F7F6F1' }}>
                  Powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener noreferrer" style={{ color: '#294577', textDecoration: 'none' }}>Geoapify</a>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
