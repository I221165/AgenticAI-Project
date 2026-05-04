import { forwardRef } from 'react'
import { cn } from '../../lib/utils.js'

function GlassFilter() {
  return (
    <svg className="absolute hidden" aria-hidden="true">
      <defs>
        <filter id="liquid-glass" x="0%" y="0%" width="100%" height="100%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.05 0.05" numOctaves="1" seed="1" result="turbulence" />
          <feGaussianBlur in="turbulence" stdDeviation="2" result="blurredNoise" />
          <feDisplacementMap in="SourceGraphic" in2="blurredNoise" scale="70" xChannelSelector="R" yChannelSelector="B" result="displaced" />
          <feGaussianBlur in="displaced" stdDeviation="4" result="finalBlur" />
          <feComposite in="finalBlur" in2="finalBlur" operator="over" />
        </filter>
      </defs>
    </svg>
  )
}

const LiquidButton = forwardRef(function LiquidButton({ className = '', children, ...props }, ref) {
  return (
    <button
      ref={ref}
      className={cn(
        'relative hover:scale-105 active:scale-95 transition-transform duration-300',
        className
      )}
      {...props}
    >
      <div
        className="absolute inset-0 z-0 rounded-[inherit] pointer-events-none transition-all
          shadow-[0_0_8px_rgba(0,0,0,0.03),
                  0_2px_6px_rgba(0,0,0,0.08),
                  inset_3px_3px_0.5px_-3.5px_rgba(255,255,255,0.09),
                  inset_-3px_-3px_0.5px_-3.5px_rgba(255,255,255,0.85),
                  inset_1px_1px_1px_-0.5px_rgba(255,255,255,0.6),
                  inset_-1px_-1px_1px_-0.5px_rgba(255,255,255,0.6),
                  inset_0_0_6px_6px_rgba(255,255,255,0.12),
                  inset_0_0_2px_2px_rgba(255,255,255,0.06),
                  0_0_12px_rgba(0,0,0,0.15)]"
      />
      <div
        className="absolute inset-0 -z-10 rounded-[inherit] overflow-hidden pointer-events-none"
        style={{ backdropFilter: 'url("#liquid-glass")' }}
      />
      <div className="relative z-10 flex items-center justify-center gap-2 pointer-events-none">
        {children}
      </div>
      <GlassFilter />
    </button>
  )
})

LiquidButton.displayName = 'LiquidButton'

export { LiquidButton }
