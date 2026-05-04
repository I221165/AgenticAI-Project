import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header.jsx'

/* ── Style options ──────────────────────────────────────── */
const STYLES = [
  { id: '2D animated',         label: '2D Animated',  icon: 'animation',      glow: 'violet' },
  { id: 'anime',               label: 'Anime',         icon: 'auto_fix_high',  glow: 'blue' },
  { id: 'Pixar 3D',            label: 'Pixar 3D',      icon: 'view_in_ar',     glow: 'emerald' },
  { id: 'comic book',          label: 'Comic Book',    icon: 'menu_book',      glow: 'amber' },
  { id: 'watercolor',          label: 'Watercolor',    icon: 'palette',        glow: 'pink' },
  { id: 'realistic cinematic', label: 'Cinematic',     icon: 'photo_camera',   glow: 'slate' },
]

const DURATIONS = [
  { id: 'short',  label: 'Short',  sub: '~1 min · 3 scenes',  icon: 'timer' },
  { id: 'medium', label: 'Medium', sub: '~2 min · 5 scenes',  icon: 'hourglass_bottom' },
  { id: 'long',   label: 'Long',   sub: '~3 min · 7 scenes',  icon: 'hourglass_full' },
]

const LANGUAGES = ['English','Urdu','Arabic','French','Spanish','German']

const glowMap = {
  violet:  'border-violet-500  shadow-[0_0_20px_rgba(124,58,237,0.4)]  bg-violet-600/10',
  blue:    'border-blue-500    shadow-[0_0_20px_rgba(59,130,246,0.4)]  bg-blue-600/10',
  emerald: 'border-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.4)]  bg-emerald-600/10',
  amber:   'border-amber-500   shadow-[0_0_20px_rgba(245,158,11,0.4)]  bg-amber-600/10',
  pink:    'border-pink-500    shadow-[0_0_20px_rgba(236,72,153,0.4)]  bg-pink-600/10',
  slate:   'border-slate-500   shadow-[0_0_20px_rgba(100,116,139,0.3)] bg-slate-600/10',
}
const iconColorMap = {
  violet:'text-violet-400', blue:'text-blue-400', emerald:'text-emerald-400',
  amber:'text-amber-400',   pink:'text-pink-400', slate:'text-slate-400',
}

/* ── Step indicator ─────────────────────────────────────── */
const STEPS = ['Prompt','Style','Settings','Generate']

function StepIndicator({ current }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-12">
      {STEPS.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-display font-bold transition-all duration-300
            ${i < current  ? 'bg-violet-600/30 text-violet-300 border border-violet-600/50' :
              i === current ? 'bg-violet-600 text-white border border-violet-400' :
                              'bg-surface text-slate-600 border border-border'}`}>
            {i < current
              ? <span className="material-symbols-outlined text-[14px]">check</span>
              : <span>{i + 1}</span>}
            <span className={i === current ? '' : 'hidden sm:inline'}>{s}</span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-8 h-px transition-colors duration-500
              ${i < current ? 'bg-violet-600' : 'bg-border'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

/* ── Animated text placeholder cycling ─────────────────── */
const PLACEHOLDERS = [
  'A gamer who sacrifices everything for his dream...',
  'A young astronaut discovers a hidden ocean on Mars...',
  'Two siblings separated by war find each other again...',
  'An AI learns what it means to love a human...',
]

/* ── Page ───────────────────────────────────────────────── */
export default function CreatePage() {
  const navigate = useNavigate()
  const [step, setStep]         = useState(0)
  const [prompt, setPrompt]     = useState('')
  const [style, setStyle]       = useState('2D animated')
  const [duration, setDuration] = useState('medium')
  const [language, setLanguage] = useState('English')
  const [loading, setLoading]   = useState(false)
  const [phIdx, setPhIdx]       = useState(0)

  // Cycle placeholder text
  useEffect(() => {
    const t = setInterval(() => setPhIdx(i => (i + 1) % PLACEHOLDERS.length), 3000)
    return () => clearInterval(t)
  }, [])

  async function handleGenerate() {
    if (!prompt.trim()) return
    setLoading(true)
    try {
      const res = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, style, duration, language }),
      })
      if (res.ok) {
        const { run_id } = await res.json()
        navigate(`/progress/${run_id}`)
      } else {
        // Demo: navigate with a fake run_id
        navigate(`/progress/demo_run_001`)
      }
    } catch {
      navigate(`/progress/demo_run_001`)
    }
  }

  const slide = {
    initial: { opacity: 0, x: 40 },
    animate: { opacity: 1, x: 0 },
    exit:    { opacity: 0, x: -40 },
    transition: { duration: 0.3, ease: 'easeInOut' },
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background"
    >
      <Header />

      {/* Background glow */}
      <div className="fixed inset-0 pointer-events-none
                      bg-[radial-gradient(ellipse_80%_50%_at_50%_0%,rgba(124,58,237,0.08),transparent)]" />

      <div className="pt-24 pb-16 px-6 min-h-screen flex flex-col items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-3xl"
        >
          {/* Header */}
          <div className="text-center mb-8">
            <p className="font-display text-[10px] uppercase tracking-widest text-violet-400 mb-2">
              New Project
            </p>
            <h1 className="font-display font-black text-4xl text-white">Create Your Film</h1>
          </div>

          <StepIndicator current={step} />

          {/* Step content */}
          <div className="glass rounded-2xl p-8 min-h-[360px] flex flex-col">
            <AnimatePresence>
              <motion.div
                key={step}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="flex flex-col flex-1 gap-6"
              >

              {/* ── STEP 0: Prompt ── */}
              {step === 0 && (<>
                  <label className="font-display text-xs uppercase tracking-widest text-violet-400">
                    Your Story Idea
                  </label>
                  <div className="relative">
                    <textarea
                      value={prompt}
                      onChange={e => setPrompt(e.target.value)}
                      placeholder={PLACEHOLDERS[phIdx]}
                      rows={5}
                      className="w-full bg-background border border-border rounded-xl px-5 py-4
                                 text-white placeholder-slate-600 font-body text-base resize-none
                                 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/50
                                 transition-all outline-none leading-relaxed"
                    />
                    <span className="absolute bottom-3 right-4 font-display text-[10px] text-slate-600">
                      {prompt.length} / 500
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs -mt-2">
                    Be specific — include emotion, setting, or conflict for richer stories.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {PLACEHOLDERS.slice(0,3).map(p => (
                      <button key={p}
                        onClick={() => setPrompt(p.replace('...',''))}
                        className="px-3 py-1.5 rounded-full border border-border bg-surface text-xs
                                   text-slate-400 hover:border-violet-500/50 hover:text-violet-300
                                   transition-all font-body truncate max-w-[220px]">
                        {p.slice(0,30)}…
                      </button>
                    ))}
                  </div>
              </>)}

              {/* ── STEP 1: Style ── */}
              {step === 1 && (<>
                  <label className="font-display text-xs uppercase tracking-widest text-violet-400">
                    Visual Style
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {STYLES.map(s => (
                      <motion.button
                        key={s.id}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => setStyle(s.id)}
                        className={`relative p-5 rounded-xl border-2 transition-all duration-200 text-left
                          ${style === s.id
                            ? `${glowMap[s.glow]} border-2`
                            : 'border-border bg-background hover:border-border-bright'}`}
                      >
                        <span className={`material-symbols-outlined text-3xl mb-3 block
                          ${style === s.id ? iconColorMap[s.glow] : 'text-slate-500'}`}>
                          {s.icon}
                        </span>
                        <p className={`font-display font-semibold text-sm
                          ${style === s.id ? 'text-white' : 'text-slate-400'}`}>
                          {s.label}
                        </p>
                        {style === s.id && (
                          <motion.div
                            layoutId="style-check"
                            className="absolute top-3 right-3 w-5 h-5 rounded-full
                                       bg-violet-600 flex items-center justify-center"
                          >
                            <span className="material-symbols-outlined text-white text-[14px]">check</span>
                          </motion.div>
                        )}
                      </motion.button>
                    ))}
                  </div>
              </>)}

              {/* ── STEP 2: Settings ── */}
              {step === 2 && (<>
                  <div>
                    <label className="font-display text-xs uppercase tracking-widest text-violet-400 mb-3 block">
                      Duration
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {DURATIONS.map(d => (
                        <motion.button
                          key={d.id}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={() => setDuration(d.id)}
                          className={`p-4 rounded-xl border-2 text-left transition-all
                            ${duration === d.id
                              ? 'border-violet-500 bg-violet-600/10 shadow-[0_0_15px_rgba(124,58,237,0.3)]'
                              : 'border-border bg-background hover:border-border-bright'}`}
                        >
                          <span className={`material-symbols-outlined text-2xl mb-2 block
                            ${duration === d.id ? 'text-violet-400' : 'text-slate-500'}`}>{d.icon}</span>
                          <p className={`font-display font-bold text-sm
                            ${duration === d.id ? 'text-white' : 'text-slate-400'}`}>{d.label}</p>
                          <p className="text-slate-500 text-xs mt-0.5">{d.sub}</p>
                        </motion.button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="font-display text-xs uppercase tracking-widest text-violet-400 mb-3 block">
                      Language
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {LANGUAGES.map(l => (
                        <button key={l}
                          onClick={() => setLanguage(l)}
                          className={`px-4 py-2 rounded-full border font-display text-xs font-bold tracking-wider transition-all
                            ${language === l
                              ? 'border-violet-500 bg-violet-600/20 text-violet-300'
                              : 'border-border text-slate-500 hover:border-border-bright hover:text-slate-300'}`}>
                          {l}
                        </button>
                      ))}
                    </div>
                  </div>
              </>)}

              {/* ── STEP 3: Confirm ── */}
              {step === 3 && (<>
                  <label className="font-display text-xs uppercase tracking-widest text-violet-400">
                    Review &amp; Generate
                  </label>
                  <div className="space-y-3">
                    {[
                      { label: 'Prompt',   value: prompt.slice(0,80) + (prompt.length > 80 ? '…' : ''), icon: 'edit_note' },
                      { label: 'Style',    value: style,    icon: 'palette' },
                      { label: 'Duration', value: duration, icon: 'timer' },
                      { label: 'Language', value: language, icon: 'language' },
                    ].map(row => (
                      <div key={row.label}
                        className="flex items-center gap-4 p-4 bg-background rounded-xl border border-border">
                        <span className="material-symbols-outlined text-violet-400 text-[20px]">{row.icon}</span>
                        <div className="flex-1">
                          <p className="font-display text-[10px] uppercase tracking-widest text-slate-500">{row.label}</p>
                          <p className="text-white text-sm mt-0.5">{row.value || '—'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="p-4 bg-violet-600/10 border border-violet-500/30 rounded-xl">
                    <p className="text-violet-300 text-sm">
                      Generation takes <strong>2–5 minutes</strong>. All 4 phases run automatically.
                      You can watch live progress on the next screen.
                    </p>
                  </div>
              </>)}

              </motion.div>
            </AnimatePresence>

            {/* Navigation */}
            <div className="flex justify-between mt-auto pt-8">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => step > 0 ? setStep(s => s - 1) : navigate('/')}
                className="px-6 py-3 rounded-xl border border-border text-slate-400
                           hover:text-white hover:border-border-bright transition-colors
                           font-display font-bold text-sm flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">arrow_back</span>
                {step === 0 ? 'Home' : 'Back'}
              </motion.button>

              {step < 3 ? (
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => setStep(s => s + 1)}
                  disabled={step === 0 && !prompt.trim()}
                  className="px-8 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600
                             text-white font-display font-bold text-sm flex items-center gap-2
                             disabled:opacity-40 disabled:cursor-not-allowed
                             shadow-[0_0_15px_rgba(124,58,237,0.3)]"
                >
                  Continue
                  <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                </motion.button>
              ) : (
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={handleGenerate}
                  disabled={loading}
                  className="px-8 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600
                             text-white font-display font-bold text-sm flex items-center gap-2
                             shadow-[0_0_25px_rgba(124,58,237,0.5)] animate-pulse-glow
                             disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <motion.span
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="material-symbols-outlined text-[18px]">sync</motion.span>
                      Launching…
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[18px] icon-fill">auto_awesome</span>
                      GENERATE FILM
                    </>
                  )}
                </motion.button>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
