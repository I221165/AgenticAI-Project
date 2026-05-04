import { useState, useEffect, useRef, lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header.jsx'

// Three.js is large — lazy-load so it only ships with the Progress page chunk
const DottedSurface = lazy(() =>
  import('../components/ui/DottedSurface.jsx').then(m => ({ default: m.DottedSurface }))
)

/* ── Phase definitions ──────────────────────────────────── */
const PHASES = [
  {
    id: 1, key: 'phase1',
    label: 'Story & Script',
    sub:   'Generating narrative, characters, and scene-by-scene script',
    icon:  'edit_note',
    color: 'violet',
    steps: ['Generating story arc…','Creating character roster…','Writing scene dialogue…','Building visual prompts…'],
  },
  {
    id: 2, key: 'phase2',
    label: 'Audio Generation',
    sub:   'Synthesizing character voices, selecting BGM, building timing manifest',
    icon:  'record_voice_over',
    color: 'blue',
    steps: ['Assigning character voices…','Generating TTS audio…','Selecting background music…','Mixing scene audio…'],
  },
  {
    id: 3, key: 'phase3',
    label: 'Video Composition',
    sub:   'Generating images, animating with Ken Burns, compositing final MP4',
    icon:  'movie_filter',
    color: 'emerald',
    steps: ['Generating scene images…','Animating frames (Ken Burns)…','Compositing transitions…','Syncing audio to video…'],
  },
  {
    id: 4, key: 'phase4',
    label: 'Finalizing',
    sub:   'Burning subtitles, exporting final MP4, saving state snapshot',
    icon:  'check_circle',
    color: 'amber',
    steps: ['Burning subtitles…','Exporting MP4…','Saving to state manager…','Done!'],
  },
]

const colorMap = {
  violet:  { ring:'border-violet-500',  bg:'bg-violet-600/10',  text:'text-violet-400',  bar:'from-violet-600 to-violet-400',  glow:'shadow-[0_0_20px_rgba(124,58,237,0.3)]' },
  blue:    { ring:'border-blue-500',    bg:'bg-blue-600/10',    text:'text-blue-400',    bar:'from-blue-600 to-blue-400',      glow:'shadow-[0_0_20px_rgba(37,99,235,0.3)]' },
  emerald: { ring:'border-emerald-500', bg:'bg-emerald-600/10', text:'text-emerald-400', bar:'from-emerald-600 to-emerald-400',glow:'shadow-[0_0_20px_rgba(16,185,129,0.3)]' },
  amber:   { ring:'border-amber-500',   bg:'bg-amber-600/10',   text:'text-amber-400',   bar:'from-amber-500 to-amber-300',    glow:'shadow-[0_0_20px_rgba(245,158,11,0.3)]' },
}

const DEMO_SCENES = [
  { scene_id:'scene_1', setting:"Ethan's bedroom, late night", tone:'tense', duration_estimate_sec:12,
    dialogue_lines:[{character_name:'Ethan',text:"I can't stop now — I'm so close to qualifying.",emotion:'determined'},{character_name:'Dad',text:'Son, it is past midnight. Your exams are tomorrow.',emotion:'worried'}] },
  { scene_id:'scene_2', setting:'Family living room, dinner', tone:'sad', duration_estimate_sec:15,
    dialogue_lines:[{character_name:'Mom',text:'We just want what is best for you, Ethan.',emotion:'sad'},{character_name:'Ethan',text:'Then let me show you what I am capable of.',emotion:'determined'}] },
  { scene_id:'scene_3', setting:'Deserted tournament hall', tone:'dark', duration_estimate_sec:11,
    dialogue_lines:[{character_name:'Ethan',text:'I lost everything for this… and I still lost.',emotion:'sad'}] },
  { scene_id:'scene_4', setting:'Living room, early morning', tone:'epic', duration_estimate_sec:16,
    dialogue_lines:[{character_name:'Dad',text:'We do not want you to give up your dream. We want to be part of it.',emotion:'determined'},{character_name:'Ethan',text:'Dad…',emotion:'sad'}] },
  { scene_id:'scene_5', setting:"Ethan's room, sunset", tone:'peaceful', duration_estimate_sec:10,
    dialogue_lines:[{character_name:'Ethan',text:'I will find the balance. For all of us.',emotion:'happy'}] },
]

const toneColor = {
  tense:'text-red-400 bg-red-600/10', sad:'text-blue-400 bg-blue-600/10',
  dark:'text-slate-400 bg-slate-600/10', epic:'text-amber-400 bg-amber-600/10',
  peaceful:'text-emerald-400 bg-emerald-600/10', happy:'text-yellow-400 bg-yellow-600/10',
  mysterious:'text-purple-400 bg-purple-600/10', action:'text-orange-400 bg-orange-600/10',
  heroic:'text-amber-300 bg-amber-600/10', romantic:'text-pink-400 bg-pink-600/10',
}

/* ── WebSocket hook ─────────────────────────────────────── */
function usePhaseProgress(runId) {
  const [phases, setPhases] = useState(
    PHASES.reduce((acc, p) => ({ ...acc, [p.key]: { status: 'waiting', progress: 0, step: '', log: [] } }), {})
  )
  const [done, setDone]       = useState(false)
  const [simMode, setSimMode] = useState(false)
  const simStarted            = useRef(false)
  const doneRef               = useRef(false)
  const wsRef                 = useRef(null)

  function startSim() {
    if (simStarted.current) return
    simStarted.current = true
    setSimMode(true)
    runSimulation(setPhases, setDone)
  }

  useEffect(() => {
    if (!runId) { startSim(); return }
    if (runId.startsWith('demo_')) { startSim(); return }

    let ws
    let noEventsTimer = null

    function attachHandlers(socket) {
      socket.onmessage = e => {
        let data
        try { data = JSON.parse(e.data) } catch { return }
        if (!data.phase) return

        clearTimeout(noEventsTimer)
        noEventsTimer = null

        setPhases(prev => ({
          ...prev,
          [`phase${data.phase}`]: {
            status:   data.status,
            progress: data.progress ?? prev[`phase${data.phase}`]?.progress ?? 0,
            step:     data.message ?? '',
            log:      [...(prev[`phase${data.phase}`]?.log || []), data.message].filter(Boolean).slice(-8),
          }
        }))
        if (data.status === 'done' && data.phase === 4) { doneRef.current = true; setDone(true) }
      }

      socket.onclose = e => {
        clearTimeout(noEventsTimer)
        if (e.code !== 1000 && !doneRef.current) startSim()
      }
    }

    function tryConnect(url, onFailFallback) {
      let sock
      try { sock = new WebSocket(url) } catch { onFailFallback(); return null }

      const failTimer = setTimeout(() => {
        sock.onopen = sock.onerror = sock.onclose = null
        try { sock.close() } catch {}
        onFailFallback()
      }, 4000)

      sock.onopen = () => {
        clearTimeout(failTimer)
        ws = sock
        wsRef.current = sock
        attachHandlers(sock)
        noEventsTimer = setTimeout(startSim, 90000)
      }

      sock.onerror = () => {
        clearTimeout(failTimer)
        try { sock.close() } catch {}
        onFailFallback()
      }

      return sock
    }

    const proto    = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const proxyUrl  = `${proto}//${window.location.host}/ws/${runId}`
    const directUrl = `ws://localhost:8000/ws/${runId}`

    tryConnect(proxyUrl, () => tryConnect(directUrl, () => startSim()))

    return () => {
      clearTimeout(noEventsTimer)
      try { ws?.close?.() } catch {}
    }
  }, [runId])

  function retryPhase(phaseId) {
    if (!runId || runId.startsWith('demo_')) return
    setPhases(prev => {
      const next = { ...prev }
      PHASES.forEach(p => {
        if (p.id >= phaseId) next[p.key] = { status: 'waiting', progress: 0, step: '', log: [] }
      })
      return next
    })
    setDone(false)
    doneRef.current = false
    fetch(`/api/runs/${runId}/rerun/${phaseId}`, { method: 'POST' }).catch(console.error)
  }

  return { phases, done, simMode, retryPhase }
}

function runSimulation(setPhases, setDone) {
  PHASES.forEach((phase, pi) => {
    const baseDelay = pi * 6000
    setTimeout(() => {
      setPhases(prev => ({ ...prev, [phase.key]: { ...prev[phase.key], status: 'running', progress: 0 } }))
    }, baseDelay)
    phase.steps.forEach((stepMsg, si) => {
      setTimeout(() => {
        const prog = Math.round(((si + 1) / phase.steps.length) * 100)
        setPhases(prev => ({
          ...prev,
          [phase.key]: {
            status:   si === phase.steps.length - 1 ? 'done' : 'running',
            progress: prog,
            step:     stepMsg,
            log:      [...(prev[phase.key].log || []), stepMsg].slice(-8),
          }
        }))
        if (pi === PHASES.length - 1 && si === phase.steps.length - 1) {
          setTimeout(() => setDone(true), 400)
        }
      }, baseDelay + (si + 1) * 1400)
    })
  })
}

/* ── Phase card ─────────────────────────────────────────── */
function PhaseCard({ phase, state, onRetry }) {
  const c = colorMap[phase.color]
  const isDone    = state.status === 'done'
  const isRunning = state.status === 'running'
  const isWaiting = state.status === 'waiting'
  const isError   = state.status === 'error'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`rounded-2xl border-2 overflow-hidden transition-all duration-500
        ${isDone    ? `${c.ring} ${c.bg} ${c.glow}` :
          isRunning ? 'border-border-bright bg-surface' :
          isError   ? 'border-red-500/60 bg-red-600/5' :
                      'border-border bg-surface/50'}`}
    >
      <div className="flex items-center gap-4 p-5">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-all
          ${isDone    ? `${c.bg} border border-current` :
            isRunning ? 'bg-surface border border-border-bright' :
            isError   ? 'bg-red-600/10 border border-red-500/40' :
                        'bg-background border border-border'}`}>
          {isDone ? (
            <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }}
              className={`material-symbols-outlined text-[24px] icon-fill ${c.text}`}>check_circle</motion.span>
          ) : isRunning ? (
            <motion.span animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className={`material-symbols-outlined text-[24px] ${c.text}`}>sync</motion.span>
          ) : isError ? (
            <span className="material-symbols-outlined text-[24px] icon-fill text-red-400">error</span>
          ) : (
            <span className="material-symbols-outlined text-[24px] text-slate-600">{phase.icon}</span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`font-display text-[10px] uppercase tracking-widest ${isError ? 'text-red-400' : c.text}`}>Phase {phase.id}</span>
            {isDone && (
              <motion.span initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-600/20 text-emerald-400 font-display font-bold border border-emerald-600/30">
                DONE
              </motion.span>
            )}
            {isRunning && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-600/20 text-amber-400 font-display font-bold border border-amber-600/30 animate-pulse">
                RUNNING
              </span>
            )}
            {isError && (
              <motion.span initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                className="text-[10px] px-2 py-0.5 rounded-full bg-red-600/20 text-red-400 font-display font-bold border border-red-600/30">
                FAILED
              </motion.span>
            )}
          </div>
          <p className="text-white font-display font-semibold text-base mt-0.5">{phase.label}</p>
          <p className="text-slate-500 text-xs mt-0.5 truncate">{phase.sub}</p>
        </div>

        {!isWaiting && !isError && (
          <motion.span key={state.progress} initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className={`font-display font-black text-2xl ${isDone ? c.text : 'text-white'}`}>
            {state.progress}%
          </motion.span>
        )}
        {isError && phase.id <= 3 && onRetry && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            onClick={onRetry}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600/20 border border-red-500/40
                       text-red-400 font-display font-bold text-[11px] hover:bg-red-600/30 transition-colors"
          >
            <span className="material-symbols-outlined text-[14px]">refresh</span>
            RETRY
          </motion.button>
        )}
      </div>

      {!isWaiting && (
        <div className="px-5 pb-3">
          <div className="h-1.5 bg-background rounded-full overflow-hidden">
            <motion.div className={`h-full bg-gradient-to-r ${c.bar} rounded-full`}
              initial={{ width: '0%' }} animate={{ width: `${state.progress}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }} />
          </div>
        </div>
      )}

      <AnimatePresence>
        {(isRunning || isDone) && state.log?.length > 0 && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }} className="overflow-hidden">
            <div className="mx-5 mb-4 p-3 bg-background rounded-xl border border-border font-mono text-[11px] space-y-1 max-h-24 overflow-y-auto">
              {state.log.map((line, i) => (
                <motion.p key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  className={`${i === state.log.length - 1 ? c.text : 'text-slate-500'} flex items-center gap-2`}>
                  <span>{i === state.log.length - 1 ? '▶' : '✓'}</span>
                  {line}
                </motion.p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

/* ── Live output sub-components ─────────────────────────── */
function ScriptPreview({ scenes }) {
  const [open, setOpen] = useState(null)

  if (!scenes.length) {
    return (
      <div className="flex items-center justify-center py-8">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          className="material-symbols-outlined text-violet-500 text-3xl">sync</motion.div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {scenes.map((scene, i) => {
        const isOpen = open === scene.scene_id
        return (
          <div key={scene.scene_id} className="rounded-xl border border-border bg-background/50 overflow-hidden">
            <button
              onClick={() => setOpen(isOpen ? null : scene.scene_id)}
              className="w-full flex items-center gap-3 p-3 text-left hover:bg-white/[0.02] transition-colors"
            >
              <div className="w-6 h-6 rounded-lg bg-violet-600/15 border border-violet-600/30 flex items-center justify-center flex-shrink-0">
                <span className="font-display font-black text-violet-400 text-[10px]">{i + 1}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-semibold truncate">{scene.setting}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-display font-bold ${toneColor[scene.tone] ?? 'text-slate-400 bg-slate-600/10'}`}>
                    {scene.tone}
                  </span>
                  <span className="text-slate-600 text-[9px] font-display">
                    {scene.dialogue_lines?.length || 0} lines · ~{scene.duration_estimate_sec}s
                  </span>
                </div>
              </div>
              <span className={`material-symbols-outlined text-slate-500 text-[16px] transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`}>
                expand_more
              </span>
            </button>

            <AnimatePresence>
              {isOpen && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                  <div className="px-3 pb-3 pt-2 space-y-2 border-t border-border/50">
                    {(scene.dialogue_lines || []).map((line, li) => (
                      <div key={li} className="flex gap-2 items-start">
                        <div className="w-5 h-5 rounded-full bg-gradient-to-br from-violet-700 to-blue-700
                                        flex items-center justify-center text-white font-bold text-[9px] flex-shrink-0 mt-0.5">
                          {line.character_name?.[0] || '?'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-violet-300 font-display font-bold text-[10px]">{line.character_name}</p>
                          <p className="text-slate-300 text-[11px] leading-relaxed">"{line.text}"</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )
      })}
    </div>
  )
}

function AudioPreview({ files }) {
  if (!files.length) {
    return (
      <div className="flex items-center justify-center py-8">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          className="material-symbols-outlined text-blue-500 text-3xl">sync</motion.div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {files.map(f => (
        <div key={f.scene_id} className="rounded-xl border border-border bg-background/50 p-3">
          <p className="text-white text-xs font-display font-semibold mb-2 capitalize">
            {f.scene_id.replace('_', ' ')} — mixed
          </p>
          <audio
            controls
            src={f.url}
            className="w-full"
            style={{ height: '36px', colorScheme: 'dark' }}
          />
        </div>
      ))}
    </div>
  )
}

function ImagesPreview({ images }) {
  const [lightbox, setLightbox] = useState(null)

  if (!images.length) {
    return (
      <div className="flex items-center justify-center py-8">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          className="material-symbols-outlined text-emerald-500 text-3xl">sync</motion.div>
      </div>
    )
  }

  const byScene = images.reduce((acc, img) => {
    ;(acc[img.scene_id] = acc[img.scene_id] || []).push(img)
    return acc
  }, {})

  return (
    <>
      <AnimatePresence>
        {lightbox && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setLightbox(null)}
            className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-6 cursor-zoom-out">
            <motion.img initial={{ scale: 0.85 }} animate={{ scale: 1 }} exit={{ scale: 0.85 }}
              src={lightbox} className="max-w-full max-h-full rounded-2xl shadow-2xl object-contain"
              onClick={e => e.stopPropagation()} />
            <button onClick={() => setLightbox(null)}
              className="absolute top-6 right-6 w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20">
              <span className="material-symbols-outlined text-white">close</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-4">
        {Object.entries(byScene).map(([sid, imgs], si) => (
          <div key={sid}>
            <p className="text-slate-500 text-[10px] uppercase tracking-widest font-display mb-2">
              {sid.replace('_', ' ')}
            </p>
            <div className="grid grid-cols-3 gap-1.5">
              {imgs.map(img => (
                <motion.div key={img.filename} whileHover={{ scale: 1.03 }}
                  onClick={() => setLightbox(img.url)}
                  className="aspect-video rounded-lg overflow-hidden border border-border cursor-zoom-in">
                  <img src={img.url} alt={img.filename}
                    className="w-full h-full object-cover hover:brightness-110 transition-all" loading="lazy" />
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

/* ── Live output panel ──────────────────────────────────── */
function LivePreview({ runId, phases }) {
  const [scenes,     setScenes]     = useState([])
  const [audioFiles, setAudioFiles] = useState([])
  const [images,     setImages]     = useState([])
  const [activeTab,  setActiveTab]  = useState(null)

  const p1Done = phases.phase1?.status === 'done'
  const p2Done = phases.phase2?.status === 'done'
  const p3Done = phases.phase3?.status === 'done'
  const isDemo = !runId || runId.startsWith('demo_')

  useEffect(() => {
    if (!p1Done) return
    setActiveTab('script')
    if (isDemo) { setScenes(DEMO_SCENES); return }
    fetch(`/api/runs/${runId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.script?.scenes) setScenes(d.script.scenes) })
      .catch(() => {})
  }, [p1Done])

  useEffect(() => {
    if (!p2Done) return
    setActiveTab('audio')
    if (isDemo) return
    fetch(`/api/runs/${runId}/audio`)
      .then(r => r.ok ? r.json() : { files: [] })
      .then(d => setAudioFiles(d.files || []))
      .catch(() => {})
  }, [p2Done])

  useEffect(() => {
    if (!p3Done) return
    setActiveTab('images')
    if (isDemo) return
    fetch(`/api/runs/${runId}/images`)
      .then(r => r.ok ? r.json() : { images: [] })
      .then(d => setImages(d.images || []))
      .catch(() => {})
  }, [p3Done])

  const anyDone = p1Done || p2Done || p3Done

  if (!anyDone) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <motion.div animate={{ opacity: [0.3, 0.8, 0.3] }} transition={{ duration: 2.5, repeat: Infinity }}>
            <span className="material-symbols-outlined text-5xl text-slate-700 block mb-3">preview</span>
          </motion.div>
          <p className="text-slate-500 font-display font-semibold text-sm">Live Output</p>
          <p className="text-slate-600 text-xs mt-1">Outputs appear here as phases complete</p>
        </div>
      </div>
    )
  }

  const tabs = [
    p1Done && { key: 'script', label: 'Script', icon: 'edit_note',       color: 'violet', activeClass: 'bg-violet-600/20 text-violet-400 border border-violet-500/40' },
    p2Done && { key: 'audio',  label: 'Audio',  icon: 'headphones',      color: 'blue',   activeClass: 'bg-blue-600/20 text-blue-400 border border-blue-500/40' },
    p3Done && { key: 'images', label: 'Images', icon: 'image',           color: 'emerald',activeClass: 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/40' },
  ].filter(Boolean)

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Tab bar */}
      <div className="flex gap-1.5 p-3 border-b border-border flex-shrink-0">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-display font-bold transition-all
              ${activeTab === t.key ? t.activeClass : 'text-slate-500 hover:text-white hover:bg-white/5'}`}>
            <span className="material-symbols-outlined text-[14px]">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        <AnimatePresence mode="wait">
          {activeTab === 'script' && (
            <motion.div key="script" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <ScriptPreview scenes={scenes} />
            </motion.div>
          )}
          {activeTab === 'audio' && (
            <motion.div key="audio" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <AudioPreview files={audioFiles} />
            </motion.div>
          )}
          {activeTab === 'images' && (
            <motion.div key="images" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <ImagesPreview images={images} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

/* ── Page ───────────────────────────────────────────────── */
export default function ProgressPage() {
  const { runId } = useParams()
  const navigate  = useNavigate()
  const { phases, done, simMode, retryPhase } = usePhaseProgress(runId)

  const activePhase = PHASES.find(p => phases[p.key]?.status === 'running')

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background relative"
    >
      {/* Violet sine-wave particle grid — lazy-loaded, fixed behind scrolling content */}
      <Suspense fallback={null}>
        <DottedSurface className="fixed inset-0 z-0" />
      </Suspense>

      <Header />

      <div className="relative z-10 pt-24 pb-16 px-6">
        <div className="container mx-auto max-w-6xl">

          {/* Top info */}
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-2">
              <p className="font-display text-[10px] uppercase tracking-widest text-violet-400">
                Run ID: {runId}
              </p>
              {simMode && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-600/20 text-amber-400 border border-amber-600/30 font-display font-bold">
                  DEMO MODE
                </span>
              )}
            </div>
            <h1 className="font-display font-black text-3xl text-white mb-2">
              {done ? '🎬 Your Film is Ready!' : 'Generating Your Film…'}
            </h1>
            <p className="text-slate-500 text-sm">
              {done
                ? 'All phases complete. Click below to open your film in Studio.'
                : activePhase
                  ? `Currently: Phase ${activePhase.id} — ${activePhase.label}`
                  : 'Starting pipeline…'}
            </p>
          </motion.div>

          {/* 2-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

            {/* LEFT — phase cards + done CTA */}
            <div className="space-y-4">
              {PHASES.map(phase => (
                <PhaseCard key={phase.id} phase={phase} state={phases[phase.key]} onRetry={() => retryPhase(phase.id)} />
              ))}

              <AnimatePresence>
                {done && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ duration: 0.5, type: 'spring', bounce: 0.3 }}
                    className="text-center"
                  >
                    <div className="inline-flex flex-col items-center gap-4 p-8 rounded-2xl glass-bright glow-violet w-full">
                      <motion.div animate={{ scale: [1, 1.15, 1] }} transition={{ duration: 1.5, repeat: Infinity }}
                        className="w-16 h-16 rounded-full bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center">
                        <span className="material-symbols-outlined text-white text-3xl icon-fill">movie</span>
                      </motion.div>
                      <p className="text-white font-display font-bold text-lg">Film Complete!</p>
                      <motion.button
                        whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                        onClick={() => navigate(`/studio/${runId}`)}
                        className="px-10 py-4 rounded-full bg-gradient-to-r from-violet-600 to-blue-600
                                   text-white font-display font-bold text-sm tracking-wider
                                   shadow-[0_0_30px_rgba(124,58,237,0.6)]"
                      >
                        <span className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-[18px] icon-fill">play_circle</span>
                          OPEN IN STUDIO
                        </span>
                      </motion.button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* RIGHT — live output preview */}
            <div className="lg:sticky lg:top-24 rounded-2xl border border-border bg-surface overflow-hidden"
              style={{ minHeight: '520px', maxHeight: 'calc(100vh - 7rem)', display: 'flex', flexDirection: 'column' }}>
              {/* Panel header */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border flex-shrink-0">
                <span className="material-symbols-outlined text-[18px] text-slate-500">tv</span>
                <span className="font-display text-[11px] uppercase tracking-widest text-slate-500">Live Output</span>
                <div className="ml-auto flex gap-1">
                  {['phase1','phase2','phase3'].map((pk, i) => (
                    <div key={pk} className={`w-2 h-2 rounded-full transition-colors ${
                      phases[pk]?.status === 'done'    ? ['bg-violet-500','bg-blue-500','bg-emerald-500'][i] :
                      phases[pk]?.status === 'running' ? 'bg-amber-400 animate-pulse' :
                                                         'bg-slate-700'
                    }`} />
                  ))}
                </div>
              </div>

              {/* Live preview content */}
              <LivePreview runId={runId} phases={phases} />
            </div>

          </div>
        </div>
      </div>
    </motion.div>
  )
}
