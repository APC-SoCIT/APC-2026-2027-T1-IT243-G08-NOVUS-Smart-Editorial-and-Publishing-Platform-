<script setup>
import { ref } from 'vue'
import api from '../services/api'
import UiButton from './ui/UiButton.vue'

const props = defineProps({
  article: { type: Object, required: true },
})
const emit = defineEmits(['changed'])

const busy = ref(false)
const error = ref('')
const heroCaption = ref(props.article.hero_caption || '')
const pendingRemove = ref(null)

async function patchArticle(payload, isFile = false) {
  error.value = ''
  busy.value = true
  try {
    let body = payload, config = {}
    if (isFile) {
      body = new FormData()
      Object.entries(payload).forEach(([k, v]) => body.append(k, v))
      config = { headers: { 'Content-Type': 'multipart/form-data' } }
    }
    await api.patch(`/editorial/articles/${props.article.id}/`, body, config)
    emit('changed')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not save that change.'
  } finally { busy.value = false }
}

function replaceHero(e) {
  const f = e.target.files[0]
  if (!f) return
  patchArticle({ hero_image: f }, true)
  e.target.value = ''
}

const removeHero = () => patchArticle({ hero_image: '' })
const saveCaption = () => patchArticle({ hero_caption: heroCaption.value })

async function addInline(e) {
  const f = e.target.files[0]
  if (!f) return
  error.value = ''
  busy.value = true
  try {
    const fd = new FormData()
    fd.append('article', props.article.id)
    fd.append('image', f)
    await api.post('/editorial/images/', fd,
      { headers: { 'Content-Type': 'multipart/form-data' } })
    emit('changed')
  } catch (e2) {
    error.value = e2.response?.data?.detail || 'Could not upload that image.'
  } finally { busy.value = false; e.target.value = '' }
}

async function removeInline(img) {
  pendingRemove.value = null
  error.value = ''
  busy.value = true
  try {
    await api.delete(`/editorial/images/${img.id}/`)
    emit('changed')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not remove that image.'
  } finally { busy.value = false }
}
</script>

<template>
  <section class="imgs">
    <h5>Photography</h5>
    <p class="hint">
      Replace weak photography before approving. Inline images appear in the
      body where the writer placed them; removing one leaves a gap in the text.
    </p>

    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <!-- hero -->
    <div class="hero">
      <div v-if="article.hero_image" class="preview">
        <img :src="article.hero_image"
             :alt="article.hero_caption || 'Current hero image'" />
        <div class="overlay">
          <label class="mini">
            Replace
            <input type="file" accept="image/*" hidden @change="replaceHero" />
          </label>
          <button class="mini danger" :disabled="busy" @click="removeHero">
            Remove
          </button>
        </div>
      </div>

      <label v-else class="drop">
        <span class="plus" aria-hidden="true">+</span>
        <span class="dt">Add a hero image</span>
        <span class="ds">This article has none. It will run as text-only.</span>
        <input type="file" accept="image/*" hidden @change="replaceHero" />
      </label>

      <label v-if="article.hero_image" class="cap">
        CAPTION OR CREDIT
        <div class="caprow">
          <input v-model="heroCaption" placeholder="Photographer, location, or context" />
          <UiButton size="sm" :loading="busy" @click="saveCaption">Save</UiButton>
        </div>
      </label>
    </div>

    <!-- inline -->
    <div class="inline">
      <div class="ihead">
        <span>In the body</span>
        <label class="mini add">
          + Add image
          <input type="file" accept="image/*" hidden @change="addInline" />
        </label>
      </div>

      <p v-if="!article.images?.length" class="none">No images in the body.</p>

      <ul v-else class="strip">
        <li v-for="img in article.images" :key="img.id">
          <img :src="img.image" :alt="img.caption || 'Image within the article'" />
          <button class="x" :disabled="busy" @click="pendingRemove = img"
                  :aria-label="`Remove image ${img.caption || ''}`">×</button>
          <span v-if="pendingRemove?.id === img.id" class="confirm">
            <button @click="removeInline(img)">Remove</button>
            <button @click="pendingRemove = null">Keep</button>
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.imgs { border: 1px solid var(--nv-line); border-radius: var(--r-md);
        padding: var(--s-5); margin-top: var(--s-5); background: var(--nv-surface); }
h5 { margin: 0 0 4px; font-size: 13px; letter-spacing: .05em;
     text-transform: uppercase; color: var(--nv-text-muted); font-weight: 600; }
.hint { margin: 0 0 var(--s-4); font-size: 13px; line-height: 1.55;
        color: var(--nv-text-faint); }
.err { color: var(--bad); font-size: 14px; margin: 0 0 var(--s-3); }

.preview { position: relative; border-radius: var(--r-sm); overflow: hidden; }
.preview img { width: 100%; max-height: 240px; object-fit: cover; }
.overlay { position: absolute; top: 10px; right: 10px; display: flex; gap: 6px; }
.mini { background: rgba(0,0,0,.72); color: #fff; border: 0; border-radius: var(--r-sm);
        padding: 7px 13px; font-size: 13px; font-family: inherit; cursor: pointer; }
.mini:hover { background: rgba(0,0,0,.88); }
.mini.danger:hover { background: var(--bad); }

.drop { display: flex; flex-direction: column; align-items: center; gap: 5px;
        padding: var(--s-6); border: 1px dashed var(--nv-line-strong);
        border-radius: var(--r-sm); cursor: pointer; text-align: center;
        transition: border-color var(--dur-fast) var(--ease-out); }
.drop:hover { border-color: var(--nv-accent); }
.plus { font-size: 22px; color: var(--nv-text-faint); }
.dt { font-size: 15px; font-weight: 600; color: var(--nv-text); }
.ds { font-size: 13px; color: var(--nv-text-faint); }

.cap { display: block; margin-top: var(--s-3); font-size: 12px;
       letter-spacing: .04em; color: var(--nv-text-muted); }
.caprow { display: flex; gap: 8px; margin-top: 5px; }
.caprow input { flex: 1; padding: 9px 12px; font-size: 14px;
                border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
                font-family: inherit; }

.inline { margin-top: var(--s-5); padding-top: var(--s-4);
          border-top: 1px solid var(--nv-line); }
.ihead { display: flex; justify-content: space-between; align-items: center;
         margin-bottom: var(--s-3); font-size: 13px; color: var(--nv-text-muted); }
.mini.add { background: var(--nv-bg); color: var(--nv-accent);
            border: 1px solid var(--nv-line-strong); }
.none { font-size: 13px; color: var(--nv-text-faint); margin: 0; }

.strip { list-style: none; margin: 0; padding: 0; display: flex;
         gap: var(--s-3); flex-wrap: wrap; }
.strip li { position: relative; width: 108px; }
.strip img { width: 108px; height: 78px; object-fit: cover;
             border-radius: var(--r-sm); border: 1px solid var(--nv-line); }
.x { position: absolute; top: -6px; right: -6px; width: 22px; height: 22px;
     border-radius: 50%; background: var(--nv-text); color: #fff; border: 0;
     font-size: 15px; line-height: 1; cursor: pointer; }
.x:hover { background: var(--bad); }
.confirm { position: absolute; inset: 0; display: flex; flex-direction: column;
           gap: 3px; align-items: center; justify-content: center;
           background: rgba(255,255,255,.96); border-radius: var(--r-sm); }
.confirm button { border: 0; background: none; font-size: 12px; cursor: pointer;
                  padding: 2px 6px; font-family: inherit; }
.confirm button:first-child { color: var(--bad); font-weight: 700; }
.confirm button:last-child { color: var(--nv-text-muted); }
</style>
