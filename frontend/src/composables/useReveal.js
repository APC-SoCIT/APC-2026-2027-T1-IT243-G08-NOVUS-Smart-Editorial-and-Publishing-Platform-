import { onMounted, onUnmounted } from 'vue'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

/**
 * Reveals elements as they enter the viewport.
 *
 * Respects prefers-reduced-motion: anyone who has asked their system for less
 * animation gets the content immediately and fully visible. Content is never
 * hidden behind an animation that might not run.
 */
export function useReveal(selector = '[data-reveal]', options = {}) {
  let ctx

  onMounted(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    ctx = gsap.context(() => {
      gsap.utils.toArray(selector).forEach((el, i) => {
        gsap.from(el, {
          opacity: 0,
          y: options.y ?? 24,
          duration: options.duration ?? 0.7,
          ease: 'power2.out',
          delay: (i % 3) * 0.06,
          scrollTrigger: { trigger: el, start: 'top 88%', once: true },
        })
      })
    })
  })

  onUnmounted(() => {
    ctx?.revert()
    ScrollTrigger.getAll().forEach(t => t.kill())
  })
}

/** A single element fading up on mount — for page headers. */
export function useIntro(selector, options = {}) {
  onMounted(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    gsap.from(selector, {
      opacity: 0,
      y: options.y ?? 18,
      duration: options.duration ?? 0.8,
      ease: 'power3.out',
      stagger: options.stagger ?? 0.08,
    })
  })
}
