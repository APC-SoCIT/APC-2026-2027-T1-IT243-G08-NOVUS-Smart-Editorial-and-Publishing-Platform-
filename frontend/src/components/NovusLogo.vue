<script setup>
/*
 * The NOVUS logo, inlined so it takes its colour from the surrounding text:
 * white on the login panel and the sidebar, whatever either theme needs.
 * variant="mark" gives the pen and star alone, for tight spaces. Set
 * decorative when the surrounding link already names the destination, so
 * screen readers don't hear "NOVUS" twice.
 */
import full from '../assets/brand/novus-logo.svg?raw'
import mark from '../assets/brand/novus-mark.svg?raw'

defineProps({
  variant: { type: String, default: 'full' },
  decorative: { type: Boolean, default: false },
})
</script>

<template>
  <span class="novus-logo" :class="variant" :aria-hidden="decorative ? 'true' : undefined"
        v-html="variant === 'mark' ? mark : full"></span>
</template>

<style scoped>
.novus-logo { display: inline-flex; line-height: 0; color: inherit; }
.novus-logo :deep(svg) { display: block; width: 100%; height: auto; }
</style>
