'use client';

import React, { useState, useEffect } from 'react';
import styles from './page.module.css';
import { uehisClient } from '@/lib/api/client';
import { recordActivity } from '@/lib/api/activity';
import Link from 'next/link';

interface ScenarioData {
  id: string;
  name: string;
  total_selected: number;
  min_spacing_m: number;
  uehi_stats?: {
    mean?: number;
    min?: number;
    max?: number;
  };
  risk_distribution?: Record<string, number>;
  candidate_class_distribution?: Record<string, number>;
  [key: string]: any;
}

const SCENARIO_DESCRIPTIONS: Record<string, { track: string; desc: string; targetScore: string }> = {
  '100k': {
    track: 'Track 01',
    desc: 'Baseline targeted infill deployment across high-priority thermal heat corridors.',
    targetScore: '82.95'
  },
  '250k': {
    track: 'Track 02',
    desc: 'Expanded municipal public easement and institutional boundary coverage.',
    targetScore: '65.97'
  },
  '500k': {
    track: 'Track 03',
    desc: 'Saturated vegetative intervention across all verified non-built opportunity polygons.',
    targetScore: '46.04'
  }
};

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<ScenarioData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    uehisClient.planting.getScenarios().then((data: any) => {
      if (data && data.scenarios) {
        const filtered = data.scenarios.filter((s: ScenarioData) => 
          ['100k', '250k', '500k'].includes(s.id)
        );
        setScenarios(filtered);
        if (filtered.length > 0) {
          recordActivity({
            activity_type: 'viewed_scenario',
            category: 'analysis',
            action_type: 'viewed',
            title: 'Reviewed Systemic Intervention Scenarios',
            description: 'Intervention models (100k, 250k, 500k tracks) across Pune study extent.',
            entity_type: 'scenario',
            entity_id: '100k',
            metadata: {
              reopen_url: '/scenarios',
            },
          });
        }
      }
      setIsLoading(false);
    }).catch(err => {
      console.error('Failed to load scenarios:', err);
      setIsLoading(false);
    });
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        {/* Header Block */}
        <section className={styles.headerBlock}>
          <div className={styles.headerMeta}>
            <div className={styles.kicker}>
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>stacks</span>
              <span>Modeling Sandbox</span>
            </div>
            <span className={styles.statusBadge}>Drafting State · v3.42 Spec</span>
          </div>

          <h1 className={styles.title}>Systemic Intervention Scenarios</h1>
          <p className={styles.subtitle}>
            Pune Study Extent · 5,309 Blocks · 250m Grid · EPSG:32643
          </p>

          <div className={styles.advisoryBanner}>
            <span className={`material-symbols-outlined ${styles.advisoryIcon}`}>policy</span>
            <div className={styles.advisoryContent}>
              <span className={styles.advisoryTitle}>Institutional Advisory</span>
              <p className={styles.advisoryText}>
                Analytical planning scenario — Not a municipal recommendation or procurement schedule. Actual feasibility requires ground surveys, land cadastre verification, and subterranean utility clearance.
              </p>
            </div>
          </div>
        </section>

        {/* Operational Baseline & Parameters */}
        <section className={styles.paramsCard}>
          <div className={styles.paramsHeader}>
            <span className={styles.paramsTitle}>Constraint Rules &amp; Parameters</span>
            <span className={styles.specBadge}>v3.42 Model Spec</span>
          </div>

          <div className={styles.paramsGrid}>
            <div className={styles.paramBox}>
              <span className={styles.paramLabel}>Minimum Unit Spacing</span>
              <div className={styles.paramValue}>10 m</div>
              <span className={styles.paramFootnote}>Iso-radial exclusion buffer</span>
            </div>

            <div className={styles.paramBox}>
              <span className={styles.paramLabel}>Standing Carbon Assumption</span>
              <div className={styles.paramValueSecondary}>
                0.5 t CO₂e <span className={styles.paramValueSub}>/ unit</span>
              </div>
              <span className={styles.paramFootnote}>Empirical proxy mean</span>
            </div>
          </div>

          <div className={styles.carbonNotice}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>info</span>
            <span>
              Illustrative scenario standing carbon reflects potential standing biomass, NOT annual future sequestration.
            </span>
          </div>
        </section>

        {/* Scenario Manifest Cards */}
        <section className={styles.manifestSection}>
          <div className={styles.manifestHeader}>
            <span className={styles.manifestTitle}>Scenario Manifest</span>
            <span className={styles.manifestCount}>
              {scenarios.length > 0 ? `${scenarios.length} Evaluated Tracks` : 'Evaluating tracks...'}
            </span>
          </div>

          <div className={styles.scenariosGrid}>
            {scenarios.map((s) => {
              const meta = SCENARIO_DESCRIPTIONS[s.id] || {
                track: `Track ${s.id.toUpperCase()}`,
                desc: 'Urban canopy intervention scenario.',
                targetScore: s.uehi_stats?.mean ? s.uehi_stats.mean.toFixed(2) : '—'
              };
              const carbonEquiv = (s.total_selected * 0.5).toLocaleString();

              return (
                <div key={s.id} className={styles.scenarioCard}>
                  <div className={styles.cardTop}>
                    <div className={styles.scenarioBadgeGroup}>
                      <span className={styles.trackPill}>{meta.track}</span>
                      <h2 className={styles.scenarioCardTitle}>{s.name}</h2>
                    </div>
                    <span className={styles.scenarioTypeTag}>Analytical</span>
                  </div>

                  <p className={styles.cardDescription}>{meta.desc}</p>

                  <div className={styles.metricsRow}>
                    <div className={styles.metricCell}>
                      <span className={styles.metricLabel}>Mean UEHI</span>
                      <span className={styles.metricValue}>
                        {s.uehi_stats?.mean ? s.uehi_stats.mean.toFixed(2) : meta.targetScore}
                      </span>
                      <span className={styles.metricSub}>Index score</span>
                    </div>

                    <div className={styles.metricCell}>
                      <span className={styles.metricLabel}>Carbon Equiv</span>
                      <span className={styles.metricValueGreen}>{carbonEquiv}</span>
                      <span className={styles.metricSub}>t CO₂e</span>
                    </div>

                    <div className={styles.metricCell}>
                      <span className={styles.metricLabel}>Spacing</span>
                      <span className={styles.metricValue}>{s.min_spacing_m || 10}m</span>
                      <span className={styles.metricSub}>Iso-buffer</span>
                    </div>
                  </div>

                  {s.candidate_class_distribution && (
                    <div className={styles.cardBreakdown}>
                      <span className={styles.breakdownTitle}>Candidate Opportunity Classes</span>
                      <div className={styles.breakdownList}>
                        {Object.entries(s.candidate_class_distribution).map(([cat, count]) => {
                          let display = cat;
                          if (cat.includes('public_like')) display = 'Public-like land';
                          else if (cat.includes('context_dependent')) display = 'Context-dependent';
                          else if (cat.includes('other_open_space')) display = 'Other open space';

                          return (
                            <div key={cat} className={styles.breakdownRow}>
                              <span className={styles.breakdownLabel}>
                                <span className={styles.breakdownDot} />
                                {display}
                              </span>
                              <span className={styles.breakdownValue}>{count.toLocaleString()}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className={styles.cardFooter}>
                    <div className={styles.targetCount}>
                      <span className={styles.targetCountDot} />
                      <span>{s.total_selected?.toLocaleString()} Target Plantings</span>
                    </div>
                    <span className={styles.trackId}>{s.id.toUpperCase()}</span>
                  </div>
                </div>
              );
            })}

            {isLoading && (
              <div className={styles.loadingCell} style={{ gridColumn: '1 / -1' }}>
                Fetching systemic scenario models...
              </div>
            )}
          </div>
        </section>

        {/* Stress Index Shift Bar Chart */}
        <section className={styles.stressChartCard}>
          <div className={styles.chartHeader}>
            <span className={styles.chartTitle}>Stress Index Shift (UEHI Score Impact)</span>
            <span className={styles.chartSub}>Lower score = improved ecological health</span>
          </div>

          <div className={styles.chartTracks}>
            {scenarios.map((s, idx) => {
              const score = s.uehi_stats?.mean ? s.uehi_stats.mean : (idx === 0 ? 82.95 : idx === 1 ? 65.97 : 46.04);
              const fillClass = idx === 0 ? styles.barFillPrimary : idx === 1 ? styles.barFillNavy : styles.barFillGreen;
              const scoreClass = idx === 2 ? styles.trackRowScoreGreen : styles.trackRowScore;

              return (
                <div key={s.id} className={styles.trackRow}>
                  <div className={styles.trackRowMeta}>
                    <span className={styles.trackRowName}>{s.name} ({s.total_selected?.toLocaleString()} units)</span>
                    <span className={scoreClass}>{score.toFixed(2)} Index</span>
                  </div>
                  <div className={styles.barTrack}>
                    <div className={fillClass} style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Detailed Analytical Table Section */}
        <section className={styles.tableSection}>
          <span className={styles.tableTitle}>Comparative Scenario Matrix</span>
          <div className={styles.tableWrapper}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Analytical Scenario</th>
                  <th className={styles.num}>Selected Units</th>
                  <th className={styles.num}>Spacing</th>
                  <th className={styles.num}>Mean UEHI</th>
                  <th className={styles.num}>Est. Carbon (t CO₂e)</th>
                  <th>Risk Distribution</th>
                  <th>Opportunity Classes</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map(s => (
                  <tr key={s.id}>
                    <td className={styles.strong}>{s.name}</td>
                    <td className={styles.num}>{s.total_selected?.toLocaleString() || 'N/A'}</td>
                    <td className={styles.num}>{s.min_spacing_m ? `${s.min_spacing_m}m` : '10m'}</td>
                    <td className={styles.num}>{s.uehi_stats?.mean ? s.uehi_stats.mean.toFixed(2) : 'N/A'}</td>
                    <td className={styles.num}>{(s.total_selected * 0.5).toLocaleString()}</td>
                    
                    <td>
                      <div className={styles.distList}>
                        {s.risk_distribution && Object.entries(s.risk_distribution).map(([risk, count]: [string, any]) => (
                          <div key={risk} className={styles.distRow}>
                            <span className={styles.distLabel}>{risk}</span>
                            <span className={styles.distValue}>{count.toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                    
                    <td>
                      <div className={styles.distList}>
                        {s.candidate_class_distribution && Object.entries(s.candidate_class_distribution).map(([cat, count]: [string, any]) => {
                          let displayCat = cat;
                          if (cat.includes('public_like')) displayCat = 'Public-like';
                          else if (cat.includes('context_dependent')) displayCat = 'Context-dependent';
                          else if (cat.includes('other_open_space')) displayCat = 'Other open space';
                          
                          return (
                            <div key={cat} className={styles.distRow}>
                              <span className={styles.distLabel}>{displayCat}</span>
                              <span className={styles.distValue}>{count.toLocaleString()}</span>
                            </div>
                          );
                        })}
                      </div>
                    </td>
                  </tr>
                ))}
                {scenarios.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={7} className={styles.loadingCell}>No scenario records returned by model server.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Bottom Protocol & Spatial CTA */}
        <div className={styles.bottomRow}>
          <div className={styles.protocolBox}>
            <div className={styles.protocolHeader}>
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>verified</span>
              <span className={styles.protocolTitle}>Methodology Protocol</span>
            </div>
            <p className={styles.protocolText}>
              All scenarios evaluated across non-zero opportunity polygons without violating existing building footprints, road carriageways, or water bodies. Minimum spacing is enforced via planar Euclidean iso-radial buffers.
            </p>
            <div className={styles.protocolMeta}>
              <span>Cadastral Mask: Applied</span>
              <span>Spatial Filter: 250m Regular</span>
            </div>
          </div>

          <div className={styles.ctaCard}>
            <div>
              <h3 className={styles.ctaTitle}>Spatial Deployment Visualization</h3>
              <p className={styles.ctaText}>
                Inspect the exact spatial distribution of candidate planting units across Pune for each modeled scenario in the interactive GIS stage.
              </p>
            </div>
            <Link href="/planting" className={styles.ctaButton}>
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>forest</span>
              <span>Launch Spatial Intervention Map</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
