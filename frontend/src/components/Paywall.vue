<script setup>
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="paywall">
    <div class="fade"></div>

    <div class="box">
      <span class="badge">Subscriber story</span>
      <h3>Keep reading with a BOSS subscription</h3>
      <p>
        Full access to premium stories, every digital issue, and the archive.
      </p>

      <ul class="perks">
        <li>Unlimited premium articles</li>
        <li>Every issue to read online or download</li>
        <li>The complete back catalogue</li>
      </ul>

      <button class="cta" disabled>Subscribe — coming soon</button>
      <p class="phase">
        Online payment is not yet available. Contact the editorial team to have
        a subscription activated on your account.
      </p>

      <p v-if="!auth.isAuthenticated" class="alt">
        Already a subscriber?
        <router-link to="/login">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.paywall { position: relative; margin-top: -140px; }
.fade { height: 140px;
        background: linear-gradient(180deg, rgba(10,10,10,0) 0%,
                    var(--boss-bg) 88%); }
.box { background: var(--boss-surface); border: 1px solid var(--boss-line);
       border-radius: var(--r-lg); padding: var(--s-7); text-align: center;
       font-family: var(--font-ui); }
.badge { display: inline-block; font-size: var(--t-xs);
         letter-spacing: var(--track-caps); text-transform: uppercase;
         color: var(--boss-gold); border: 1px solid var(--boss-gold-deep);
         padding: var(--s-1) var(--s-3); border-radius: var(--r-full); }
h3 { font-family: var(--font-serif); font-size: var(--t-xl);
     margin: var(--s-4) 0 var(--s-3); line-height: var(--lh-tight);
     color: var(--boss-text); font-weight: 600; }
.box > p { color: var(--boss-text-muted); font-size: var(--t-base);
           line-height: var(--lh-body); margin: 0 auto var(--s-5); max-width: 400px; }
.perks { list-style: none; padding: 0; margin: 0 auto var(--s-6); max-width: 300px;
         text-align: left; }
.perks li { position: relative; padding: var(--s-2) 0 var(--s-2) var(--s-5);
            font-size: var(--t-sm); color: var(--boss-text); }
.perks li::before { content: '\2713'; position: absolute; left: 0;
                    color: var(--boss-gold); font-weight: 700; }
.cta { border: 0; background: var(--boss-gold); color: var(--boss-bg);
       padding: var(--s-3) var(--s-7); font-size: var(--t-sm); font-weight: 700;
       letter-spacing: var(--track-caps); text-transform: uppercase;
       cursor: pointer; transition: background var(--dur-base) var(--ease-out); }
.cta:hover:not(:disabled) { background: var(--boss-gold-bright); }
.cta:disabled { opacity: .5; cursor: not-allowed; }
.phase { font-size: var(--t-xs); color: var(--boss-text-faint);
         margin: var(--s-4) auto 0; max-width: 360px; line-height: var(--lh-snug); }
.alt { font-size: var(--t-sm); color: var(--boss-text-muted); margin: var(--s-5) 0 0; }
.alt a { color: var(--boss-gold); }
</style>
