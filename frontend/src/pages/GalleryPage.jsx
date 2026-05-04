import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header.jsx'

const STATUS_BADGE = {
  done:         'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
  running:      'bg-amber-600/20   text-amber-400   border-amber-600/30   animate-pulse',
  phase1_done:  'bg-blue-600/20    text-blue-400    border-blue-600/30',
  phase2_done:  'bg-blue-600/20    text-blue-400    border-blue-600/30',
  phase3_done:  'bg-violet-600/20  text-violet-400  border-violet-600/30',
  pending:      'bg-slate-600/20   text-slate-400   border-slate-600/30',
  error:        'bg-red-600/20     text-red-400     border-red-600/30',
  unknown:      'bg-slate-600/20   text-slate-400   border-slate-600/30',
}
const STATUS_LABEL = {
  done: 'Done', running: 'Running', pending: 'Pending',
  phase1_done: 'Phase 1 ✓', phase2_done: 'Phase 2 ✓', phase3_done: 'Phase 3 ✓',
  error: 'Error', unknown: 'Unknown',
}

const DEMO_RUNS = [
  { run_id:'demo_run_001', prompt:'A gamer who sacrifices everything for his dream', style:'2D animated', duration:'medium', status:'done', has_video:false, thumbnail_url:null, created_at:'2026-05-03T00:28:12' },
  { run_id:'demo_run_002', prompt:'Two siblings separated by war find each other', style:'anime', duration:'long', status:'done', has_video:false, thumbnail_url:null, created_at:'2026-05-02T22:15:00' },
  { run_id:'demo_run_003', prompt:'A young astronaut discovers a hidden ocean on Mars', style:'Pixar 3D', duration:'short', status:'phase2_done', has_video:false, thumbnail_url:null, created_at:'2026-05-02T20:00:00' },
]

const toneColor = {
  tense:'text-red-400 bg-red-600/10', sad:'text-blue-400 bg-blue-600/10',
  dark:'text-slate-400 bg-slate-600/10', epic:'text-amber-400 bg-amber-600/10',
  peaceful:'text-emerald-400 bg-emerald-600/10', happy:'text-yellow-400 bg-yellow-600/10',
  mysterious:'text-purple-400 bg-purple-600/10', action:'text-orange-400 bg-orange-600/10',
}

/* ── Run detail drawer ─────────────────────────────────── */
function RunDrawer({ run, onClose, navigate }) {
  const [tab, setTab]           = useState('script')
  const [data, setData]         = useState(null)
  const [images, setImages]     = useState([])
  const [audioLines, setAudio]  = useState([])
  const [loading, setLoading]   = useState(true)
  const [lightbox, setLightbox] = useState(null)

  useEffect(() => {
    if (!run) return
    if (run.run_id.startsWith('demo_')) { setLoading(false); return }

    setLoading(true)
    setData(null); setImages([]); setAudio([])

    fetch(`/api/runs/${run.run_id}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .catch(() => {})
      .finally(() => setLoading(false))

    fetch(`/api/runs/${run.run_id}/images`)
      .then(r => r.ok ? r.json() : { images: [] })
      .then(d => setImages(d.images || []))
      .catch(() => {})

    fetch(`/api/runs/${run.run_id}/audio`)
      .then(r => r.ok ? r.json() : { lines: [] })
      .then(d => setAudio(d.lines || []))
      .catch(() => {})
  }, [run?.run_id])

  const story      = data?.story
  const characters = data?.characters?.characters || []
  const scenes     = data?.script?.scenes || []
  const audioByChar = audioLines.reduce((acc, f) => {
    ;(acc[f.character_name || 'Unknown'] = acc[f.character_name || 'Unknown'] || []).push(f)
    return acc
  }, {})
  const imagesByScene = images.reduce((acc, img) => {
    ;(acc[img.scene_id] = acc[img.scene_id] || []).push(img)
    return acc
  }, {})

  const TABS = [
    { key:'script',     label:'Script',     icon:'edit_note'       },
    { key:'characters', label:'Characters', icon:'group'           },
    { key:'images',     label:'Images',     icon:'image'           },
    { key:'audio',      label:'Audio',      icon:'headphones'      },
  ]

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
      />

      {/* Lightbox */}
      <AnimatePresence>
        {lightbox && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
            onClick={() => setLightbox(null)}
            className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center p-6 cursor-zoom-out">
            <motion.img initial={{ scale:0.85 }} animate={{ scale:1 }} exit={{ scale:0.85 }}
              src={lightbox} className="max-w-full max-h-full rounded-2xl object-contain"
              onClick={e => e.stopPropagation()} />
            <button onClick={() => setLightbox(null)}
              className="absolute top-6 right-6 w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20">
              <span className="material-symbols-outlined text-white">close</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Drawer */}
      <motion.div
        initial={{ x:'100%' }} animate={{ x:0 }} exit={{ x:'100%' }}
        transition={{ type:'spring', damping:28, stiffness:280 }}
        className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-2xl bg-background border-l border-border flex flex-col shadow-2xl"
      >
        {/* Drawer header */}
        <div className="flex items-center gap-4 px-6 py-4 border-b border-border flex-shrink-0">
          <button onClick={onClose}
            className="w-9 h-9 rounded-xl border border-border flex items-center justify-center text-slate-500 hover:text-white hover:border-border-bright transition-colors">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
          <div className="flex-1 min-w-0">
            <p className="text-white font-display font-semibold text-sm truncate">{run.prompt || 'Untitled'}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-[10px] px-2 py-0.5 rounded-full border font-display font-bold ${STATUS_BADGE[run.status] || STATUS_BADGE.unknown}`}>
                {STATUS_LABEL[run.status] || run.status}
              </span>
              <span className="text-slate-600 text-[10px] font-display">{run.style} · {run.duration}</span>
            </div>
          </div>
          <motion.button
            whileHover={{ scale:1.04 }} whileTap={{ scale:0.97 }}
            onClick={() => navigate(`/studio/${run.run_id}`)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600
                       text-white font-display font-bold text-xs flex items-center gap-1.5
                       shadow-[0_0_12px_rgba(124,58,237,0.4)] flex-shrink-0"
          >
            <span className="material-symbols-outlined text-[16px] icon-fill">open_in_full</span>
            Studio
          </motion.button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border flex-shrink-0">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-[11px] font-display font-bold transition-colors relative
                ${tab === t.key ? 'text-white' : 'text-slate-500 hover:text-slate-300'}`}>
              <span className="material-symbols-outlined text-[14px]">{t.icon}</span>
              <span className="hidden sm:inline">{t.label}</span>
              {tab === t.key && (
                <motion.div layoutId="drawer-tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-violet-500 to-blue-500" />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <motion.div animate={{ rotate:360 }} transition={{ duration:1.2, repeat:Infinity, ease:'linear' }}
                className="material-symbols-outlined text-violet-500 text-4xl">sync</motion.div>
            </div>
          ) : (
            <AnimatePresence mode="wait">

              {/* SCRIPT */}
              {tab === 'script' && (
                <motion.div key="script" initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}>
                  {scenes.length === 0 ? (
                    <p className="text-slate-500 text-center py-10">No script data available</p>
                  ) : (
                    <div className="space-y-3">
                      {scenes.map((scene, i) => (
                        <div key={scene.scene_id} className="rounded-xl border border-border bg-surface/50 overflow-hidden">
                          <div className="flex items-center gap-3 p-4">
                            <div className="w-8 h-8 rounded-lg bg-violet-600/15 border border-violet-600/30 flex items-center justify-center flex-shrink-0">
                              <span className="font-display font-black text-violet-400 text-sm">{i+1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-white font-semibold text-sm truncate">{scene.setting}</p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-display font-bold ${toneColor[scene.tone] ?? 'text-slate-400 bg-slate-600/10'}`}>{scene.tone}</span>
                                <span className="text-slate-600 text-[10px]">{scene.dialogue_lines?.length || 0} lines</span>
                              </div>
                            </div>
                          </div>
                          {(scene.dialogue_lines || []).length > 0 && (
                            <div className="px-4 pb-4 space-y-2 border-t border-border/50 pt-3">
                              {scene.dialogue_lines.map((line, li) => (
                                <div key={li} className="flex gap-2 items-start">
                                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-700 to-blue-700 flex items-center justify-center text-white font-bold text-[10px] flex-shrink-0 mt-0.5">
                                    {line.character_name?.[0] || '?'}
                                  </div>
                                  <div>
                                    <p className="text-violet-300 font-display font-bold text-[11px]">{line.character_name}</p>
                                    <p className="text-slate-300 text-sm leading-relaxed">"{line.text}"</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}

              {/* CHARACTERS */}
              {tab === 'characters' && (
                <motion.div key="chars" initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
                  className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {characters.length === 0 ? (
                    <p className="text-slate-500 text-center py-10 col-span-2">No character data available</p>
                  ) : characters.map((c, i) => (
                    <div key={c.name} className="rounded-2xl border border-border bg-surface/50 p-4">
                      <div className="w-full aspect-video rounded-xl bg-gradient-to-br from-violet-900/40 to-blue-900/40 border border-border flex items-center justify-center mb-3">
                        <span className="font-display font-black text-4xl text-gradient">{c.name[0]}</span>
                      </div>
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="text-white font-display font-semibold text-sm">{c.name}</h3>
                        <span className={`text-[10px] px-2 py-0.5 rounded border font-display font-bold
                          ${ c.role === 'Protagonist' ? 'bg-violet-600/20 text-violet-400 border-violet-500/30' :
                             c.role === 'Antagonist'  ? 'bg-red-600/20 text-red-400 border-red-500/30' :
                                                        'bg-blue-600/20 text-blue-400 border-blue-500/30' }`}>
                          {c.role}
                        </span>
                      </div>
                      {c.voice_personality && <p className="text-slate-500 text-xs italic">"{c.voice_personality}"</p>}
                    </div>
                  ))}
                </motion.div>
              )}

              {/* IMAGES */}
              {tab === 'images' && (
                <motion.div key="images" initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}>
                  {images.length === 0 ? (
                    <div className="text-center py-10">
                      <span className="material-symbols-outlined text-5xl text-slate-700 block mb-3">image_not_supported</span>
                      <p className="text-slate-500">No images generated yet</p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {Object.entries(imagesByScene).map(([sid, imgs], si) => (
                        <div key={sid}>
                          <p className="text-slate-500 text-[10px] uppercase tracking-widest font-display mb-2">{sid.replace('_',' ')}</p>
                          <div className="grid grid-cols-3 gap-2">
                            {imgs.map(img => (
                              <motion.div key={img.filename} whileHover={{ scale:1.03 }}
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
                  )}
                </motion.div>
              )}

              {/* AUDIO */}
              {tab === 'audio' && (
                <motion.div key="audio" initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
                  className="space-y-4">
                  {Object.keys(audioByChar).length === 0 ? (
                    <div className="text-center py-10">
                      <span className="material-symbols-outlined text-5xl text-slate-700 block mb-3">mic_off</span>
                      <p className="text-slate-500">No audio generated yet</p>
                    </div>
                  ) : (
                    Object.entries(audioByChar).map(([charName, lines]) => (
                      <div key={charName} className="rounded-xl border border-border bg-surface/50 p-4">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center font-bold text-sm flex-shrink-0">
                            {charName[0]}
                          </div>
                          <div>
                            <p className="text-white font-display font-semibold text-sm">{charName}</p>
                            <p className="text-slate-500 text-xs">{lines.length} line{lines.length !== 1 ? 's' : ''}</p>
                          </div>
                        </div>
                        <div className="space-y-2">
                          {lines.map(line => (
                            <div key={line.filename} className="flex items-center gap-3 bg-background/50 rounded-lg px-3 py-2">
                              <span className="text-[10px] text-slate-500 font-display font-bold uppercase flex-shrink-0">
                                {line.scene_id?.replace('scene_','')} · {line.emotion}
                              </span>
                              <audio controls src={line.url} className="flex-1 min-w-0"
                                style={{ height:'32px', colorScheme:'dark' }} />
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </motion.div>
              )}

            </AnimatePresence>
          )}
        </div>
      </motion.div>
    </>
  )
}

/* ── Run card ──────────────────────────────────────────── */
function RunCard({ run, index, onExpand, onOpen }) {
  const badgeClass = STATUS_BADGE[run.status] || STATUS_BADGE.unknown
  const label      = STATUS_LABEL[run.status]  || run.status
  const date = run.created_at
    ? new Date(run.created_at).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })
    : ''
  const styleIcon = { 'anime':'auto_fix_high','Pixar 3D':'view_in_ar','comic book':'menu_book','watercolor':'palette','realistic cinematic':'photo_camera' }[run.style] || 'animation'

  return (
    <motion.div
      initial={{ opacity:0, y:20 }}
      animate={{ opacity:1, y:0 }}
      transition={{ delay:index * 0.06, duration:0.4 }}
      whileHover={{ y:-4, borderColor:'rgba(124,58,237,0.4)' }}
      className="bg-surface border border-border rounded-2xl overflow-hidden cursor-pointer transition-colors duration-300 group"
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-gradient-to-br from-violet-900/40 via-background to-blue-900/30 relative flex items-center justify-center overflow-hidden"
        onClick={onOpen}>
        {run.thumbnail_url ? (
          <img src={run.thumbnail_url} alt={run.prompt}
            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
        ) : run.has_video ? (
          <video src={run.video_url} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
            muted onMouseEnter={e => e.target.play()} onMouseLeave={e => { e.target.pause(); e.target.currentTime = 0 }} />
        ) : (
          <>
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(124,58,237,0.15),transparent)]" />
            <span className="material-symbols-outlined text-5xl text-violet-700/60">{styleIcon}</span>
          </>
        )}
        <div className="absolute top-3 right-3">
          <span className={`text-[10px] px-2 py-0.5 rounded-full border font-display font-bold ${badgeClass}`}>{label}</span>
        </div>
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-12 h-12 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-2xl icon-fill">open_in_full</span>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="p-5" onClick={onOpen}>
        <p className="text-white font-display font-semibold text-sm leading-snug line-clamp-2 mb-3">
          {run.prompt || 'Untitled film'}
        </p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-violet-400 text-[16px]">palette</span>
            <span className="text-slate-500 text-xs font-display">{run.style || '—'}</span>
            <span className="text-slate-700">·</span>
            <span className="text-slate-500 text-xs font-display capitalize">{run.duration || '—'}</span>
          </div>
          <span className="text-slate-600 text-[10px] font-display">{date}</span>
        </div>
      </div>

      {/* Action strip */}
      <div className="px-5 pb-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={e => { e.stopPropagation(); onExpand() }}
          className="text-xs font-display font-bold text-violet-400 flex items-center gap-1 hover:text-violet-300 transition-colors">
          <span className="material-symbols-outlined text-[14px]">folder_open</span>
          View Assets
        </button>
        <button onClick={e => { e.stopPropagation(); onOpen() }}
          className="ml-auto text-xs font-display font-bold text-slate-400 flex items-center gap-1 hover:text-white transition-colors">
          <span className="material-symbols-outlined text-[14px]">open_in_full</span>
          Studio
        </button>
        {run.has_video && (
          <a href={run.video_url} onClick={e => e.stopPropagation()}
            className="text-xs font-display font-bold text-slate-400 flex items-center gap-1 hover:text-white transition-colors">
            <span className="material-symbols-outlined text-[14px]">download</span>
            MP4
          </a>
        )}
      </div>
    </motion.div>
  )
}

/* ── Page ──────────────────────────────────────────────── */
export default function GalleryPage() {
  const navigate = useNavigate()
  const [runs, setRuns]           = useState([])
  const [loading, setLoading]     = useState(true)
  const [filter, setFilter]       = useState('all')
  const [selectedRun, setSelectedRun] = useState(null)

  useEffect(() => {
    fetch('/api/runs')
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.runs?.length > 0) setRuns(data.runs)
        else setRuns(DEMO_RUNS)
      })
      .catch(() => setRuns(DEMO_RUNS))
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? runs : runs.filter(r => r.status === filter || r.status.startsWith(filter))

  function openRun(run) {
    if (run.status === 'running' || run.status.includes('phase')) {
      navigate(`/progress/${run.run_id}`)
    } else {
      navigate(`/studio/${run.run_id}`)
    }
  }

  return (
    <motion.div
      initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} transition={{ duration:0.3 }}
      className="min-h-screen bg-background"
    >
      <Header />

      <div className="pt-24 pb-16 px-6">
        <div className="container mx-auto max-w-6xl">

          {/* Header */}
          <motion.div initial={{ opacity:0, y:-10 }} animate={{ opacity:1, y:0 }} className="mb-10">
            <p className="font-display text-[10px] uppercase tracking-widest text-violet-400 mb-2">Your Films</p>
            <div className="flex items-end justify-between flex-wrap gap-4">
              <h1 className="font-display font-black text-4xl text-white">History</h1>
              <motion.button
                whileHover={{ scale:1.04 }} whileTap={{ scale:0.97 }}
                onClick={() => navigate('/create')}
                className="px-6 py-3 rounded-full bg-gradient-to-r from-violet-600 to-blue-600
                           text-white font-display font-bold text-sm flex items-center gap-2
                           shadow-[0_0_20px_rgba(124,58,237,0.4)]"
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
                New Film
              </motion.button>
            </div>
          </motion.div>

          {/* Filter pills */}
          <div className="flex gap-2 mb-8 flex-wrap">
            {['all','done','running','pending'].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-4 py-1.5 rounded-full border font-display text-xs font-bold tracking-wider transition-all
                  ${filter === f
                    ? 'border-violet-500 bg-violet-600/20 text-violet-300'
                    : 'border-border text-slate-500 hover:border-border-bright hover:text-slate-300'}`}>
                {f.toUpperCase()}
                {f !== 'all' && (
                  <span className="ml-2 opacity-60">{runs.filter(r => r.status === f || r.status.startsWith(f)).length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Grid */}
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1,2,3].map(i => (
                <div key={i} className="aspect-video rounded-2xl bg-surface border border-border animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} className="text-center py-24">
              <span className="material-symbols-outlined text-6xl text-slate-700 block mb-4">movie_filter</span>
              <p className="text-slate-500 font-display font-semibold text-lg mb-2">No films yet</p>
              <p className="text-slate-600 text-sm mb-8">Create your first film to see it here.</p>
              <motion.button whileHover={{ scale:1.04 }} whileTap={{ scale:0.97 }} onClick={() => navigate('/create')}
                className="px-8 py-3 rounded-full bg-gradient-to-r from-violet-600 to-blue-600 text-white font-display font-bold text-sm">
                Create Now
              </motion.button>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filtered.map((run, i) => (
                <RunCard
                  key={run.run_id}
                  run={run}
                  index={i}
                  onExpand={() => setSelectedRun(run)}
                  onOpen={() => openRun(run)}
                />
              ))}
            </div>
          )}

          {/* Stats */}
          {runs.length > 0 && (
            <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.3 }}
              className="mt-12 p-5 bg-surface border border-border rounded-2xl flex flex-wrap gap-6 justify-center">
              {[
                { label:'Total Films', value:runs.length,                                  icon:'movie' },
                { label:'Completed',   value:runs.filter(r => r.status === 'done').length, icon:'check_circle' },
                { label:'With Video',  value:runs.filter(r => r.has_video).length,         icon:'videocam' },
              ].map(s => (
                <div key={s.label} className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-violet-400 text-[20px]">{s.icon}</span>
                  <div>
                    <p className="font-display font-black text-2xl text-white">{s.value}</p>
                    <p className="font-display text-[10px] uppercase tracking-widest text-slate-500">{s.label}</p>
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </div>
      </div>

      {/* Run asset drawer */}
      <AnimatePresence>
        {selectedRun && (
          <RunDrawer
            run={selectedRun}
            onClose={() => setSelectedRun(null)}
            navigate={navigate}
          />
        )}
      </AnimatePresence>
    </motion.div>
  )
}
