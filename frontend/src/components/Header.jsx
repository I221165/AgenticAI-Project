import { motion } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'

const navLinks = [
  { label: 'HOME',    path: '/' },
  { label: 'STUDIO',  path: '/create' },
  { label: 'GALLERY', path: '/gallery' },
]

export default function Header() {
  const navigate  = useNavigate()
  const location  = useLocation()

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="fixed top-0 w-full z-50 flex justify-between items-center px-6 h-16
                 bg-background/80 backdrop-blur-xl border-b border-border
                 shadow-[0_0_15px_rgba(124,58,237,0.08)]"
    >
      {/* Logo */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 group"
        >
          {/* Animated logo mark */}
          <motion.div
            className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center"
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <span className="material-symbols-outlined text-white text-[18px] icon-fill">movie_filter</span>
          </motion.div>
          <span className="text-lg font-display font-black tracking-widest text-gradient">
            STORYFORGE AI
          </span>
        </button>
      </div>

      {/* Desktop Nav */}
      <nav className="hidden md:flex gap-8 items-center">
        {navLinks.map(link => (
          <button
            key={link.path}
            onClick={() => navigate(link.path)}
            className="relative font-display text-xs font-bold tracking-widest transition-colors
                       group"
          >
            <span className={location.pathname === link.path
              ? 'text-violet-400'
              : 'text-slate-400 hover:text-white transition-colors'}>
              {link.label}
            </span>
            {location.pathname === link.path && (
              <motion.div
                layoutId="nav-indicator"
                className="absolute -bottom-1 left-0 right-0 h-0.5 bg-gradient-to-r from-violet-500 to-blue-500 rounded-full"
              />
            )}
          </button>
        ))}
      </nav>

      {/* Right side */}
      <div className="flex items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/create')}
          className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full
                     bg-gradient-to-r from-violet-600 to-blue-600 text-white
                     font-display font-bold text-xs tracking-wider
                     shadow-[0_0_15px_rgba(124,58,237,0.3)]"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          NEW FILM
        </motion.button>

        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-blue-600
                        flex items-center justify-center font-display font-bold text-xs cursor-pointer">
          H
        </div>
      </div>
    </motion.header>
  )
}
