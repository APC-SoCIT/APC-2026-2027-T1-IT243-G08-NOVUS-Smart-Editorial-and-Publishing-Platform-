<script setup>
import { ref, onMounted } from 'vue'

const KEY = 'novus.cookie-choice'
const visible = ref(false)
const expanded = ref(false)

onMounted(() => {
  // Shown once. The choice itself is the only thing we store as a result.
  if (!localStorage.getItem(KEY)) {
    setTimeout(() => (visible.value = true), 900)
  }
})

function record(choice) {
  localStorage.setItem(KEY, JSON.stringify({
    choice,
    at: new Date().toISOString(),
  }))
  if (choice === 'necessary') {
    // Clear anything functional we may have kept. Sign-in tokens stay —
    // without them the user cannot remain signed in at all.
    localStorage.removeItem('novus.prefs')
  }
  visible.value = false
}
</script>

<template>
  <transition name="rise">
    <aside v-if="visible" class="notice" role="region"
           aria-label="Cookie and storage notice">
      <div class="inner">
        <div class="copy">
          <h2>Browser storage</h2>
          <p>
            We store only what the site needs to work — a sign-in token so you
            stay logged in, and a record of this choice. No advertising
            cookies, no cross-site tracking.
          </p>

          <button class="more" :aria-expanded="expanded"
                  aria-controls="cookie-detail" @click="expanded = !expanded">
            {{ expanded ? 'Hide detail' : 'What is stored?' }}
          </button>

          <div v-show="expanded" id="cookie-detail" class="detail">
            <dl>
              <dt>Strictly necessary</dt>
              <dd>
                Authentication tokens that keep you signed in, cleared when you
                sign out. A record of this choice. These cannot be switched off
                without breaking sign-in.
              </dd>
              <dt>Functional</dt>
              <dd>
                Interface preferences, such as the category you last filtered
                by. Declining these only makes the site slightly less
                convenient.
              </dd>
            </dl>
            <router-link to="/legal/cookies" class="policy">
              Read the full Cookie Policy →
            </router-link>
          </div>
        </div>

        <div class="actions">
          <button class="ghost" @click="record('necessary')">
            Necessary only
          </button>
          <button class="primary" @click="record('all')">
            Accept all
          </button>
        </div>
      </div>
    </aside>
  </transition>
</template>

<style scoped>
.notice { position: fixed; left: 0; right: 0; bottom: 0; z-index: 80;
          background: var(--boss-surface); border-top: 1px solid var(--boss-gold-deep);
          box-shadow: 0 -10px 40px rgba(0,0,0,.5); }
.inner { max-width: 1100px; margin: 0 auto; padding: var(--s-5) var(--s-7);
         display: flex; gap: var(--s-7); align-items: flex-start; }
.copy { flex: 1; }
h2 { font-size: var(--t-xs); letter-spacing: var(--track-caps);
     text-transform: uppercase; color: var(--boss-gold); margin: 0 0 var(--s-2); }
.copy p { font-size: var(--t-sm); line-height: var(--lh-body);
          color: var(--boss-text-muted); margin: 0; max-width: 62ch; }

.more { background: none; border: 0; padding: var(--s-2) 0; cursor: pointer;
        font-size: var(--t-xs); letter-spacing: var(--track-caps);
        text-transform: uppercase; color: var(--boss-text-faint);
        transition: color var(--dur-fast) var(--ease-out); }
.more:hover { color: var(--boss-gold); }

.detail { margin-top: var(--s-3); padding-top: var(--s-3);
          border-top: 1px solid var(--boss-line); }
dl { margin: 0; }
dt { font-size: var(--t-xs); letter-spacing: var(--track-caps);
     text-transform: uppercase; color: var(--boss-text); margin-bottom: var(--s-1); }
dd { margin: 0 0 var(--s-3); font-size: var(--t-sm); line-height: var(--lh-body);
     color: var(--boss-text-muted); max-width: 62ch; }
.policy { font-size: var(--t-xs); letter-spacing: var(--track-caps);
          text-transform: uppercase; color: var(--boss-gold); }

.actions { display: flex; gap: var(--s-3); flex-shrink: 0; padding-top: var(--s-2); }
.actions button { padding: var(--s-3) var(--s-5); font-size: var(--t-xs);
                  font-weight: 600; letter-spacing: var(--track-caps);
                  text-transform: uppercase; cursor: pointer;
                  transition: all var(--dur-base) var(--ease-out); }
.ghost { background: transparent; border: 1px solid var(--boss-line);
         color: var(--boss-text-muted); }
.ghost:hover { border-color: var(--boss-text-muted); color: var(--boss-text); }
.primary { background: var(--boss-gold); border: 1px solid var(--boss-gold);
           color: var(--boss-bg); }
.primary:hover { background: var(--boss-gold-bright);
                 border-color: var(--boss-gold-bright); }

.rise-enter-active, .rise-leave-active {
  transition: transform var(--dur-base) var(--ease-out), opacity var(--dur-base); }
.rise-enter-from, .rise-leave-to { transform: translateY(100%); opacity: 0; }

@media (max-width: 820px) {
  .inner { flex-direction: column; gap: var(--s-4); padding: var(--s-4); }
  .actions { width: 100%; }
  .actions button { flex: 1; }
}
</style>
