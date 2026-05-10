import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header.jsx'

/* ── Demo data ─────────────────────────────────────────── */
const DEMO_STORY = {
  title: 'The Last Frame',
  logline: 'A teenage gamer bets everything on his dream while his family fights to bring him back.',
  themes: ['Sacrifice','Family','Passion'],
  narrative_arc: 'Intro: Ethan abandons studies for gaming. Climax: His parents confront him after a failed tournament. Resolution: He finds balance between dreams and family.',
}
const DEMO_CHARS = [
  { name: 'Ethan Blackwood', role: 'Protagonist', voice_personality: 'young male, determined, slightly anxious', visual_description: 'Teenage boy, 17, slim build, messy dark hair, tired eyes, gaming hoodie' },
  { name: 'Mark Blackwood',  role: 'Supporting',  voice_personality: 'deep authoritative male, 40s, measured',  visual_description: 'Man, early 40s, neat beard, formal shirt, serious expression' },
  { name: 'Olivia Blackwood',role: 'Supporting',  voice_personality: 'warm caring female, late 30s, worried',   visual_description: 'Woman, late 30s, curly brown hair, green eyes, pastel sweater' },
]
const DEMO_SCENES = [
  { scene_id:'scene_1', setting:"Ethan's bedroom, late night",   tone:'tense',    duration_estimate_sec:12,
    dialogue_lines:[{character_name:'Ethan Blackwood',text:"I can't stop now — I'm so close to qualifying.",emotion:'determined'},{character_name:'Mark Blackwood',text:'Son, it is past midnight. Your exams are tomorrow.',emotion:'worried'}] },
  { scene_id:'scene_2', setting:'Family living room, dinner',    tone:'sad',      duration_estimate_sec:15,
    dialogue_lines:[{character_name:'Olivia Blackwood',text:'We just want what is best for you, Ethan.',emotion:'sad'},{character_name:'Ethan Blackwood',text:'Then let me show you what I am capable of.',emotion:'determined'}] },
  { scene_id:'scene_3', setting:'Deserted tournament hall',      tone:'dark',     duration_estimate_sec:11,
    dialogue_lines:[{character_name:'Ethan Blackwood',text:'I lost everything for this… and I still lost.',emotion:'sad'}] },
  { scene_id:'scene_4', setting:'Living room, early morning',    tone:'epic',     duration_estimate_sec:16,
    dialogue_lines:[{character_name:'Mark Blackwood',text:'We do not want you to give up your dream. We want to be part of it.',emotion:'determined'},{character_name:'Ethan Blackwood',text:'Dad…',emotion:'sad'}] },
  { scene_id:'scene_5', setting:"Ethan's room, sunset",          tone:'peaceful', duration_estimate_sec:10,
    dialogue_lines:[{character_name:'Ethan Blackwood',text:'I will find the balance. For all of us.',emotion:'happy'}] },
]

/* ── Lookups ─────────────────────────────────────────────── */
const ASSET_TABS = ['Characters','Script','Images','Audio']

const roleBadge = {
  Protagonist: 'bg-violet-600/20 text-violet-400 border-violet-500/30',
  Supporting:  'bg-blue-600/20 text-blue-400 border-blue-500/30',
  Antagonist:  'bg-red-600/20 text-red-400 border-red-500/30',
}
const toneColor = {
  tense:'text-red-400 bg-red-600/10',      sad:'text-blue-400 bg-blue-600/10',
  dark:'text-slate-400 bg-slate-600/10',   epic:'text-amber-400 bg-amber-600/10',
  peaceful:'text-emerald-400 bg-emerald-600/10', happy:'text-yellow-400 bg-yellow-600/10',
  mysterious:'text-purple-400 bg-purple-600/10', action:'text-orange-400 bg-orange-600/10',
  heroic:'text-amber-300 bg-amber-600/10', romantic:'text-pink-400 bg-pink-600/10',
}
const emotionIcon = {
  happy:'sentiment_very_satisfied', sad:'sentiment_very_dissatisfied',
  angry:'mood_bad', scared:'sentiment_dissatisfied', neutral:'sentiment_neutral',
  excited:'celebration', confused:'help', determined:'emoji_events', nervous:'psychology',
}

/* ── Data hook ───────────────────────────────────────────── */
function useRunData(runId, refreshKey) {
  const [data, setData]             = useState(null)
  const [images, setImages]         = useState([])
  const [audioLines, setAudioLines] = useState([])
  const [dbMessages, setDbMessages] = useState(null)   // null = not yet loaded
  const [loading, setLoading]       = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchAll = useCallback(() => {
    if (!runId || runId.startsWith('demo_')) { setLoading(false); return }
    if (refreshKey > 0) setRefreshing(true)

    // Fetch run data + messages in parallel
    Promise.all([
      fetch(`/api/runs/${runId}`).then(r => r.ok ? r.json() : null),
      fetch(`/api/runs/${runId}/messages`).then(r => r.ok ? r.json() : { messages: [] }),
    ]).then(([d, msgData]) => {
      if (d) {
        setData(d)
        fetch(`/api/runs/${runId}/images`)
          .then(r => r.ok ? r.json() : { images: [] })
          .then(r2 => setImages(r2.images || []))
          .catch(() => {})
        const s = d.status || ''
        const hasAudio = s === 'done' || s === 'phase2_done' || s === 'phase3_done'
        if (hasAudio) {
          fetch(`/api/runs/${runId}/audio`)
            .then(r => r.ok ? r.json() : { lines: [] })
            .then(r2 => setAudioLines(r2.lines || []))
            .catch(() => {})
        }
      }
      setDbMessages(msgData?.messages || [])
    })
    .catch(() => {})
    .finally(() => { setLoading(false); setRefreshing(false) })
  }, [runId, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchAll() }, [fetchAll])

  const story      = data?.story || DEMO_STORY
  const characters = (data?.characters?.characters || []).length > 0
                     ? data.characters.characters : DEMO_CHARS
  const scenes     = (data?.script?.scenes || []).length > 0
                     ? data.script.scenes : DEMO_SCENES
  const videoUrl   = data?.video_url || null
  const apiVersions = (data?.versions || []).map((v, i) => ({
    v:        v.version,
    label:    v.label,
    time:     v.saved_at?.slice(11,16) || '',
    current:  i === 0,
    videoUrl: v.video_url || null,
  }))

  return { story, characters, scenes, videoUrl, images, audioLines, apiVersions, dbMessages, loading, refreshing }
}

/* ── Page ───────────────────────────────────────────────── */
export default function StudioPage() {
  const { runId }  = useParams()
  const navigate   = useNavigate()

  const [refreshKey, setRefreshKey] = useState(0)
  const { story, characters, scenes, videoUrl, images, audioLines, apiVersions, dbMessages, loading, refreshing }
    = useRunData(runId, refreshKey)

  const [sideView, setSideView]   = useState('assets')
  const [assetTab, setAssetTab]   = useState('Characters')
  const [playing, setPlaying]     = useState(false)
  const [progress, setProgress]   = useState(0)
  const [chatInput, setChatInput] = useState('')
  const [optimisticMsgs, setOptimisticMsgs] = useState([])
  const [versions, setVersions]   = useState([])
  const [sending, setSending]     = useState(false)
  const [expandedScene, setExpandedScene] = useState(null)
  const [lightboxImg, setLightboxImg]     = useState(null)
  const [comparison, setComparison]       = useState(null)

  // Edit-time progress received over WebSocket
  const [editActive, setEditActive]   = useState(false)
  const [editPhaseNum, setEditPhaseNum] = useState(5)
  const [editPct, setEditPct]         = useState(0)
  const [editMsg, setEditMsg]         = useState('')

  // Version browsing: null = viewing current live state, number = viewing a snapshot
  const [viewingVersion, setViewingVersion]   = useState(null)
  const [versionAssets, setVersionAssets]     = useState(null)   // fetched snapshot data
  const [versionLoading, setVersionLoading]   = useState(false)

  const chatEndRef = useRef(null)
  const videoRef   = useRef(null)

  const messages = dbMessages === null
    ? optimisticMsgs
    : [...dbMessages, ...optimisticMsgs]

  useEffect(() => {
    if (apiVersions.length > 0) setVersions(apiVersions)
  }, [JSON.stringify(apiVersions)]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (dbMessages && dbMessages.length > 0 && optimisticMsgs.length > 0) {
      setOptimisticMsgs([])
    }
  }, [dbMessages?.length]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages.length])

  // Fetch snapshot assets whenever user browses to a version
  useEffect(() => {
    if (viewingVersion === null) { setVersionAssets(null); return }
    setVersionLoading(true)
    fetch(`/api/runs/${runId}/versions/${viewingVersion}/assets`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setVersionAssets(d))
      .catch(() => setVersionAssets(null))
      .finally(() => setVersionLoading(false))
  }, [viewingVersion, runId])

  // Determine what to actually display — live data or snapshot
  const displayImages     = viewingVersion ? (versionAssets?.images || [])                : images
  const displayCharacters = viewingVersion ? (versionAssets?.characters?.characters || []) : characters
  const displayScenes     = viewingVersion ? (versionAssets?.script?.scenes || [])         : scenes
  // Cache-bust the live video URL so the browser re-fetches from disk after every edit/refresh.
  // Version snapshot URLs are content-addressable (different path each time) so they don't need it.
  const displayVideoUrl   = viewingVersion
    ? (versionAssets?.video_url || null)
    : (videoUrl ? `${videoUrl}?v=${refreshKey}` : null)

  // WebSocket — listen for Phase 5 (and sub-phase) progress during edits
  useEffect(() => {
    if (!runId) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url   = `${proto}://${window.location.host}/ws/${runId}`
    let ws
    try { ws = new WebSocket(url) } catch { return }

    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (!d.phase) return
        const phase = d.phase
        const pct   = d.progress ?? 0
        const msg   = d.message  ?? ''
        const isDone = d.status === 'done' || d.status === 'error'

        if (isDone && phase === 5) {
          // Edit complete — show 100% briefly then dismiss
          setEditPct(100)
          setEditMsg(d.status === 'error' ? '✗ ' + msg : '✓ Edit applied')
          setTimeout(() => { setEditActive(false); setRefreshKey(k => k + 1) }, 1500)
        } else if (!isDone) {
          // Any running progress event (Phase 5 start, Phase 2/3 sub-steps) — always activate bar
          // Note: no stale-closure check on editActive here; bar activates on ANY live event
          setEditActive(true)
          setEditPhaseNum(phase)
          setEditPct(pct)
          setEditMsg(msg)
        }
      } catch { /* ignore malformed */ }
    }
    ws.onerror = (err) => { console.warn('[StudioWS] error', err) }
    return () => { try { ws.close() } catch { /* ignore */ } }
  }, [runId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!playing || videoUrl) return
    const t = setInterval(() => setProgress(p => {
      if (p >= 100) { setPlaying(false); return 100 }
      return p + 0.3
    }), 100)
    return () => clearInterval(t)
  }, [playing, videoUrl])

  // Image URL with cache-buster so browser reloads after edits (skipped for version snapshots which have stable paths)
  const imgSrc = (url) => url
    ? (viewingVersion ? url : `${url}?v=${refreshKey}`)
    : url

  // Group display images by scene_id
  const imagesByScene = displayImages.reduce((acc, img) => {
    ;(acc[img.scene_id] = acc[img.scene_id] || []).push(img)
    return acc
  }, {})

  // Group audio lines by character name
  const audioByChar = audioLines.reduce((acc, f) => {
    const key = f.character_name || 'Unknown'
    ;(acc[key] = acc[key] || []).push(f)
    return acc
  }, {})

  /* ── Revert ──────────────────────────────────────────── */
  async function revertVersion(vNum) {
    const targetVer  = versions.find(v => v.v === vNum)
    const currentVer = versions.find(v => v.current)
    const beforeUrl  = videoUrl || currentVer?.videoUrl || null
    try {
      const res = await fetch(`/api/runs/${runId}/revert/${vNum}`, { method: 'POST' })
      if (res.ok) {
        const d = await res.json()
        const afterUrl = d.version_video_url || d.current_video_url || null
        if (beforeUrl || afterUrl) {
          setComparison({
            beforeUrl,
            afterUrl,
            beforeLabel: `Before (v${currentVer?.v ?? '?'})`,
            afterLabel:  `After (v${vNum})`,
          })
        }
        // Optimistically prune pills newer than the restored version immediately
        // so the UI reflects the change before the re-fetch completes
        setVersions(prev =>
          prev
            .filter(v => v.v <= vNum)
            .map((v, i) => ({ ...v, current: i === 0 }))
        )
        setViewingVersion(null)
        setRefreshKey(k => k + 1)  // re-fetch to confirm server state
      }
    } catch {
      setOptimisticMsgs(prev => [...prev, {
        role: 'ai', text: `Revert to v${vNum} failed.`, ts: new Date().toISOString(),
      }])
    }
  }

  /* ── Send edit ───────────────────────────────────────── */
  async function sendEdit() {
    if (!chatInput.trim()) return
    const userMsg = chatInput.trim()
    setChatInput('')
    setSending(true)
    // Optimistic user bubble (backend persists it but hasn't responded yet)
    setOptimisticMsgs(prev => [...prev, { role: 'user', text: userMsg, ts: new Date().toISOString() }])
    try {
      const editBody = { instruction: userMsg }
      if (viewingVersion !== null) editBody.base_version = viewingVersion
      const res = await fetch(`/api/runs/${runId}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editBody),
      })
      const d    = res.ok ? await res.json() : null
      const intent = d?.intent?.type || 'edit'
      const vNum   = d?.version_saved || (versions[0]?.v ?? 0) + 1
      const branchNote = viewingVersion !== null ? ` (branched from v${viewingVersion})` : ''
      // Optimistic AI "processing" bubble — replaced once BG task completes and we refresh
      setOptimisticMsgs(prev => [
        ...prev,
        { role: 'ai', text: `Intent: **${intent}** → processing edit${branchNote}. Saved as v${vNum}.`, ts: new Date().toISOString() },
      ])
      setVersions(prev => [
        { v: vNum, label: userMsg.slice(0,35), time: 'Just now', current: true, videoUrl: null },
        ...prev.map(v => ({ ...v, current: false })),
      ])
      setComparison(null)
      setViewingVersion(null)   // return to live view when a new edit starts
      setRefreshKey(k => k + 1)
    } catch {
      setOptimisticMsgs(prev => [
        ...prev,
        { role: 'ai', text: `Could not reach server for "${userMsg}".`, ts: new Date().toISOString() },
      ])
    }
    setSending(false)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="h-screen bg-background flex flex-col overflow-hidden"
    >
      <Header />

      {/* Image lightbox */}
      <AnimatePresence>
        {lightboxImg && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setLightboxImg(null)}
            className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-6 cursor-zoom-out"
          >
            <motion.img
              initial={{ scale: 0.85 }} animate={{ scale: 1 }} exit={{ scale: 0.85 }}
              src={lightboxImg}
              className="max-w-full max-h-full rounded-2xl shadow-2xl object-contain"
              onClick={e => e.stopPropagation()}
            />
            <button onClick={() => setLightboxImg(null)}
              className="absolute top-6 right-6 w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20">
              <span className="material-symbols-outlined text-white">close</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-1 overflow-hidden mt-16">

        {/* ── LEFT SIDEBAR ─────────────────────────────────── */}
        <aside className="w-16 md:w-64 flex-shrink-0 bg-background border-r border-border flex flex-col">
          <div className="p-4 hidden md:block">
            <p className="font-display text-[10px] uppercase tracking-widest text-slate-600 mb-4">Studio</p>
            {[
              { icon:'view_timeline', label:'Timeline', key:'timeline' },
              { icon:'folder_open',   label:'Assets',   key:'assets'   },
              { icon:'history',       label:'History',  key:'history'  },
            ].map(item => (
              <button
                key={item.label}
                onClick={() => {
                  if (item.key === 'history') { navigate('/gallery'); return }
                  setSideView(item.key)
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-all font-display text-sm font-medium
                  ${sideView === item.key && item.key !== 'history'
                    ? 'bg-violet-600/15 text-white border-l-2 border-violet-500'
                    : 'text-slate-500 hover:bg-surface hover:text-white'}`}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>

          {/* Mobile icon-only nav */}
          <div className="md:hidden flex flex-col items-center gap-1 pt-4">
            {[
              { icon:'view_timeline', key:'timeline' },
              { icon:'folder_open',   key:'assets'   },
              { icon:'history',       key:'history'  },
            ].map(item => (
              <button key={item.key}
                onClick={() => { if (item.key === 'history') { navigate('/gallery'); return } setSideView(item.key) }}
                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all
                  ${sideView === item.key ? 'bg-violet-600/20 text-violet-400' : 'text-slate-600 hover:text-white'}`}>
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              </button>
            ))}
          </div>

          <div className="mt-auto p-4 border-t border-border hidden md:block">
            <p className="font-display text-[10px] uppercase tracking-widest text-slate-600 mb-2">Version</p>
            <p className="text-white font-display font-bold text-sm">v{versions[0]?.v ?? '—'} · Current</p>
            <p className="text-slate-500 text-xs mb-3">{versions[0]?.time ?? ''}</p>
            <motion.button
              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/create')}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600
                         text-white font-display font-bold text-xs flex items-center justify-center gap-2
                         shadow-[0_0_15px_rgba(124,58,237,0.3)]"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
              New Film
            </motion.button>
          </div>
        </aside>

        {/* ── MAIN ─────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">

            {/* ── BEFORE / AFTER COMPARISON ── */}
            <AnimatePresence>
              {comparison && (
                <motion.section
                  key="comparison"
                  initial={{ opacity: 0, y: -12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.3 }}
                  className="max-w-5xl mx-auto"
                >
                  <div className="glass rounded-2xl p-4 border border-violet-500/30">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-violet-400 text-[18px]">compare</span>
                        <p className="text-white font-display font-bold text-sm">Version Comparison</p>
                      </div>
                      <button
                        onClick={() => setComparison(null)}
                        className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors"
                      >
                        <span className="material-symbols-outlined text-slate-400 text-[16px]">close</span>
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {[
                        { url: comparison.beforeUrl, label: comparison.beforeLabel, accent: 'border-slate-500/40 text-slate-400' },
                        { url: comparison.afterUrl,  label: comparison.afterLabel,  accent: 'border-violet-500/60 text-violet-400' },
                      ].map(({ url, label, accent }) => (
                        <div key={label} className={`rounded-xl overflow-hidden border ${accent.split(' ')[0]}`}>
                          <div className={`px-3 py-1.5 text-[11px] font-display font-bold uppercase tracking-wider ${accent.split(' ')[1]}`}>
                            {label}
                          </div>
                          {url ? (
                            <video
                              src={url}
                              controls
                              className="w-full aspect-video object-contain bg-black"
                            />
                          ) : (
                            <div className="aspect-video bg-black/50 flex items-center justify-center">
                              <p className="text-slate-600 text-xs font-display">No video recorded for this version</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.section>
              )}
            </AnimatePresence>

            {/* ── VIDEO PLAYER ── */}
            <section className="max-w-5xl mx-auto">
              <motion.div
                initial={{ opacity:0, scale:0.98 }}
                animate={{ opacity:1, scale:1 }}
                transition={{ duration:0.5 }}
                className="relative group aspect-video rounded-2xl overflow-hidden bg-black border border-border shadow-2xl"
              >
                {/* Refreshing overlay */}
                <AnimatePresence>
                  {refreshing && (
                    <motion.div
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      className="absolute inset-0 z-20 bg-black/60 flex flex-col items-center justify-center gap-3"
                    >
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                        className="w-10 h-10 rounded-full border-2 border-violet-500 border-t-transparent"
                      />
                      <p className="text-violet-300 font-display text-sm font-bold">Refreshing assets…</p>
                    </motion.div>
                  )}
                </AnimatePresence>

                {displayVideoUrl ? (
                  <video
                    key={displayVideoUrl}
                    ref={videoRef}
                    src={displayVideoUrl}
                    controls
                    className="w-full h-full object-contain bg-black"
                    onPlay={() => setPlaying(true)}
                    onPause={() => setPlaying(false)}
                    onTimeUpdate={() => {
                      const v = videoRef.current
                      if (v && v.duration) setProgress((v.currentTime / v.duration) * 100)
                    }}
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-violet-900/30 via-background to-blue-900/20
                                  flex items-center justify-center relative">
                    <div className="absolute top-6 left-6 z-20">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full border-2 border-violet-500 bg-violet-600/30 flex items-center justify-center">
                          <span className="font-display text-xs font-bold text-violet-300">{story.title?.[0] || 'S'}</span>
                        </div>
                        <div>
                          <p className="font-display text-[10px] uppercase tracking-widest text-violet-400">Film</p>
                          <p className="text-white text-sm font-bold">{story.title}</p>
                        </div>
                      </div>
                    </div>
                    <motion.button
                      onClick={() => setPlaying(p => !p)}
                      className="relative z-20 w-16 h-16 rounded-full border border-violet-500/50
                                 bg-violet-600/20 backdrop-blur-md flex items-center justify-center
                                 hover:bg-violet-600/40 transition-colors"
                      whileHover={{ scale:1.1 }} whileTap={{ scale:0.9 }}
                    >
                      <span className="material-symbols-outlined text-white text-4xl icon-fill">
                        {playing ? 'pause' : 'play_arrow'}
                      </span>
                    </motion.button>
                    <div className="absolute bottom-16 inset-x-0 text-center">
                      <p className="text-slate-500 text-xs font-display">Video not yet generated</p>
                    </div>
                  </div>
                )}

                {!displayVideoUrl && (
                  <div className="absolute inset-x-0 bottom-0 p-5 bg-gradient-to-t from-black/90 to-transparent
                                  opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <div className="relative h-1.5 w-full bg-white/10 rounded-full cursor-pointer mb-4"
                      onClick={e => {
                        const rect = e.currentTarget.getBoundingClientRect()
                        setProgress(((e.clientX - rect.left) / rect.width) * 100)
                      }}>
                      <motion.div className="absolute h-full bg-violet-500 rounded-full" style={{ width:`${progress}%` }} />
                      <motion.div className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full border-2 border-violet-500"
                        style={{ left:`calc(${progress}% - 8px)` }} />
                    </div>
                    <div className="flex items-center gap-5">
                      <button onClick={() => setPlaying(p => !p)}>
                        <span className="material-symbols-outlined text-white text-[24px] hover:text-violet-400 transition-colors icon-fill">
                          {playing ? 'pause' : 'play_arrow'}
                        </span>
                      </button>
                      <span className="material-symbols-outlined text-white text-[24px] cursor-pointer hover:text-violet-400 transition-colors">volume_up</span>
                    </div>
                  </div>
                )}
              </motion.div>

              {/* Action bar */}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex gap-3">
                  <motion.a
                    href={`/api/runs/${runId}/video`}
                    whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600
                               text-white font-display font-bold text-xs flex items-center gap-2
                               shadow-[0_0_15px_rgba(124,58,237,0.3)]"
                  >
                    <span className="material-symbols-outlined text-[18px]">download</span>
                    Download MP4
                  </motion.a>
                  <motion.button
                    whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
                    onClick={() => setRefreshKey(k => k + 1)}
                    className="px-5 py-2.5 rounded-xl border border-border text-slate-300
                               font-display font-bold text-xs flex items-center gap-2
                               hover:border-violet-500/50 hover:text-white transition-colors"
                  >
                    <span className={`material-symbols-outlined text-[18px] ${refreshing ? 'animate-spin' : ''}`}>refresh</span>
                    Refresh
                  </motion.button>
                </div>
                <div className="font-display text-[10px] text-slate-500 uppercase tracking-widest">
                  Run: {runId}
                </div>
              </div>
            </section>

            {/* ── ASSETS PANEL ── */}
            <AnimatePresence>
              {sideView === 'assets' && (
                <motion.section
                  key="assets"
                  initial={{ opacity:0, y:10 }}
                  animate={{ opacity:1, y:0 }}
                  exit={{ opacity:0, y:10 }}
                  transition={{ duration:0.25 }}
                  className="max-w-5xl mx-auto"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex border-b border-border overflow-x-auto no-scrollbar flex-1">
                      {ASSET_TABS.map(t => (
                        <button key={t}
                          onClick={() => setAssetTab(t)}
                          className={`relative px-6 py-3 font-display font-bold text-xs tracking-widest whitespace-nowrap transition-colors
                            ${assetTab === t ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}>
                          {t}
                          {t === 'Images' && displayImages.length > 0 && (
                            <span className="ml-1.5 text-[9px] bg-violet-600/30 text-violet-400 px-1.5 py-0.5 rounded-full font-bold">
                              {displayImages.length}
                            </span>
                          )}
                          {t === 'Audio' && audioLines.length > 0 && (
                            <span className="ml-1.5 text-[9px] bg-blue-600/30 text-blue-400 px-1.5 py-0.5 rounded-full font-bold">
                              {audioLines.length}
                            </span>
                          )}
                          {assetTab === t && (
                            <motion.div layoutId="asset-tab-indicator"
                              className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-violet-500 to-blue-500 rounded-full" />
                          )}
                        </button>
                      ))}
                    </div>
                    {(refreshing || versionLoading) && (
                      <div className={`ml-3 flex items-center gap-1.5 text-[11px] font-display
                        ${versionLoading ? 'text-amber-400' : 'text-violet-400'}`}>
                        <motion.span
                          className="material-symbols-outlined text-[14px]"
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 0.8, ease: 'linear' }}
                        >refresh</motion.span>
                        {versionLoading ? `v${viewingVersion}` : 'updating'}
                      </div>
                    )}
                  </div>

                  <AnimatePresence mode="wait">

                    {/* CHARACTERS */}
                    {assetTab === 'Characters' && (
                      <motion.div key="chars"
                        initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
                        transition={{ duration:0.2 }}
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6"
                      >
                        {displayCharacters.map((c, i) => (
                          <motion.div key={c.name}
                            initial={{ opacity:0, scale:0.95 }} animate={{ opacity:1, scale:1 }}
                            transition={{ delay: i * 0.08 }} whileHover={{ y:-4 }}
                            className="glass rounded-2xl p-5 flex flex-col gap-3 cursor-default"
                          >
                            <div className="w-full aspect-[4/3] rounded-xl bg-gradient-to-br from-violet-900/40 to-blue-900/40 border border-border flex items-center justify-center">
                              <span className="font-display font-black text-5xl text-gradient">{c.name[0]}</span>
                            </div>
                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <h3 className="text-white font-display font-semibold">{c.name}</h3>
                                <span className={`text-[10px] px-2 py-0.5 rounded border font-display font-bold ${roleBadge[c.role] ?? 'bg-slate-600/20 text-slate-400 border-slate-500/30'}`}>
                                  {c.role}
                                </span>
                              </div>
                              <p className="text-slate-500 text-xs italic leading-relaxed">"{c.voice_personality}"</p>
                              {c.visual_description && (
                                <p className="text-slate-600 text-[11px] mt-2 leading-relaxed">{c.visual_description}</p>
                              )}
                            </div>
                          </motion.div>
                        ))}
                      </motion.div>
                    )}

                    {/* SCRIPT */}
                    {assetTab === 'Script' && (
                      <motion.div key="script"
                        initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
                        transition={{ duration:0.2 }}
                        className="space-y-3 mt-6"
                      >
                        {displayScenes.map((scene, i) => {
                          const isOpen = expandedScene === scene.scene_id
                          return (
                            <motion.div key={scene.scene_id}
                              initial={{ opacity:0, x:-20 }} animate={{ opacity:1, x:0 }}
                              transition={{ delay: i * 0.05 }}
                              className="glass rounded-xl overflow-hidden"
                            >
                              <button
                                onClick={() => setExpandedScene(isOpen ? null : scene.scene_id)}
                                className="w-full flex items-center gap-4 p-4 text-left hover:bg-white/[0.02] transition-colors"
                              >
                                <div className="w-9 h-9 rounded-xl bg-violet-600/15 border border-violet-600/30 flex items-center justify-center flex-shrink-0">
                                  <span className="font-display font-black text-violet-400 text-sm">{i+1}</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-white font-display font-semibold text-sm truncate">{scene.setting}</p>
                                  <div className="flex items-center gap-3 mt-1">
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-display font-bold ${toneColor[scene.tone] ?? 'text-slate-400 bg-slate-600/10'}`}>
                                      {scene.tone}
                                    </span>
                                    <span className="font-display text-[10px] text-slate-500">~{scene.duration_estimate_sec}s</span>
                                    {scene.dialogue_lines?.length > 0 && (
                                      <span className="font-display text-[10px] text-slate-600">
                                        {scene.dialogue_lines.length} line{scene.dialogue_lines.length !== 1 ? 's' : ''}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <span className={`material-symbols-outlined text-slate-500 text-[20px] transition-transform ${isOpen ? 'rotate-180' : ''}`}>expand_more</span>
                              </button>
                              <AnimatePresence>
                                {isOpen && scene.dialogue_lines?.length > 0 && (
                                  <motion.div
                                    initial={{ height:0, opacity:0 }} animate={{ height:'auto', opacity:1 }}
                                    exit={{ height:0, opacity:0 }} transition={{ duration:0.25 }}
                                    className="overflow-hidden"
                                  >
                                    <div className="px-4 pb-4 space-y-2 border-t border-border/50 pt-3">
                                      {scene.dialogue_lines.map((line, li) => (
                                        <div key={li} className="flex gap-3 items-start">
                                          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-700 to-blue-700
                                                          flex items-center justify-center text-white font-display font-bold text-[11px] flex-shrink-0 mt-0.5">
                                            {line.character_name?.[0] || '?'}
                                          </div>
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5">
                                              <span className="text-violet-300 font-display font-bold text-[11px]">{line.character_name}</span>
                                              {line.emotion && (
                                                <span className="flex items-center gap-1 text-[10px] text-slate-500">
                                                  <span className="material-symbols-outlined text-[12px]">{emotionIcon[line.emotion] || 'sentiment_neutral'}</span>
                                                  {line.emotion}
                                                </span>
                                              )}
                                            </div>
                                            <p className="text-slate-300 text-sm leading-relaxed">"{line.text}"</p>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </motion.div>
                          )
                        })}
                      </motion.div>
                    )}

                    {/* IMAGES — cache-busted URLs so edits are visible immediately */}
                    {assetTab === 'Images' && (
                      <motion.div key="images"
                        initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
                        transition={{ duration:0.2 }}
                        className="mt-6"
                      >
                        {displayImages.length === 0 ? (
                          <div className="text-center py-16">
                            <span className="material-symbols-outlined text-6xl text-slate-700 block mb-3">image_not_supported</span>
                            <p className="text-slate-500 font-display font-semibold">No images generated yet</p>
                            <p className="text-slate-600 text-xs mt-1">Images appear here after Phase 3 completes</p>
                          </div>
                        ) : (
                          <div className="space-y-6">
                            {displayScenes.map((scene, si) => {
                              const sceneImgs = imagesByScene[scene.scene_id] || []
                              if (sceneImgs.length === 0) return null
                              return (
                                <div key={scene.scene_id}>
                                  <div className="flex items-center gap-3 mb-3">
                                    <div className="w-7 h-7 rounded-lg bg-violet-600/15 border border-violet-600/30 flex items-center justify-center flex-shrink-0">
                                      <span className="font-display font-black text-violet-400 text-[11px]">{si+1}</span>
                                    </div>
                                    <div>
                                      <p className="text-white font-display font-semibold text-sm">{scene.setting}</p>
                                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-display font-bold ${toneColor[scene.tone] ?? 'text-slate-400 bg-slate-600/10'}`}>{scene.tone}</span>
                                    </div>
                                  </div>
                                  <div className="grid grid-cols-3 gap-3">
                                    {['wide','mid','close'].map(ft => {
                                      const img = sceneImgs.find(x => x.frame_type === ft)
                                      return (
                                        <div key={ft}>
                                          {img ? (
                                            <motion.div whileHover={{ scale:1.02, y:-2 }}
                                              onClick={() => setLightboxImg(imgSrc(img.url))}
                                              className="relative aspect-video rounded-xl overflow-hidden border border-border cursor-zoom-in group">
                                              <img
                                                src={imgSrc(img.url)}
                                                alt={`${scene.scene_id} ${ft}`}
                                                className="w-full h-full object-cover group-hover:brightness-110 transition-all"
                                                loading="lazy"
                                              />
                                              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/70 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <span className="text-white font-display text-[10px] font-bold uppercase tracking-widest">{ft}</span>
                                              </div>
                                            </motion.div>
                                          ) : (
                                            <div className="aspect-video rounded-xl bg-surface border border-border border-dashed flex items-center justify-center">
                                              <span className="text-slate-700 font-display text-[10px] uppercase">{ft}</span>
                                            </div>
                                          )}
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </motion.div>
                    )}

                    {/* AUDIO */}
                    {assetTab === 'Audio' && (
                      <motion.div key="audio"
                        initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
                        transition={{ duration:0.2 }}
                        className="space-y-4 mt-6"
                      >
                        {Object.keys(audioByChar).length === 0 ? (
                          <div className="text-center py-16">
                            <span className="material-symbols-outlined text-6xl text-slate-700 block mb-3">mic_off</span>
                            <p className="text-slate-500 font-display font-semibold">No audio generated yet</p>
                            <p className="text-slate-600 text-xs mt-1">Audio appears here after Phase 2 completes</p>
                          </div>
                        ) : (
                          Object.entries(audioByChar).map(([charName, lines]) => (
                            <div key={charName} className="glass rounded-xl p-5">
                              <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center font-display font-bold text-sm flex-shrink-0">
                                  {charName[0]}
                                </div>
                                <div>
                                  <p className="text-white font-display font-semibold">{charName}</p>
                                  <p className="text-slate-500 text-xs">{lines.length} audio line{lines.length !== 1 ? 's' : ''}</p>
                                </div>
                              </div>
                              <div className="space-y-2">
                                {lines.map(line => (
                                  <div key={line.filename} className="flex items-center gap-3 bg-background/50 rounded-lg px-3 py-2">
                                    <div className="flex-shrink-0">
                                      <span className="text-[10px] text-slate-500 font-display font-bold uppercase">
                                        {line.scene_id?.replace('scene_','')} · {line.emotion}
                                      </span>
                                    </div>
                                    <audio
                                      controls
                                      src={line.url}
                                      className="flex-1 min-w-0"
                                      style={{ height: '32px', colorScheme: 'dark' }}
                                    />
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))
                        )}
                      </motion.div>
                    )}

                  </AnimatePresence>
                </motion.section>
              )}
            </AnimatePresence>

          </div>

          {/* ── AI EDIT PANEL ── */}
          <div className="border-t border-border bg-surface flex flex-col" style={{ height:'260px' }}>
            {/* Version switcher row */}
            <div className="border-b border-border">
              {/* Snapshot banner — shown when browsing a past version */}
              <AnimatePresence>
                {viewingVersion !== null && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="flex items-center gap-3 px-4 py-2 bg-amber-500/10 border-b border-amber-500/20">
                      <span className="material-symbols-outlined text-amber-400 text-[16px]">history</span>
                      <p className="text-amber-300 font-display font-bold text-[11px] flex-1">
                        Browsing v{viewingVersion}{versionLoading ? ' — loading…' : ''}.
                        Type an edit below to branch from this version.
                      </p>
                      <motion.button
                        whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
                        onClick={() => revertVersion(viewingVersion)}
                        className="px-3 py-1 rounded-lg bg-amber-500/20 border border-amber-500/40
                                   text-amber-300 font-display font-bold text-[10px] hover:bg-amber-500/30 transition-colors"
                      >
                        Restore this version
                      </motion.button>
                      <button
                        onClick={() => setViewingVersion(null)}
                        className="w-6 h-6 rounded-md hover:bg-white/10 flex items-center justify-center transition-colors"
                      >
                        <span className="material-symbols-outlined text-slate-400 text-[14px]">close</span>
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Version pills — click to browse, hold undo button to revert */}
              <div className="px-4 py-2 flex gap-2 overflow-x-auto no-scrollbar">
                {versions.length === 0 && (
                  <p className="text-slate-600 font-display text-[11px] py-1">No versions saved yet.</p>
                )}
                <AnimatePresence>
                  {versions.map(ver => {
                    const isViewing = viewingVersion === ver.v
                    const isCurrent = ver.current && viewingVersion === null
                    return (
                      <motion.div key={ver.v}
                        initial={{ opacity:0, scale:0.8 }} animate={{ opacity:1, scale:1 }}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs whitespace-nowrap flex-shrink-0
                          cursor-pointer select-none transition-all
                          ${isCurrent
                            ? 'border border-violet-500 bg-violet-600/10 text-violet-300'
                            : isViewing
                              ? 'border border-amber-500 bg-amber-500/10 text-amber-300'
                              : 'border border-border text-slate-400 hover:border-slate-500 hover:text-slate-200'}`}
                        onClick={() => setViewingVersion(ver.current && !isViewing ? null : isViewing ? null : ver.v)}
                        title={isViewing ? 'Click to return to current' : `Click to preview v${ver.v}`}
                      >
                        <span className="font-display font-bold">v{ver.v}</span>
                        <span className="max-w-[90px] truncate opacity-70">{ver.label}</span>
                        <span className="text-[10px] opacity-50">{ver.time}</span>
                        {isCurrent && (
                          <span className="text-[9px] font-display font-bold text-violet-400 uppercase tracking-wider">
                            live
                          </span>
                        )}
                        {isViewing && (
                          <span className="text-[9px] font-display font-bold text-amber-400 uppercase tracking-wider">
                            viewing
                          </span>
                        )}
                        {/* Revert button — only on non-current, non-viewing pills */}
                        {!ver.current && !isViewing && (
                          <motion.button
                            whileHover={{ scale: 1.15 }} whileTap={{ scale: 0.9 }}
                            onClick={e => { e.stopPropagation(); revertVersion(ver.v) }}
                            title={`Restore v${ver.v} as current`}
                            className="ml-1 flex items-center justify-center w-5 h-5 rounded-full
                                       bg-slate-700/60 text-slate-300 hover:bg-violet-600/40
                                       hover:text-violet-300 transition-colors"
                          >
                            <span className="material-symbols-outlined text-[12px]">undo</span>
                          </motion.button>
                        )}
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
              </div>
            </div>

            {/* Chat */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {/* Empty state */}
              {messages.length === 0 && !sending && dbMessages !== null && (
                <div className="h-full flex flex-col items-center justify-center gap-2 py-4">
                  <span className="material-symbols-outlined text-4xl text-slate-700">chat</span>
                  <p className="text-slate-600 font-display text-xs text-center">
                    No edits yet. Describe a change below to get started.
                  </p>
                </div>
              )}
              <AnimatePresence>
                {messages.map((msg, i) => (
                  <motion.div key={i}
                    initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}
                    className={`flex items-start gap-3 ${msg.role === 'user' ? '' : 'justify-end'}`}
                  >
                    {msg.role === 'user' && (
                      <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">U</div>
                    )}
                    <div className="flex flex-col gap-0.5 max-w-sm">
                      <div className={`px-4 py-2 rounded-2xl text-sm
                        ${msg.role === 'user'
                          ? 'bg-border text-white rounded-tl-none'
                          : `bg-violet-600/20 border rounded-tr-none text-violet-100
                             ${msg.error ? 'border-red-500/40 bg-red-600/10 text-red-300' : 'border-violet-500/30'}`}`}>
                        {msg.text}
                      </div>
                      {msg.ts && (
                        <span className={`text-[10px] text-slate-600 ${msg.role === 'ai' ? 'text-right' : ''}`}>
                          {msg.ts.slice(11,16)} UTC
                        </span>
                      )}
                    </div>
                    {msg.role === 'ai' && (
                      <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">AI</div>
                    )}
                  </motion.div>
                ))}
                {sending && (
                  <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} className="flex justify-end items-start gap-3">
                    <div className="px-4 py-2 rounded-2xl bg-violet-600/20 border border-violet-500/30 flex gap-1.5">
                      {[0,1,2].map(i => (
                        <motion.div key={i} className="w-1.5 h-1.5 rounded-full bg-violet-400"
                          animate={{ y:[-3,0,-3] }} transition={{ duration:0.6, repeat:Infinity, delay:i*0.15 }} />
                      ))}
                    </div>
                    <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-[10px] font-bold flex-shrink-0">AI</div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={chatEndRef} />
            </div>

            {/* Phase 5 edit progress bar */}
            <AnimatePresence>
              {editActive && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="px-4 pt-3 pb-1"
                >
                  <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 px-3 py-2">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-display font-bold text-violet-400 uppercase tracking-widest">
                        Phase {editPhaseNum} — Applying edit
                      </span>
                      <span className="text-[10px] font-mono text-violet-300">{editPct}%</span>
                    </div>
                    <div className="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-violet-500 to-blue-500 rounded-full"
                        animate={{ width: `${editPct}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                    {editMsg && (
                      <p className="mt-1 text-[10px] text-slate-400 truncate font-body">{editMsg}</p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Input */}
            <div className="px-4 py-3 flex gap-3 items-center border-t border-border">
              <div className="flex-1 relative">
                <input
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendEdit()}
                  placeholder="Describe what you want to change… e.g. 'Make scene 3 darker'"
                  className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-white
                             placeholder-slate-600 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/40
                             outline-none transition-all font-body"
                />
              </div>
              <motion.button
                whileHover={{ scale:1.05 }} whileTap={{ scale:0.95 }}
                onClick={sendEdit}
                disabled={sending || !chatInput.trim()}
                className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-600 to-blue-600
                           flex items-center justify-center text-white
                           shadow-[0_0_15px_rgba(124,58,237,0.4)]
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span className="material-symbols-outlined text-[20px]">send</span>
              </motion.button>
            </div>
          </div>
        </main>
      </div>
    </motion.div>
  )
}
