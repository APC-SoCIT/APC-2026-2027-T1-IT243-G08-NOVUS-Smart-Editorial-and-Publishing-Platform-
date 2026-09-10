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
.paywall { position: relative; margin-top: -120px; }
.fade { height: 120px;
        background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #fff 88%); }
.box { background: #fff; border: 1px solid #e8e8e8; border-radius: 14px;
       padding: 34px 36px; text-align: center; font-family: system-ui; }
.badge { display: inline-block; font-size: 10px; letter-spacing: 1.6px;
         text-transform: uppercase; color: #96631a; background: #fdf6e8;
         padding: 5px 12px; border-radius: 12px; }
h3 { font-family: Georgia, serif; font-size: 26px; margin: 16px 0 10px;
     line-height: 1.3; }
.box > p { color: #778; font-size: 14px; line-height: 1.6; margin: 0 auto 22px;
           max-width: 380px; }
.perks { list-style: none; padding: 0; margin: 0 auto 26px; max-width: 300px;
         text-align: left; }
.perks li { position: relative; padding: 7px 0 7px 26px; font-size: 14px; color: #445; }
.perks li::before { content: '✓'; position: absolute; left: 0; color: #2e9e63;
                    font-weight: 700; }
.cta { border: 0; background: #111; color: #fff; padding: 13px 34px;
       border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
.cta:disabled { opacity: .45; cursor: not-allowed; }
.phase { font-size: 12px; color: #aaa; margin: 14px auto 0; max-width: 340px;
         line-height: 1.55; }
.alt { font-size: 13px; color: #778; margin: 18px 0 0; }
.alt a { color: #4a7fb5; }
</style>
