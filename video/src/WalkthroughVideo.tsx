import { Sequence, Img, Audio, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig, AbsoluteFill } from 'remotion';
import React from 'react';

/**
 * MCP Memory Service — Web Dashboard Walkthrough Video
 *
 * Key design decisions:
 * - Scene durations derived from actual voiceover audio lengths (+ breathing room)
 * - Crossfade transitions: scenes overlap visually but audio is strictly sequential
 * - No black screens: each scene has its own dark background during fade
 */

// ─── Scene definitions with audio-matched durations ────────────────────────
// Audio durations measured from the generated MP3 files (in seconds)
// Scene frame count = ceil(audioDuration * fps) + BREATH_FRAMES
const FPS = 30;
const BREATH_FRAMES = 30; // 1s breathing pause after voiceover finishes
const CROSSFADE_FRAMES = 15; // 0.5s visual crossfade overlap

interface SceneConfig {
  id: string;
  screenshot: string; // empty string for animated (text-only) scenes
  audio: string;
  audioDuration: number; // seconds
  title: string;
  subtitle: string;
  description: string;
  // Optional: for animated feature scenes (no screenshot)
  featureItems?: string[];
  featureEmoji?: string;
  // Optional: for comparison scenes (two-column without/with)
  comparisonItems?: { without: string; with: string }[];
}

const INTRO_AUDIO = 'walkthrough/audio/00-intro.mp3';
const INTRO_AUDIO_DUR = 45.93;
const OUTRO_AUDIO = 'walkthrough/audio/09-outro.mp3';
const OUTRO_AUDIO_DUR = 6.32;
const OUTRO_HOLD_FRAMES = 90; // 3s extra hold after audio ends

const SCENES: SceneConfig[] = [
  {
    id: 'dashboard',
    screenshot: 'walkthrough/01-dashboard.png',
    audio: 'walkthrough/audio/01-01-dashboard.mp3',
    audioDuration: 18.62,
    title: 'Dashboard Overview',
    subtitle: 'Your command center for 8,000+ AI memories',
    description: 'Real-time stats, recent memories, and quick actions at a glance.',
  },
  {
    id: 'search',
    screenshot: 'walkthrough/02-search.png',
    audio: 'walkthrough/audio/02-02-search.mp3',
    audioDuration: 15.28,
    title: 'Semantic Search',
    subtitle: 'Find any memory with natural language',
    description: 'Live search with filters for tags, date ranges, and content types.',
  },
  {
    id: 'browse',
    screenshot: 'walkthrough/03b-browse-filtered.png',
    audio: 'walkthrough/audio/03-03-browse.mp3',
    audioDuration: 22.34,
    title: 'Browse by Tags',
    subtitle: 'Click any tag to filter memories',
    description: 'Interactive tag cloud organized by frequency. Click to filter, then inspect details.',
  },
  {
    id: 'documents',
    screenshot: 'walkthrough/04-documents.png',
    audio: 'walkthrough/audio/04-04-documents.mp3',
    audioDuration: 14.35,
    title: 'Document Ingestion',
    subtitle: 'Ingest PDFs, markdown, and more',
    description: 'Drag-and-drop upload with configurable chunking and overlap.',
  },
  {
    id: 'manage',
    screenshot: 'walkthrough/05-manage.png',
    audio: 'walkthrough/audio/05-05-manage.mp3',
    audioDuration: 14.72,
    title: 'Memory Management',
    subtitle: 'Bulk operations and tag governance',
    description: 'Cleanup duplicates, manage tags, and maintain data quality.',
  },
  {
    id: 'analytics',
    screenshot: 'walkthrough/06-analytics.png',
    audio: 'walkthrough/audio/06-06-analytics.mp3',
    audioDuration: 20.53,
    title: 'Analytics Dashboard',
    subtitle: 'Track growth and usage patterns',
    description: 'Memory growth trends, tag distribution, and database metrics.',
  },
  {
    id: 'knowledge-graph',
    screenshot: 'walkthrough/09-knowledge-graph.png',
    audio: 'walkthrough/audio/10-09-knowledge-graph.mp3',
    audioDuration: 26.80,
    title: 'Knowledge Graph',
    subtitle: 'Visualize memory connections',
    description: 'Observations, decisions, learnings — mapped and color-coded in real time.',
  },
  {
    id: 'quality',
    screenshot: 'walkthrough/07-quality.png',
    audio: 'walkthrough/audio/07-07-quality.mp3',
    audioDuration: 14.63,
    title: 'Quality Analytics',
    subtitle: 'AI-powered quality scoring',
    description: 'Score distribution, provider breakdown, and quality tiers.',
  },
  {
    id: 'api-docs',
    screenshot: 'walkthrough/08-api-docs.png',
    audio: 'walkthrough/audio/08-08-api-docs.mp3',
    audioDuration: 17.37,
    title: 'API Documentation',
    subtitle: 'Full REST API reference',
    description: 'Interactive Swagger UI, ReDoc, and categorized endpoint overview.',
  },
  {
    id: 'swagger-api',
    screenshot: 'walkthrough/10-swagger-ui.png',
    audio: 'walkthrough/audio/11-10-swagger-api.mp3',
    audioDuration: 26.15,
    title: 'Live REST API',
    subtitle: 'Test every endpoint interactively',
    description: 'Store, search, tag, stream — full CRUD with Server-Sent Events.',
  },
  {
    id: 'memory-hooks',
    screenshot: '',
    audio: 'walkthrough/audio/13-12-memory-hooks.mp3',
    audioDuration: 24.61,
    title: 'Memory Awareness Hooks',
    subtitle: 'Seamless Claude Code integration',
    description: 'Automatic store and recall during coding sessions.',
    featureEmoji: '🔗',
    featureItems: [
      'Session-start hooks load relevant project memories',
      'Mid-conversation hooks capture solutions in real time',
      'Session-end hooks consolidate learnings automatically',
      'Prior context recalled seamlessly in later sessions',
    ],
  },
  {
    id: 'dream-consolidation',
    screenshot: '',
    audio: 'walkthrough/audio/12-11-dream-consolidation.mp3',
    audioDuration: 24.43,
    title: 'Dream-Based Consolidation',
    subtitle: 'Inspired by human memory processing',
    description: 'Automatic cleanup during idle periods.',
    featureEmoji: '🌙',
    featureItems: [
      'Merges near-duplicate memories automatically',
      'Strengthens important connections between entries',
      'Decays low-quality or outdated information',
      'Keeps your knowledge base lean over time',
    ],
  },
  {
    id: 'enterprise',
    screenshot: '',
    audio: 'walkthrough/audio/14-13-enterprise.mp3',
    audioDuration: 28.33,
    title: 'Enterprise Ready',
    subtitle: 'Secure, distributed, team-grade',
    description: 'Built for production deployment across organizations.',
    featureEmoji: '🏢',
    featureItems: [
      'OAuth 2.1 with Dynamic Client Registration',
      'Cloudflare Vectorize, D1, and Workers AI integration',
      'Multi-instance database synchronization',
      'Hybrid backend: local + cloud across team boundaries',
    ],
  },
];

// Compute frame duration for each scene: audio duration + breathing room
function sceneDuration(audioDur: number): number {
  return Math.ceil(audioDur * FPS) + BREATH_FRAMES;
}

const INTRO_FRAMES = sceneDuration(INTRO_AUDIO_DUR);
const OUTRO_FRAMES = sceneDuration(OUTRO_AUDIO_DUR) + OUTRO_HOLD_FRAMES;

// ─── Visual Components ─────────────────────────────────────────────────────

/** Dark background that persists during crossfades (prevents black frames) */
const DarkBackground: React.FC = () => (
  <AbsoluteFill style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)' }} />
);

/** Intro scene — title phase then comparison table */
const TITLE_PHASE_END = 7 * FPS; // ~7s: transition from title to comparison
const COMPARISON_ITEMS = [
  { without: 'Every agent run starts from zero', with: 'Retrieve prior decisions in 5ms' },
  { without: 'Memory locked to one session', with: 'Shared across all agents and runs' },
  { without: 'Redis + Pinecone + glue code', with: 'One self-hosted service, zero cloud cost' },
  { without: 'No relationships between facts', with: 'Knowledge graph with typed edges' },
];

const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();

  // --- Title phase (frames 0 – TITLE_PHASE_END) ---
  const titleIn = interpolate(frame, [10, 35], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subtitleIn = interpolate(frame, [35, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  // Title fades out as comparison fades in
  const titlePhaseOut = interpolate(frame, [TITLE_PHASE_END - 15, TITLE_PHASE_END], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // --- Comparison phase (frames TITLE_PHASE_END onwards) ---
  const compIn = interpolate(frame, [TITLE_PHASE_END, TITLE_PHASE_END + 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const compTitleIn = interpolate(frame, [TITLE_PHASE_END + 5, TITLE_PHASE_END + 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const compSubtitleIn = interpolate(frame, [TITLE_PHASE_END + 15, TITLE_PHASE_END + 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const headerIn = interpolate(frame, [TITLE_PHASE_END + 30, TITLE_PHASE_END + 45], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Title phase */}
      {titlePhaseOut > 0 && (
        <AbsoluteFill style={{ opacity: titlePhaseOut }}>
          <div style={{
            width: '100%', height: '100%',
            display: 'flex', flexDirection: 'column',
            justifyContent: 'center', alignItems: 'center',
          }}>
            <div style={{
              opacity: titleIn,
              fontSize: 72, fontWeight: 800, color: '#fff',
              fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
            }}>
              🧠 MCP Memory Service
            </div>
            <div style={{
              opacity: subtitleIn, fontSize: 36, color: '#60a5fa',
              fontFamily: 'Inter, system-ui, sans-serif', marginTop: 16,
            }}>
              Persistent Semantic Memory for AI Agents
            </div>
            <div style={{
              opacity: subtitleIn, fontSize: 24, color: '#94a3b8',
              fontFamily: 'Inter, system-ui, sans-serif', marginTop: 24,
            }}>
              v10.31.2
            </div>
          </div>
        </AbsoluteFill>
      )}

      {/* Comparison phase */}
      {compIn > 0 && (
        <AbsoluteFill style={{ opacity: compIn }}>
          <div style={{
            width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
            justifyContent: 'center', alignItems: 'center', padding: '40px 100px',
          }}>
            <div style={{ opacity: compTitleIn, fontSize: 72, marginBottom: 12 }}>🧠</div>
            <div style={{
              opacity: compTitleIn, fontSize: 48, fontWeight: 800, color: '#fff',
              fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
            }}>MCP Memory Service</div>
            <div style={{
              opacity: compSubtitleIn, fontSize: 28, color: '#60a5fa',
              fontFamily: 'Inter, system-ui, sans-serif', marginTop: 8, textAlign: 'center',
            }}>Persistent Semantic Memory for AI Agents</div>

            {/* Column headers */}
            <div style={{
              opacity: headerIn, display: 'flex', gap: 40,
              marginTop: 40, width: '100%', maxWidth: 1400,
            }}>
              <div style={{
                flex: 1, fontSize: 22, fontWeight: 700, color: '#f87171',
                fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
                paddingBottom: 12, borderBottom: '2px solid rgba(248,113,113,0.3)',
              }}>Without</div>
              <div style={{
                flex: 1, fontSize: 22, fontWeight: 700, color: '#4ade80',
                fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
                paddingBottom: 12, borderBottom: '2px solid rgba(74,222,128,0.3)',
              }}>With MCP Memory Service</div>
            </div>

            {/* Comparison rows */}
            {COMPARISON_ITEMS.map((item, i) => {
              const rowStart = TITLE_PHASE_END + 45 + i * 18;
              const rowOpacity = interpolate(frame, [rowStart, rowStart + 15], [0, 1], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              });
              return (
                <div key={i} style={{
                  opacity: rowOpacity, display: 'flex', gap: 40,
                  width: '100%', maxWidth: 1400, marginTop: 16,
                }}>
                  <div style={{
                    flex: 1, fontSize: 22, color: '#fca5a5',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    padding: '12px 20px', backgroundColor: 'rgba(248,113,113,0.08)',
                    borderRadius: 8, borderLeft: '3px solid #f87171',
                  }}>{item.without}</div>
                  <div style={{
                    flex: 1, fontSize: 22, color: '#86efac',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    padding: '12px 20px', backgroundColor: 'rgba(74,222,128,0.08)',
                    borderRadius: 8, borderLeft: '3px solid #4ade80',
                  }}>{item.with}</div>
                </div>
              );
            })}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/** Walkthrough scene with screenshot + animated text overlay + crossfade */
const WalkthroughScene: React.FC<{
  scene: SceneConfig;
  totalFrames: number;
}> = ({ scene, totalFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Crossfade: fade in at start, fade out at end
  const fadeIn = interpolate(frame, [0, CROSSFADE_FRAMES], [0, 1], { extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [totalFrames - CROSSFADE_FRAMES, totalFrames], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const sceneOpacity = Math.min(fadeIn, fadeOut);

  // Subtle Ken Burns zoom
  const scale = interpolate(frame, [0, totalFrames], [1.0, 1.04], { extrapolateRight: 'clamp' });

  // Text overlay animations (appear after fade-in settles)
  const textStart = CROSSFADE_FRAMES + 5;
  // Text overlay fades in and HOLDS — scene crossfade handles exit
  const overlayOpacity = interpolate(frame,
    [textStart, textStart + 20],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  const titleSlide = spring({ frame: frame - textStart, fps, config: { damping: 14 } }) * 100;
  const subtitleSlide = spring({ frame: frame - textStart - 8, fps, config: { damping: 14 } }) * 100;
  const descSlide = spring({ frame: frame - textStart - 16, fps, config: { damping: 14 } }) * 100;

  return (
    <AbsoluteFill style={{ opacity: sceneOpacity }}>
      <DarkBackground />
      {/* Screenshot */}
      <Img
        src={staticFile(scene.screenshot)}
        style={{
          width: '100%', height: '100%', objectFit: 'cover',
          transform: `scale(${scale})`, transformOrigin: 'center center',
        }}
      />
      {/* Bottom gradient */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: '35%',
        background: 'linear-gradient(transparent, rgba(15,23,42,0.95))',
        opacity: overlayOpacity,
      }} />
      {/* Text overlay */}
      <div style={{
        position: 'absolute', bottom: 40, left: 60, right: 60,
        opacity: overlayOpacity,
      }}>
        <div style={{
          fontSize: 48, fontWeight: 800, color: '#fff',
          fontFamily: 'Inter, system-ui, sans-serif',
          transform: `translateX(${100 - titleSlide}px)`,
          textShadow: '0 2px 8px rgba(0,0,0,0.7)',
        }}>{scene.title}</div>
        <div style={{
          fontSize: 28, color: '#60a5fa', marginTop: 8,
          fontFamily: 'Inter, system-ui, sans-serif',
          transform: `translateX(${100 - subtitleSlide}px)`,
          textShadow: '0 2px 6px rgba(0,0,0,0.7)',
        }}>{scene.subtitle}</div>
        <div style={{
          fontSize: 22, color: '#cbd5e1', marginTop: 12,
          fontFamily: 'Inter, system-ui, sans-serif',
          transform: `translateX(${100 - descSlide}px)`,
          textShadow: '0 1px 4px rgba(0,0,0,0.7)',
        }}>{scene.description}</div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Feature scene (no screenshot, text-based with item list).
 * Staggered fade-in for each element, all hold visible once shown.
 * No fade-out — next scene covers via its own fade-in layer.
 */
const FeatureScene: React.FC<{
  scene: SceneConfig;
  totalFrames: number;
}> = ({ scene }) => {
  const frame = useCurrentFrame();

  // Simple fade-in helpers — once at 1, stays at 1 (clamp)
  const emoji = interpolate(frame, [5, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const title = interpolate(frame, [15, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subtitle = interpolate(frame, [25, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      <div style={{
        width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center', padding: '60px 120px',
      }}>
        <div style={{ opacity: emoji, fontSize: 96, marginBottom: 20 }}>
          {scene.featureEmoji || '⚡'}
        </div>
        <div style={{
          opacity: title, fontSize: 56, fontWeight: 800, color: '#fff',
          fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
        }}>{scene.title}</div>
        <div style={{
          opacity: subtitle, fontSize: 30, color: '#60a5fa',
          fontFamily: 'Inter, system-ui, sans-serif', marginTop: 12, textAlign: 'center',
        }}>{scene.subtitle}</div>
        <div style={{ marginTop: 48, maxWidth: 900 }}>
          {(scene.featureItems || []).map((item, i) => {
            const itemOpacity = interpolate(frame, [40 + i * 15, 55 + i * 15], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            });
            return (
              <div key={i} style={{
                opacity: itemOpacity,
                display: 'flex', alignItems: 'center', gap: 16,
                marginBottom: 20,
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', backgroundColor: '#60a5fa',
                  flexShrink: 0,
                }} />
                <div style={{
                  fontSize: 26, color: '#e2e8f0',
                  fontFamily: 'Inter, system-ui, sans-serif',
                }}>{item}</div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Comparison scene — two-column "Without vs With" layout.
 * All content static, no fade-out.
 */
const ComparisonScene: React.FC<{
  scene: SceneConfig;
  totalFrames: number;
}> = ({ scene }) => {
  const frame = useCurrentFrame();

  const emoji = interpolate(frame, [5, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const title = interpolate(frame, [15, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subtitle = interpolate(frame, [25, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const headerOpacity = interpolate(frame, [40, 55], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      <div style={{
        width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center', padding: '40px 100px',
      }}>
        <div style={{ opacity: emoji, fontSize: 72, marginBottom: 12 }}>
          {scene.featureEmoji || '🧠'}
        </div>
        <div style={{
          opacity: title, fontSize: 48, fontWeight: 800, color: '#fff',
          fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
        }}>{scene.title}</div>
        <div style={{
          opacity: subtitle, fontSize: 28, color: '#60a5fa',
          fontFamily: 'Inter, system-ui, sans-serif', marginTop: 8, textAlign: 'center',
        }}>{scene.subtitle}</div>

        {/* Column headers */}
        <div style={{
          opacity: headerOpacity, display: 'flex', gap: 40,
          marginTop: 40, width: '100%', maxWidth: 1400,
        }}>
          <div style={{
            flex: 1, fontSize: 22, fontWeight: 700, color: '#f87171',
            fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
            paddingBottom: 12, borderBottom: '2px solid rgba(248,113,113,0.3)',
          }}>Without</div>
          <div style={{
            flex: 1, fontSize: 22, fontWeight: 700, color: '#4ade80',
            fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
            paddingBottom: 12, borderBottom: '2px solid rgba(74,222,128,0.3)',
          }}>With MCP Memory Service</div>
        </div>

        {/* Comparison rows */}
        {(scene.comparisonItems || []).map((item, i) => {
          const rowStart = 55 + i * 18;
          const rowOpacity = interpolate(frame, [rowStart, rowStart + 15], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });
          return (
            <div key={i} style={{
              opacity: rowOpacity, display: 'flex', gap: 40,
              width: '100%', maxWidth: 1400, marginTop: 16,
            }}>
              <div style={{
                flex: 1, fontSize: 22, color: '#fca5a5',
                fontFamily: 'Inter, system-ui, sans-serif',
                padding: '12px 20px', backgroundColor: 'rgba(248,113,113,0.08)',
                borderRadius: 8, borderLeft: '3px solid #f87171',
              }}>{item.without}</div>
              <div style={{
                flex: 1, fontSize: 22, color: '#86efac',
                fontFamily: 'Inter, system-ui, sans-serif',
                padding: '12px 20px', backgroundColor: 'rgba(74,222,128,0.08)',
                borderRadius: 8, borderLeft: '3px solid #4ade80',
              }}>{item.with}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Outro scene — all content visible immediately, holds until end */
const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const contentOpacity = interpolate(frame, [10, 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const linkOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      <div style={{
        width: '100%', height: '100%',
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
      }}>
        <div style={{
          opacity: contentOpacity, fontSize: 56, fontWeight: 800, color: '#fff',
          fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'center',
        }}>Get Started</div>
        <div style={{
          opacity: linkOpacity, fontSize: 28, color: '#60a5fa',
          fontFamily: 'Inter, system-ui, sans-serif', marginTop: 24,
        }}>github.com/doobidoo/mcp-memory-service</div>
        <div style={{
          opacity: linkOpacity, fontSize: 22, color: '#94a3b8',
          fontFamily: 'Inter, system-ui, sans-serif', marginTop: 16,
        }}>pip install mcp-memory-service</div>
      </div>
    </AbsoluteFill>
  );
};

// ─── Main Composition ──────────────────────────────────────────────────────

/**
 * Timeline layout:
 *
 * |-- Intro --|-- Scene1 --|-- Scene2 --| ... |-- Outro --|
 *             ↑ crossfade ↑
 *
 * Visual sequences overlap by CROSSFADE_FRAMES for smooth blending.
 * Audio sequences do NOT overlap — each audio starts where visual starts,
 * but the visual fade-in means the viewer sees a smooth blend.
 */
export const WalkthroughVideo: React.FC = () => {
  // Build timeline: each scene starts CROSSFADE_FRAMES before the previous ends
  const timeline: { from: number; duration: number; sceneIndex: number }[] = [];

  let cursor = 0;

  // Intro
  const introFrom = cursor;
  cursor += INTRO_FRAMES - CROSSFADE_FRAMES; // next scene overlaps visually

  // Main scenes
  for (let i = 0; i < SCENES.length; i++) {
    const dur = sceneDuration(SCENES[i].audioDuration);
    timeline.push({ from: cursor, duration: dur, sceneIndex: i });
    cursor += dur - CROSSFADE_FRAMES;
  }

  // Outro
  const outroFrom = cursor;
  const totalFrames = outroFrom + OUTRO_FRAMES;

  return (
    <>
      {/* Persistent dark background — always visible, prevents any black frames */}
      <AbsoluteFill>
        <DarkBackground />
      </AbsoluteFill>

      {/* Intro */}
      <Sequence from={introFrom} durationInFrames={INTRO_FRAMES}>
        <IntroScene />
      </Sequence>
      <Sequence from={introFrom} durationInFrames={INTRO_FRAMES - CROSSFADE_FRAMES}>
        <Audio src={staticFile(INTRO_AUDIO)} volume={1} />
      </Sequence>

      {/* Main scenes */}
      {timeline.map(({ from, duration, sceneIndex }) => {
        const scene = SCENES[sceneIndex];
        return (
          <React.Fragment key={scene.id}>
            {/* Visual: includes crossfade overlap */}
            <Sequence from={from} durationInFrames={duration}>
              {scene.comparisonItems ? (
                <ComparisonScene scene={scene} totalFrames={duration} />
              ) : scene.screenshot ? (
                <WalkthroughScene scene={scene} totalFrames={duration} />
              ) : (
                <FeatureScene scene={scene} totalFrames={duration} />
              )}
            </Sequence>
            {/* Audio: starts with visual but is strictly bounded to this scene */}
            {scene.audio && (
              <Sequence from={from} durationInFrames={duration - CROSSFADE_FRAMES}>
                <Audio src={staticFile(scene.audio)} volume={1} />
              </Sequence>
            )}
          </React.Fragment>
        );
      })}

      {/* Outro */}
      <Sequence from={outroFrom} durationInFrames={OUTRO_FRAMES}>
        <OutroScene />
      </Sequence>
      <Sequence from={outroFrom} durationInFrames={OUTRO_FRAMES}>
        <Audio src={staticFile(OUTRO_AUDIO)} volume={1} />
      </Sequence>
    </>
  );
};

/** Export total duration for Root.tsx registration */
export function getWalkthroughDuration(): number {
  let cursor = INTRO_FRAMES - CROSSFADE_FRAMES;
  for (const scene of SCENES) {
    cursor += sceneDuration(scene.audioDuration) - CROSSFADE_FRAMES;
  }
  return cursor + OUTRO_FRAMES;
}
