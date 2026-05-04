import { motion } from 'framer-motion'

/**
 * Cinematic projector beam — adapted from the Aceternity "Lamp" component.
 * Colors match the app's violet/indigo palette. Background `#0a0a0f` matches
 * the site background so the masking divs blend seamlessly.
 *
 * Usage: place as a direct child inside a `relative overflow-hidden` container.
 * It renders absolutely positioned and is pointer-events-none, so it never
 * blocks clicks on content layered above it.
 */
export function ProjectorBeam({ className = '' }) {
  return (
    <div
      className={`absolute inset-0 z-0 pointer-events-none overflow-hidden ${className}`}
    >
      {/* scale-y-125 stretches the effect vertically for a more dramatic sweep */}
      <div className="relative flex w-full h-full scale-y-125 items-center justify-center isolate">

        {/* ── Left conic beam ─────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0.4, width: '12rem' }}
          whileInView={{ opacity: 1, width: '30rem' }}
          transition={{ delay: 0.3, duration: 1.0, ease: 'easeInOut' }}
          style={{
            backgroundImage: `conic-gradient(var(--conic-position), var(--tw-gradient-stops))`,
          }}
          className="absolute inset-auto right-1/2 h-56 overflow-visible w-[30rem]
                     bg-gradient-conic from-violet-600 via-transparent to-transparent
                     [--conic-position:from_70deg_at_center_top]"
        >
          {/* Bottom fade — hides the base of the cone */}
          <div className="absolute w-full left-0 bg-background h-40 bottom-0 z-20
                          [mask-image:linear-gradient(to_top,white,transparent)]" />
          {/* Left edge fade */}
          <div className="absolute w-40 h-full left-0 bg-background bottom-0 z-20
                          [mask-image:linear-gradient(to_right,white,transparent)]" />
        </motion.div>

        {/* ── Right conic beam ────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0.4, width: '12rem' }}
          whileInView={{ opacity: 1, width: '30rem' }}
          transition={{ delay: 0.3, duration: 1.0, ease: 'easeInOut' }}
          style={{
            backgroundImage: `conic-gradient(var(--conic-position), var(--tw-gradient-stops))`,
          }}
          className="absolute inset-auto left-1/2 h-56 w-[30rem]
                     bg-gradient-conic from-transparent via-transparent to-violet-600
                     [--conic-position:from_290deg_at_center_top]"
        >
          {/* Right edge fade */}
          <div className="absolute w-40 h-full right-0 bg-background bottom-0 z-20
                          [mask-image:linear-gradient(to_left,white,transparent)]" />
          {/* Bottom fade */}
          <div className="absolute w-full right-0 bg-background h-40 bottom-0 z-20
                          [mask-image:linear-gradient(to_top,white,transparent)]" />
        </motion.div>

        {/* ── Bottom fog — hides lower artifacts ──────────── */}
        <div className="absolute top-1/2 h-48 w-full translate-y-12 scale-x-150 bg-background blur-2xl" />

        {/* ── Subtle backdrop blur at beam centre ─────────── */}
        <div className="absolute top-1/2 z-50 h-48 w-full opacity-10 backdrop-blur-md" />

        {/* ── Wide ambient glow blob ───────────────────────── */}
        <div className="absolute inset-auto z-50 h-36 w-[28rem] -translate-y-1/2
                        rounded-full bg-violet-600 opacity-40 blur-3xl" />

        {/* ── Tight hot-spot glow ──────────────────────────── */}
        <motion.div
          initial={{ width: '6rem' }}
          whileInView={{ width: '14rem' }}
          transition={{ delay: 0.3, duration: 1.0, ease: 'easeInOut' }}
          className="absolute inset-auto z-30 h-36 w-56 -translate-y-24
                     rounded-full bg-violet-500 blur-2xl opacity-70"
        />

        {/* ── Bright apex line (the "projector lens") ─────── */}
        <motion.div
          initial={{ width: '12rem', opacity: 0 }}
          whileInView={{ width: '30rem', opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.9, ease: 'easeInOut' }}
          className="absolute inset-auto z-50 h-px w-[30rem] -translate-y-[7rem]
                     bg-gradient-to-r from-transparent via-violet-400 to-transparent"
        />

        {/* ── Top cover — masks everything above the beam ─── */}
        <div className="absolute inset-auto z-40 h-44 w-full -translate-y-[12.5rem] bg-background" />
      </div>
    </div>
  )
}
