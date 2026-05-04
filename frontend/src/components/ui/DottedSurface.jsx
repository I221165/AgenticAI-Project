import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { cn } from '../../lib/utils.js'

/**
 * DottedSurface — animated Three.js sine-wave particle grid.
 *
 * Adapted for the dark `#0a0a0f` background:
 *   • Dots are violet-400 (#a78bfa) at 55% opacity
 *   • Fog fades distant dots toward the page background so they disappear
 *     naturally instead of clipping hard
 *   • No next-themes dependency — always renders for dark mode
 *   • Canvas is sized to the container element (not window) so it works
 *     both as `fixed inset-0` and `absolute inset-0`
 */
export function DottedSurface({ className, ...props }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const SEPARATION = 150
    const AMOUNTX   = 40
    const AMOUNTY   = 60

    // ── Scene ────────────────────────────────────────────────
    const scene = new THREE.Scene()
    // Fog color matches the page background so far particles fade out cleanly
    scene.fog = new THREE.Fog(0x0a0a0f, 2500, 9000)

    // ── Camera ───────────────────────────────────────────────
    const w = container.offsetWidth  || window.innerWidth
    const h = container.offsetHeight || window.innerHeight

    const camera = new THREE.PerspectiveCamera(60, w / h, 1, 10000)
    camera.position.set(0, 355, 1220)

    // ── Renderer ─────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setSize(w, h)
    renderer.setClearColor(0x000000, 0)   // transparent canvas background

    container.appendChild(renderer.domElement)

    // ── Geometry ─────────────────────────────────────────────
    const positions = []
    const colors    = []

    for (let ix = 0; ix < AMOUNTX; ix++) {
      for (let iy = 0; iy < AMOUNTY; iy++) {
        positions.push(
          ix * SEPARATION - (AMOUNTX * SEPARATION) / 2,
          0,
          iy * SEPARATION - (AMOUNTY * SEPARATION) / 2,
        )
        // violet-400 #a78bfa → 167/255, 139/255, 250/255
        colors.push(0.655, 0.545, 0.980)
      }
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geometry.setAttribute('color',    new THREE.Float32BufferAttribute(colors, 3))

    const material = new THREE.PointsMaterial({
      size: 6,
      vertexColors: true,
      transparent: true,
      opacity: 0.55,
      sizeAttenuation: true,
    })

    const points = new THREE.Points(geometry, material)
    scene.add(points)

    // ── Animation ─────────────────────────────────────────────
    let count = 0
    const raf = { id: null }

    const animate = () => {
      raf.id = requestAnimationFrame(animate)

      const posAttr = geometry.attributes.position
      const pos     = posAttr.array
      let i = 0

      for (let ix = 0; ix < AMOUNTX; ix++) {
        for (let iy = 0; iy < AMOUNTY; iy++) {
          pos[i * 3 + 1] =
            Math.sin((ix + count) * 0.3) * 50 +
            Math.sin((iy + count) * 0.5) * 50
          i++
        }
      }

      posAttr.needsUpdate = true
      renderer.render(scene, camera)
      count += 0.1
    }

    // ── Resize ────────────────────────────────────────────────
    const handleResize = () => {
      const nw = container.offsetWidth  || window.innerWidth
      const nh = container.offsetHeight || window.innerHeight
      camera.aspect = nw / nh
      camera.updateProjectionMatrix()
      renderer.setSize(nw, nh)
    }

    window.addEventListener('resize', handleResize)
    animate()

    // ── Cleanup ───────────────────────────────────────────────
    return () => {
      window.removeEventListener('resize', handleResize)
      if (raf.id) cancelAnimationFrame(raf.id)

      scene.traverse((obj) => {
        if (obj instanceof THREE.Points) {
          obj.geometry.dispose()
          if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose())
          else obj.material.dispose()
        }
      })

      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className={cn('pointer-events-none', className)}
      {...props}
    />
  )
}
