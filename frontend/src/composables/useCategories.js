/* The managed category list, shared by every picker on the page so a
   category created in one form shows up in the others at once. */
import { ref, computed } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import { confirm } from './useConfirm'

const list = ref([])
let loading = null

export function useCategories() {
  const auth = useAuthStore()

  function load(force = false) {
    if (!force && (list.value.length || loading)) return loading
    loading = api.get('/editorial/categories/')
      .then(({ data }) => { list.value = data })
      .finally(() => { loading = null })
    return loading
  }

  /* Options for UiCombobox. The article's own category is kept even if it
     has since been archived, so the field never shows blank. */
  const optionsWith = (current = '') => {
    const opts = list.value.map((c) => ({
      value: c.name, label: c.name,
      hint: c.article_count ? `${c.article_count} article${c.article_count === 1 ? '' : 's'}` : '',
    }))
    if (current && !opts.some((o) => o.value === current)) {
      opts.push({ value: current, label: current, hint: 'archived' })
    }
    return opts
  }

  /* Editors and administrators may add a category from the picker. */
  const canCreate = computed(() => ['EDITOR', 'ADMIN'].includes(auth.role))

  async function create(name) {
    const clean = name.trim().replace(/\s+/g, ' ')
    const ok = await confirm({
      title: `Create the category “${clean}”?`,
      message: 'It is added to the category list for the whole team.',
      points: [
        'Writers and editors can file articles under it straight away.',
        'Only an administrator can rename or archive it later.',
      ],
      confirmLabel: 'Create category',
    })
    if (!ok) return null
    const { data } = await api.post('/editorial/categories/', { name: clean })
    if (!list.value.some((c) => c.id === data.id)) {
      list.value = [...list.value, data].sort((a, b) => a.name.localeCompare(b.name))
    }
    return { value: data.name, label: data.name }
  }

  return { categories: list, load, optionsWith, canCreate, create }
}
