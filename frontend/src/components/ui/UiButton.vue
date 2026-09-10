<script setup>
defineProps({
  variant: { type: String, default: 'ghost' },  // primary | ghost | danger | warn | quiet
  size: { type: String, default: 'md' },        // sm | md | lg
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  full: { type: Boolean, default: false },
  /* Required when the button shows only an icon — otherwise it is unlabelled
     to a screen reader. */
  label: { type: String, default: '' },
})
</script>

<template>
  <button :class="['btn', variant, size, { full, loading }]"
          :disabled="disabled || loading"
          :aria-label="label || undefined"
          :aria-busy="loading">
    <span v-if="loading" class="spin" aria-hidden="true"></span>
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: var(--s-2);
  border-radius: var(--r-sm);
  font-family: var(--font-ui); font-weight: 600;
  cursor: pointer; white-space: nowrap;
  border: 1px solid transparent;
  transition: background var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out),
              color var(--dur-fast) var(--ease-out),
              transform var(--dur-fast) var(--ease-out);
}
.btn:active:not(:disabled) { transform: translateY(1px); }
.btn:disabled { opacity: .45; cursor: not-allowed; }

.sm { padding: var(--s-2) var(--s-3); font-size: var(--t-xs); }
.md { padding: var(--s-3) var(--s-4); font-size: var(--t-sm); }
.lg { padding: var(--s-4) var(--s-6); font-size: var(--t-base); }
.full { width: 100%; }

.primary { background: var(--nv-navy-2); color: #fff; border-color: var(--nv-navy-2); }
.primary:hover:not(:disabled) { background: var(--nv-navy-3); border-color: var(--nv-navy-3); }

.ghost { background: var(--nv-surface); color: var(--nv-text);
         border-color: var(--nv-line-strong); }
.ghost:hover:not(:disabled) { background: var(--nv-bg); border-color: var(--nv-text-faint); }

.danger { background: var(--bad); color: #fff; border-color: var(--bad); }
.danger:hover:not(:disabled) { filter: brightness(1.1); }

.warn { background: var(--warn); color: #fff; border-color: var(--warn); }
.warn:hover:not(:disabled) { filter: brightness(1.1); }

.quiet { background: transparent; color: var(--nv-accent); border-color: transparent;
         font-weight: 500; }
.quiet:hover:not(:disabled) { background: var(--nv-accent-soft); }

.spin { width: 13px; height: 13px; border: 2px solid currentColor;
        border-top-color: transparent; border-radius: 50%;
        animation: rot .6s linear infinite; }
@keyframes rot { to { transform: rotate(360deg); } }
</style>
