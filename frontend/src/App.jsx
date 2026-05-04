import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import LandingPage   from './pages/LandingPage.jsx'
import CreatePage    from './pages/CreatePage.jsx'
import ProgressPage  from './pages/ProgressPage.jsx'
import StudioPage    from './pages/StudioPage.jsx'
import GalleryPage   from './pages/GalleryPage.jsx'

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/"                       element={<LandingPage />} />
        <Route path="/create"                 element={<CreatePage />} />
        <Route path="/progress/:runId"        element={<ProgressPage />} />
        <Route path="/studio/:runId"          element={<StudioPage />} />
        <Route path="/gallery"               element={<GalleryPage />} />
      </Routes>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      {/* Global scan-line decoration */}
      <div className="scan-line" />
      <AnimatedRoutes />
    </BrowserRouter>
  )
}
