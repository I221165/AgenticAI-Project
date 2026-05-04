import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header.jsx'
import { BackgroundPaths } from '../components/ui/BackgroundPaths.jsx'
import { LiquidButton } from '../components/ui/LiquidButton.jsx'
import { GooeyText } from '../components/ui/GooeyText.jsx'

/* ── Stagger helpers ────────────────────────────────────── */
const container = { hidden: {}, show: { transition: { staggerChildren: 0.12 } } }
const fadeUp     = { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' } } }
const fadeIn     = { hidden: { opacity: 0 },        show: { opacity: 1, transition: { duration: 0.8 } } }

/* ── Words cycled by the gooey morph ─────────────────────── */
const words = ['animated film', 'epic story', 'short movie', 'cinematic world']

/* ── Feature pills ──────────────────────────────────────── */
const features = [
  { icon: 'edit_note',        label: 'AI Story Writing' },
  { icon: 'record_voice_over',label: 'Voice Synthesis' },
  { icon: 'movie_filter',     label: 'Auto Animation' },
  { icon: 'music_note',       label: 'Smart BGM' },
  { icon: 'subtitles',        label: 'Auto Subtitles' },
]

/* ── Bento cards ────────────────────────────────────────── */
const bentoItems = [
  {
    cols: 'md:col-span-2', accent: 'violet',
    tag: 'ENGINE CORE', title: 'Neural Directing',
    body: 'Our AI understands cinematography. Ken Burns zooms, scene transitions, tone-aware camera — your story gets a real director.',
    icon: 'movie',
  },
  {
    cols: '', accent: 'blue',
    tag: 'AUDIO LOGIC', title: 'Spatial Sound',
    body: 'Layered voice synthesis, mood-matched BGM, and emotion-aware gaps that sync to every line.',
    icon: 'graphic_eq',
  },
  {
    cols: '', accent: 'emerald',
    tag: 'RENDERING', title: 'MP4 Export',
    body: 'H.264 output with burned subtitles, audio overlay, and xfade scene transitions.',
    icon: 'download',
  },
  {
    cols: 'md:col-span-2', accent: 'amber',
    tag: 'EDIT SYSTEM', title: 'Intelligent Editing',
    body: 'Tell the AI "make Ethan\'s voice darker" or "redo scene 3 in anime style" — it classifies your intent and re-runs only what\'s needed.',
    icon: 'auto_fix_high',
  },
]

/* ── Page wrapper ──────────────────────────────────────── */
export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-background"
    >
      <Header />

      {/* ── HERO ──────────────────────────────── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center pt-16 overflow-hidden">
        {/* Flowing path lines background */}
        <BackgroundPaths />

        {/* Subtle radial accent underneath content */}
        <div className="absolute inset-0 z-0 pointer-events-none
                        bg-[radial-gradient(ellipse_60%_40%_at_50%_40%,rgba(124,58,237,0.10)_0%,transparent_70%)]" />

        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="relative z-10 container mx-auto px-6 text-center max-w-5xl"
        >
          {/* Badge */}
          <motion.div variants={fadeUp} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
            bg-violet-500/10 border border-violet-500/30 mb-8">
            <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
            <span className="font-display text-violet-300 text-[10px] uppercase tracking-widest">
              Agentic AI · Phase 1–5 Pipeline
            </span>
          </motion.div>

          {/* Headline — whileInView fade-up, same pattern as the lamp demo */}
          <motion.h1
            initial={{ opacity: 0.4, y: 60 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ delay: 0.3, duration: 0.9, ease: 'easeInOut' }}
            className="font-display font-black text-5xl md:text-7xl leading-[1.08] tracking-tighter text-white mb-2"
          >
            Turn any idea into an
          </motion.h1>

          {/* Gooey morphing word — replaces the old slide-up cycling word */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.8 }}
            className="mb-6"
          >
            <GooeyText
              texts={words}
              morphTime={1.5}
              cooldownTime={0.6}
              className="h-[56px] md:h-[88px] w-full"
              textClassName="font-display font-black text-5xl md:text-7xl tracking-tighter text-violet-400"
            />
          </motion.div>

          {/* Sub */}
          <motion.p variants={fadeUp}
            className="text-lg text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Type a story. StoryForge AI writes the script, voices the characters,
            animates every scene, and exports a finished MP4 — all autonomously.
          </motion.p>

          {/* CTAs */}
          <motion.div variants={fadeUp} className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <LiquidButton
              onClick={() => navigate('/create')}
              className="px-10 py-4 rounded-full bg-gradient-to-r from-violet-600 to-blue-600
                         font-display font-bold text-sm tracking-widest text-white
                         shadow-[0_0_30px_rgba(124,58,237,0.5)] animate-pulse-glow
                         flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[20px] icon-fill">auto_awesome</span>
              CREATE YOUR FILM
            </LiquidButton>
            <LiquidButton
              className="px-10 py-4 rounded-full border border-border bg-surface
                         font-display font-bold text-sm tracking-widest text-slate-300
                         hover:border-violet-500/40 hover:text-white transition-colors"
            >
              EXPLORE SHOWCASE
            </LiquidButton>
          </motion.div>

          {/* Feature pills */}
          <motion.div variants={container} className="flex flex-wrap justify-center gap-3 mb-20">
            {features.map((f, i) => (
              <motion.div
                key={f.label}
                variants={fadeUp}
                whileHover={{ y: -3, borderColor: 'rgba(124,58,237,0.5)' }}
                className="flex items-center gap-2 px-4 py-2 bg-surface border border-border
                           rounded-xl cursor-default transition-colors"
              >
                <span className="material-symbols-outlined text-violet-400 text-[18px]">{f.icon}</span>
                <span className="font-display text-xs font-semibold text-slate-300">{f.label}</span>
              </motion.div>
            ))}
          </motion.div>

          {/* Demo preview card */}
          <motion.div
            variants={fadeIn}
            whileHover={{ scale: 1.01 }}
            className="relative max-w-4xl mx-auto rounded-2xl overflow-hidden border border-border
                       bg-surface shadow-2xl shadow-violet-900/20"
          >
            {/* Gradient overlay on demo */}
            <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent z-10 pointer-events-none" />
            <div className="aspect-video bg-gradient-to-br from-violet-900/30 via-background to-blue-900/20
                            flex items-center justify-center relative">
              {/* Simulated pipeline steps */}
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-8">
                {['Story', 'Audio', 'Video'].map((step, i) => (
                  <motion.div
                    key={step}
                    initial={{ width: '0%', opacity: 0 }}
                    animate={{ width: ['0%', '100%'], opacity: 1 }}
                    transition={{ delay: 1 + i * 0.8, duration: 1.2, ease: 'easeOut' }}
                    className="w-full max-w-sm"
                  >
                    <div className="flex justify-between mb-1">
                      <span className="font-display text-[10px] text-slate-400 uppercase tracking-widest">Phase {i+1} — {step}</span>
                      <span className="font-display text-[10px] text-violet-400">✓ Done</span>
                    </div>
                    <div className="h-1 bg-border rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: '0%' }}
                        animate={{ width: '100%' }}
                        transition={{ delay: 1 + i * 0.8, duration: 1.2, ease: 'easeOut' }}
                        className="h-full bg-gradient-to-r from-violet-600 to-blue-500 rounded-full"
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
              {/* Play button overlay */}
              <motion.button
                className="relative z-20 w-16 h-16 rounded-full border border-violet-500/50
                           bg-violet-600/20 backdrop-blur-md flex items-center justify-center
                           hover:bg-violet-600/40 transition-colors mt-24"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
              >
                <span className="material-symbols-outlined text-white text-4xl icon-fill">play_arrow</span>
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* ── BENTO GRID ────────────────────────── */}
      <section className="py-24 px-6 relative z-10">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <p className="font-display text-[10px] uppercase tracking-widest text-violet-400 mb-3">What it does</p>
            <h2 className="font-display font-bold text-4xl text-white">Every phase, automated.</h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {bentoItems.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                whileHover={{ y: -4, borderColor: `rgba(124,58,237,0.35)` }}
                className={`${item.cols} bg-surface border border-border rounded-2xl p-8
                            transition-colors duration-300 cursor-default group overflow-hidden relative`}
              >
                {/* Subtle background glow on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-violet-600/0 to-blue-600/0
                                group-hover:from-violet-600/5 group-hover:to-blue-600/5 transition-all duration-500" />
                <div className="relative z-10">
                  <div className={`w-10 h-10 rounded-xl mb-5 flex items-center justify-center
                    ${item.accent === 'violet' ? 'bg-violet-600/20' :
                      item.accent === 'blue'   ? 'bg-blue-600/20'   :
                      item.accent === 'emerald'? 'bg-emerald-600/20' : 'bg-amber-600/20'}`}>
                    <span className={`material-symbols-outlined text-[20px]
                      ${item.accent === 'violet' ? 'text-violet-400' :
                        item.accent === 'blue'   ? 'text-blue-400'   :
                        item.accent === 'emerald'? 'text-emerald-400' : 'text-amber-400'}`}>
                      {item.icon}
                    </span>
                  </div>
                  <p className={`font-display text-[10px] uppercase tracking-widest mb-2
                    ${item.accent === 'violet' ? 'text-violet-400' :
                      item.accent === 'blue'   ? 'text-blue-400'   :
                      item.accent === 'emerald'? 'text-emerald-400' : 'text-amber-400'}`}>
                    {item.tag}
                  </p>
                  <h3 className="font-display font-semibold text-2xl text-white mb-3">{item.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{item.body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────── */}
      <section className="py-24 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(124,58,237,0.08)_0%,transparent_70%)]" />
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="container mx-auto max-w-2xl text-center relative z-10"
        >
          <h2 className="font-display font-bold text-4xl text-white mb-6">Ready to tell your story?</h2>
          <p className="text-slate-400 mb-10">One prompt. Four AI phases. One finished film.</p>
          <LiquidButton
            onClick={() => navigate('/create')}
            className="px-14 py-5 rounded-full bg-gradient-to-r from-violet-600 to-blue-600
                       font-display font-bold text-sm tracking-widest text-white
                       shadow-[0_0_40px_rgba(124,58,237,0.5)]"
          >
            GET STARTED FREE
          </LiquidButton>
        </motion.div>
      </section>

      {/* ── FOOTER ─────────────────────────────── */}
      <footer className="py-10 border-t border-border bg-background px-6">
        <div className="container mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <span className="font-display font-black text-sm tracking-widest text-gradient">STORYFORGE AI</span>
          <div className="flex gap-8 font-display text-[10px] tracking-widest text-slate-500">
            {['PRIVACY','TERMS','API','SUPPORT'].map(l => (
              <a key={l} href="#" className="hover:text-white transition-colors">{l}</a>
            ))}
          </div>
          <span className="font-display text-[10px] tracking-widest text-slate-600">
            © 2026 STORYFORGE LABS
          </span>
        </div>
      </footer>
    </motion.div>
  )
}
