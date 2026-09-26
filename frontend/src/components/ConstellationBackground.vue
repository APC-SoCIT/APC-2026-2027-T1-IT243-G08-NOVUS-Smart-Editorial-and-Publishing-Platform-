<script setup>
/*
 * Constellation background: points drift slowly and join with faint lines
 * when they pass near each other, echoing the network in the wireframe.
 *
 * Written against a plain canvas rather than a particle library: it needs
 * one effect, a library would ship dozens. It stops when the tab is hidden,
 * draws a single still frame when the viewer has asked for reduced motion,
 * and scales for high-density screens without drawing more than it must.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  density: { type: Number, default: 9000 },   // screen pixels per point
  maxPoints: { type: Number, default: 110 },
  linkDistance: { type: Number, default: 150 },
})

const canvas = ref(null)
let ctx, raf = 0, points = [], w = 0, h = 0, dpr = 1, ro
const pointer = { x: -9999, y: -9999 }
const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function seed() {
  const n = Math.min(props.maxPoints, Math.round((w * h) / props.density))
  points = Array.from({ length: n }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.22,
    vy: (Math.random() - 0.5) * 0.22,
    r: Math.random() < 0.12 ? 2.2 + Math.random() * 1.4 : 0.8 + Math.random() * 1.2,
  }))
}

function resize() {
  const box = canvas.value.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = box.width; h = box.height
  canvas.value.width = Math.round(w * dpr)
  canvas.value.height = Math.round(h * dpr)
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  seed()
  draw()
}

function draw() {
  ctx.clearRect(0, 0, w, h)
  const L = props.linkDistance, L2 = L * L

  for (let i = 0; i < points.length; i++) {
    const a = points[i]
    for (let j = i + 1; j < points.length; j++) {
      const b = points[j]
      const dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy
      if (d2 < L2) {
        ctx.strokeStyle = `rgba(130, 165, 235, ${(1 - Math.sqrt(d2) / L) * 0.32})`
        ctx.lineWidth = 0.7
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke()
      }
    }
    // A faint reach toward the pointer, so the panel answers the viewer.
    const px = a.x - pointer.x, py = a.y - pointer.y, p2 = px * px + py * py
    if (p2 < L2 * 1.4) {
      ctx.strokeStyle = `rgba(170, 200, 255, ${(1 - Math.sqrt(p2) / (L * 1.18)) * 0.35})`
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(pointer.x, pointer.y); ctx.stroke()
    }
  }

  for (const p of points) {
    if (p.r > 2) {
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5)
      g.addColorStop(0, 'rgba(190, 215, 255, 0.35)')
      g.addColorStop(1, 'rgba(190, 215, 255, 0)')
      ctx.fillStyle = g
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 5, 0, Math.PI * 2); ctx.fill()
    }
    ctx.fillStyle = 'rgba(205, 222, 255, 0.85)'
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill()
  }
}

function step() {
  for (const p of points) {
    p.x += p.vx; p.y += p.vy
    if (p.x < -20) p.x = w + 20; else if (p.x > w + 20) p.x = -20
    if (p.y < -20) p.y = h + 20; else if (p.y > h + 20) p.y = -20
  }
  draw()
  raf = requestAnimationFrame(step)
}

function start() { if (!still && !raf) raf = requestAnimationFrame(step) }
function stop() { cancelAnimationFrame(raf); raf = 0 }
function onVisibility() { document.hidden ? stop() : start() }
function onMove(e) {
  const box = canvas.value.getBoundingClientRect()
  pointer.x = e.clientX - box.left; pointer.y = e.clientY - box.top
}
function onLeave() { pointer.x = pointer.y = -9999 }

onMounted(() => {
  ctx = canvas.value.getContext('2d')
  ro = new ResizeObserver(resize)
  ro.observe(canvas.value)
  document.addEventListener('visibilitychange', onVisibility)
  canvas.value.parentElement.addEventListener('pointermove', onMove)
  canvas.value.parentElement.addEventListener('pointerleave', onLeave)
  start()
})

onBeforeUnmount(() => {
  stop(); ro?.disconnect()
  document.removeEventListener('visibilitychange', onVisibility)
  canvas.value?.parentElement?.removeEventListener('pointermove', onMove)
  canvas.value?.parentElement?.removeEventListener('pointerleave', onLeave)
})
</script>

<template>
  <canvas ref="canvas" class="constellation" aria-hidden="true"></canvas>
</template>

<style scoped>
.constellation { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
</style>
