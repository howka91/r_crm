<!--
  RichTextEditor — Tiptap v3 wrapper for ContractTemplate.body.

  Outputs raw HTML via v-model. Toolbar exposes the set agreed in the
  design plan: basic marks (bold/italic/underline/strike), headings,
  lists, text-align, text-color, font-family, font-size, link, and a
  "Insert placeholder" picker that drops `{{key}}` at the caret.

  In Tiptap v3 TextStyle + Color + FontFamily + FontSize all live in the
  same `@tiptap/extension-text-style` package. Underline is a separate
  mark.
-->
<script setup lang="ts">
import Image from "@tiptap/extension-image"
import Link from "@tiptap/extension-link"
import TextAlign from "@tiptap/extension-text-align"
import {
  Color,
  FontFamily,
  FontSize,
  TextStyle,
} from "@tiptap/extension-text-style"
import { Underline } from "@tiptap/extension-underline"
import StarterKit from "@tiptap/starter-kit"
import { EditorContent, Node, useEditor } from "@tiptap/vue-3"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"

import { usePromptStore } from "@/store/prompt"
import type { TemplatePlaceholder } from "@/types/models"

const props = defineProps<{
  modelValue: string
  placeholders?: TemplatePlaceholder[]
  disabled?: boolean
  /** Async uploader. Receives a File, returns the URL to embed. Without
   * this, the "insert image" button is hidden — we never embed base64
   * data URIs because they bloat the HTML payload and the PDF. */
  imageUploader?: (file: File) => Promise<string>
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void
}>()

// --- PageBreak custom node ----------------------------------------------
//
// An atomic block-level node rendered as `<div class="page-break"></div>`
// in the HTML output. The CSS (both in the editor and server-side in
// docgen) maps this class to `break-before: page`, which WeasyPrint
// honours when rasterising the PDF. In the editor the CSS shows a
// dashed "— Разрыв страницы —" divider so the admin can see the break.

const PageBreak = Node.create({
  name: "pageBreak",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,
  parseHTML() {
    return [
      { tag: "div.page-break" },
      { tag: "hr.page-break" },
      { tag: 'div[data-page-break="true"]' },
    ]
  },
  // Inline styles guarantee the marker is visible in the editor even if
  // the scoped CSS fails to load (HMR glitches, cache, etc.). The
  // `page-break` class is what actually triggers the PDF break on the
  // server via docgen's base stylesheet.
  renderHTML() {
    return [
      "div",
      {
        class: "page-break",
        "data-page-break": "true",
        style:
          "position:relative;display:block;height:28px;margin:1.2em 0;" +
          "border-top:2px dashed oklch(0.72 0.18 130);",
      },
    ]
  },
})

// --- Image — extended with an `align` attribute --------------------------
//
// The stock `@tiptap/extension-image` node renders a plain <img>. We add
// an `align` attribute (left / right / center / none) that maps to CSS:
// left/right = float (text wraps around the logo), center = block-level
// centred, none = default inline-block. Selected image gets a small
// toolbar row with alignment buttons (see template below).

const AlignedImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      align: {
        default: null,
        parseHTML: (el) =>
          el.getAttribute("data-align") || el.style.float || null,
        renderHTML: (attrs: { align?: string | null }) => {
          const a = attrs.align
          if (!a || a === "none") return {}
          if (a === "left") {
            return {
              "data-align": "left",
              style:
                "float:left;margin:0 16px 8px 0;max-width:50%;",
            }
          }
          if (a === "right") {
            return {
              "data-align": "right",
              style:
                "float:right;margin:0 0 8px 16px;max-width:50%;",
            }
          }
          if (a === "center") {
            return {
              "data-align": "center",
              style: "display:block;margin:0.5em auto;",
            }
          }
          return {}
        },
      },
    }
  },
})

// --- Editor --------------------------------------------------------------

// --- A4 pagination preview ----------------------------------------------
//
// The editor renders the document as a stack of real A4 sheets with a
// visible gap between them, so the admin sees the PDF layout directly.
// Sheet dimensions match docgen CSS: 210×297 mm with 18mm top/bottom
// and 15mm side margins. At 96 DPI: 794×1123 px outer, 680×987 px
// inner content area. Sheets are decorative backgrounds; the actual
// ProseMirror content is a single continuous flow overlaid on top.
const PX_PER_MM = 3.7795275591
const A4_WIDTH_PX = Math.round(210 * PX_PER_MM) // 794
const A4_HEIGHT_PX = Math.round(297 * PX_PER_MM) // 1123
const A4_CONTENT_WIDTH_PX = Math.round(180 * PX_PER_MM) // 680
const A4_CONTENT_HEIGHT_PX = Math.round(261 * PX_PER_MM) // 987
const PAGE_MARGIN_TOP_PX = Math.round(18 * PX_PER_MM) // 68
const PAGE_MARGIN_SIDE_PX = Math.round(15 * PX_PER_MM) // 57
const PAGE_GAP_PX = 24 // visual gap between stacked sheets

const editor = useEditor({
  content: props.modelValue,
  editable: !props.disabled,
  extensions: [
    StarterKit,
    Underline,
    TextStyle,
    FontFamily,
    Color,
    FontSize,
    TextAlign.configure({ types: ["heading", "paragraph"] }),
    Link.configure({ openOnClick: false, autolink: true }),
    AlignedImage.configure({ inline: false, allowBase64: false }),
    PageBreak,
  ],
  editorProps: {
    attributes: {
      class: "prose prose-sm max-w-none focus:outline-none",
    },
  },
  onUpdate: ({ editor }) => {
    emit("update:modelValue", editor.getHTML())
    // Reflow the page-guide markers whenever content changes.
    scheduleGuidesRecalc()
  },
})

// Keep editor in sync when parent resets the value (e.g. after load).
watch(
  () => props.modelValue,
  (val) => {
    const inst = editor.value
    if (!inst) return
    if (val === inst.getHTML()) return
    inst.commands.setContent(val || "", { emitUpdate: false })
  },
)

watch(
  () => props.disabled,
  (d) => editor.value?.setEditable(!d),
)

onBeforeUnmount(() => {
  editor.value?.destroy()
  resizeObs?.disconnect()
  window.removeEventListener("resize", scheduleGuidesRecalc)
  if (guidesRaf != null) cancelAnimationFrame(guidesRaf)
})

// --- Toolbar actions -----------------------------------------------------

const isActive = (mark: string, attrs?: Record<string, unknown>) => {
  const e = editor.value
  if (!e) return false
  return attrs ? e.isActive(mark, attrs) : e.isActive(mark)
}

const fontFamilies = [
  { label: "Inter", value: "Inter Tight, sans-serif" },
  { label: "Times", value: "'Times New Roman', Times, serif" },
  { label: "Courier", value: "'Courier New', Courier, monospace" },
  { label: "Arial", value: "Arial, Helvetica, sans-serif" },
]

const fontSizes = ["10px", "11px", "12px", "13px", "14px", "16px", "18px", "20px", "24px"]

const currentFontFamily = computed(() => {
  const e = editor.value
  if (!e) return ""
  return (e.getAttributes("textStyle").fontFamily as string) || ""
})

const currentFontSize = computed(() => {
  const e = editor.value
  if (!e) return ""
  return (e.getAttributes("textStyle").fontSize as string) || ""
})

const setFontFamily = (value: string) => {
  if (!editor.value) return
  if (!value) editor.value.chain().focus().unsetFontFamily().run()
  else editor.value.chain().focus().setFontFamily(value).run()
}

const setFontSize = (value: string) => {
  if (!editor.value) return
  if (!value) editor.value.chain().focus().unsetFontSize().run()
  else editor.value.chain().focus().setFontSize(value).run()
}

const setColor = (e: Event) => {
  const value = (e.target as HTMLInputElement).value
  editor.value?.chain().focus().setColor(value).run()
}

const insertLink = async () => {
  const e = editor.value
  if (!e) return
  const previous = (e.getAttributes("link").href as string) || ""
  const url = await usePromptStore().ask({
    title: "Ссылка",
    message: "Введите URL (оставьте пустым, чтобы снять ссылку):",
    placeholder: "https://example.com",
    defaultValue: previous,
  })
  if (url === null) return
  if (url === "") {
    e.chain().focus().unsetLink().run()
  } else {
    e.chain().focus().setLink({ href: url }).run()
  }
}

const insertPlaceholder = (key: string) => {
  const e = editor.value
  if (!e) return
  e.chain().focus().insertContent(`{{${key}}}`).run()
}

// --- Image upload --------------------------------------------------------

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadError = ref<string | null>(null)

function triggerImagePicker() {
  if (!props.imageUploader) return
  uploadError.value = null
  fileInput.value?.click()
}

async function onImagePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // Reset so picking the same file twice still fires @change.
  input.value = ""
  if (!file || !props.imageUploader) return
  uploading.value = true
  uploadError.value = null
  try {
    const url = await props.imageUploader(file)
    // Default to left-aligned (float) so subsequent text naturally
    // flows to the right of the logo — this is what users expect from
    // a "insert logo" action, and matches how the legacy templates were
    // laid out. Admin can still switch to center/right/no-wrap via the
    // contextual image toolbar.
    editor.value
      ?.chain()
      .focus()
      .insertContent({
        type: "image",
        attrs: { src: url, alt: file.name, align: "left" },
      })
      .run()
  } catch (err) {
    uploadError.value = err instanceof Error ? err.message : "Upload failed"
  } finally {
    uploading.value = false
  }
}

// --- Page break — forced break is still supported via the PageBreak node,
//     but auto A4 guides below remove the everyday need for it. ---------

function insertPageBreak() {
  const e = editor.value
  if (!e) return
  e.chain()
    .focus()
    .insertContent(
      '<div class="page-break" data-page-break="true"></div><p></p>',
    )
    .run()
}

// --- A4 multi-sheet preview ----------------------------------------------

const pageSheetRef = ref<HTMLElement | null>(null)
const pageCount = ref(1)
let guidesRaf: number | null = null

function scheduleGuidesRecalc() {
  if (guidesRaf != null) cancelAnimationFrame(guidesRaf)
  guidesRaf = requestAnimationFrame(() => {
    guidesRaf = null
    recalcPageCount()
  })
}

/** Count how many A4 sheets are needed to fit the current content.
 *
 * The tolerance buffer absorbs rounding slop from child `<p>` margins
 * and sub-pixel layout quirks — without it an empty editor with a
 * single `<p>` can measure ~1000px (just over one page) and wrongly
 * render two sheets. A second sheet only appears once content clearly
 * extends past the first page. */
function recalcPageCount() {
  const host = pageSheetRef.value
  const pm = host?.querySelector(".ProseMirror") as HTMLElement | null
  if (!pm || !host) {
    pageCount.value = 1
    return
  }
  const TOLERANCE_PX = 24
  const effective = Math.max(0, pm.offsetHeight - TOLERANCE_PX)
  pageCount.value = Math.max(1, Math.ceil(effective / A4_CONTENT_HEIGHT_PX))
}

/** Total height of the stack of sheets (including gaps). */
const stackHeight = computed(
  () =>
    pageCount.value * A4_HEIGHT_PX +
    Math.max(0, pageCount.value - 1) * PAGE_GAP_PX,
)

// Recompute on window resize (font metrics / wrapping change at different
// scroll zooms), on editor mount, and whenever modelValue is pushed in
// from outside (e.g. after loading a template).
let resizeObs: ResizeObserver | null = null

onMounted(() => {
  // Tiptap's ProseMirror view attaches itself on its own microtask cycle,
  // so the .ProseMirror element may not exist yet when the Vue component
  // has just mounted. A 0-ms setTimeout defers the first measurement
  // until after Tiptap is fully wired up.
  setTimeout(scheduleGuidesRecalc, 0)
  if (typeof ResizeObserver !== "undefined" && pageSheetRef.value) {
    resizeObs = new ResizeObserver(() => scheduleGuidesRecalc())
    resizeObs.observe(pageSheetRef.value)
  }
  window.addEventListener("resize", scheduleGuidesRecalc)
})

watch(
  () => props.modelValue,
  () => scheduleGuidesRecalc(),
)

// --- Image alignment (float / center) -----------------------------------

const imageSelected = computed(() => editor.value?.isActive("image") ?? false)

const currentImageAlign = computed<string>(() => {
  const e = editor.value
  if (!e) return "none"
  const attrs = e.getAttributes("image") as { align?: string | null }
  return attrs.align || "none"
})

function setImageAlign(align: "left" | "right" | "center" | "none") {
  const e = editor.value
  if (!e) return
  e.chain().focus().updateAttributes("image", { align }).run()
}

function removeImage() {
  const e = editor.value
  if (!e) return
  e.chain().focus().deleteSelection().run()
}

// Let the parent (template editor screen) drive caret-insertion from its
// own placeholder catalog. Same implementation as the in-toolbar picker.
defineExpose({ insertPlaceholder, insertPageBreak })
</script>

<template>
  <div class="border border-ym-line rounded-md bg-ym-surface overflow-hidden">
    <!-- Toolbar -->
    <div
      class="flex flex-wrap items-center gap-1 px-2 py-1.5 border-b border-ym-line-soft bg-ym-sunken/60"
    >
      <!--
        Marks: bold/italic/underline/strike — PrimeIcons 7 doesn't ship
        dedicated icons for these, so we render styled letters. That's
        also the canonical rich-editor pattern (Google Docs, Word).
      -->
      <button
        type="button"
        class="btn btn-xs btn-icon font-bold"
        :class="isActive('bold') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Жирный (Ctrl+B)"
        @click="editor?.chain().focus().toggleBold().run()"
      >
        B
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon italic"
        :class="isActive('italic') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Курсив (Ctrl+I)"
        @click="editor?.chain().focus().toggleItalic().run()"
      >
        I
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon underline"
        :class="isActive('underline') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Подчёркнутый (Ctrl+U)"
        @click="editor?.chain().focus().toggleUnderline().run()"
      >
        U
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon line-through"
        :class="isActive('strike') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Зачёркнутый"
        @click="editor?.chain().focus().toggleStrike().run()"
      >
        S
      </button>

      <span class="mx-1 h-5 w-px bg-ym-line-soft" aria-hidden="true" />

      <!-- Headings -->
      <button
        type="button"
        class="btn btn-xs"
        :class="isActive('heading', { level: 1 }) ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="H1"
        @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
      >
        H1
      </button>
      <button
        type="button"
        class="btn btn-xs"
        :class="isActive('heading', { level: 2 }) ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="H2"
        @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        H2
      </button>
      <button
        type="button"
        class="btn btn-xs"
        :class="isActive('heading', { level: 3 }) ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="H3"
        @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()"
      >
        H3
      </button>

      <span class="mx-1 h-5 w-px bg-ym-line-soft" aria-hidden="true" />

      <!-- Lists -->
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="isActive('bulletList') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Bullet list"
        @click="editor?.chain().focus().toggleBulletList().run()"
      >
        <i class="pi pi-list" />
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="isActive('orderedList') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Ordered list"
        @click="editor?.chain().focus().toggleOrderedList().run()"
      >
        <i class="pi pi-sort-numeric-down" />
      </button>

      <span class="mx-1 h-5 w-px bg-ym-line-soft" aria-hidden="true" />

      <!-- Align -->
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="editor?.isActive({ textAlign: 'left' }) ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Align left"
        @click="editor?.chain().focus().setTextAlign('left').run()"
      >
        <i class="pi pi-align-left" />
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="editor?.isActive({ textAlign: 'center' }) ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Align center"
        @click="editor?.chain().focus().setTextAlign('center').run()"
      >
        <i class="pi pi-align-center" />
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="editor?.isActive({ textAlign: 'right' }) ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Align right"
        @click="editor?.chain().focus().setTextAlign('right').run()"
      >
        <i class="pi pi-align-right" />
      </button>
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="editor?.isActive({ textAlign: 'justify' }) ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Justify"
        @click="editor?.chain().focus().setTextAlign('justify').run()"
      >
        <i class="pi pi-align-justify" />
      </button>

      <span class="mx-1 h-5 w-px bg-ym-line-soft" aria-hidden="true" />

      <!-- Font family -->
      <select
        class="inp inp-sm w-[130px]"
        :value="currentFontFamily"
        :disabled="disabled"
        @change="setFontFamily(($event.target as HTMLSelectElement).value)"
      >
        <option value="">Шрифт</option>
        <option v-for="f in fontFamilies" :key="f.value" :value="f.value">
          {{ f.label }}
        </option>
      </select>

      <!-- Font size -->
      <select
        class="inp inp-sm w-[86px]"
        :value="currentFontSize"
        :disabled="disabled"
        @change="setFontSize(($event.target as HTMLSelectElement).value)"
      >
        <option value="">Размер</option>
        <option v-for="s in fontSizes" :key="s" :value="s">{{ s }}</option>
      </select>

      <!-- Color -->
      <label
        class="btn btn-xs btn-ghost cursor-pointer"
        :class="{ 'opacity-50 cursor-not-allowed': disabled }"
        title="Text color"
      >
        <i class="pi pi-palette" />
        <input
          type="color"
          class="sr-only"
          :disabled="disabled"
          @change="setColor($event)"
        />
      </label>

      <span class="mx-1 h-5 w-px bg-ym-line-soft" aria-hidden="true" />

      <!-- Link -->
      <button
        type="button"
        class="btn btn-xs btn-icon"
        :class="isActive('link') ? 'bg-ym-primary-soft text-ym-primary' : 'btn-ghost'"
        :disabled="disabled"
        title="Link"
        @click="insertLink"
      >
        <i class="pi pi-link" />
      </button>

      <!-- Image upload — only when parent provided an uploader -->
      <button
        v-if="imageUploader"
        type="button"
        class="btn btn-xs btn-icon btn-ghost"
        :disabled="disabled || uploading"
        :title="uploading ? 'Загрузка…' : 'Вставить логотип / картинку'"
        @click="triggerImagePicker"
      >
        <i v-if="uploading" class="pi pi-spin pi-spinner" />
        <i v-else class="pi pi-image" />
      </button>
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
        @change="onImagePicked"
      />


      <span class="mx-1 h-5 w-px bg-ym-line-soft" aria-hidden="true" />

      <!-- Placeholder picker -->
      <div v-if="placeholders && placeholders.length" class="relative group">
        <button type="button" class="btn btn-xs btn-soft" :disabled="disabled">
          <i class="pi pi-hashtag" />
          <span>{{ $t("references.contract_templates.insert_placeholder") }}</span>
          <i class="pi pi-chevron-down text-[10px]" />
        </button>
        <div
          class="absolute top-full right-0 z-20 mt-1 min-w-[220px] max-h-[280px] overflow-auto card shadow-ym-float p-1 hidden group-focus-within:block group-hover:block"
        >
          <button
            v-for="p in placeholders"
            :key="p.key"
            type="button"
            class="w-full text-left px-2 py-1.5 rounded hover:bg-ym-primary-soft hover:text-ym-primary text-[12px] flex flex-col"
            @click="insertPlaceholder(p.key)"
          >
            <span class="mono text-ym-primary" v-text="`{{${p.key}}}`" />
            <span v-if="p.label" class="text-[11px] text-ym-muted">{{
              p.label
            }}</span>
          </button>
        </div>
      </div>

      <span
        v-if="uploadError"
        class="ml-auto text-[11px] text-ym-danger px-2 truncate"
        :title="uploadError"
      >
        {{ uploadError }}
      </span>
      <span v-else class="ml-auto text-[11px] text-ym-subtle px-2">
        Tiptap · HTML
      </span>
    </div>

    <!-- Image-selected contextual row — visible only when an image is
         selected. Controls the float/align attribute which affects how
         text wraps around the logo in the PDF. -->
    <div
      v-if="imageSelected"
      class="flex items-center gap-1 px-2 py-1.5 border-b border-ym-line-soft bg-ym-primary-soft/40"
    >
      <span class="text-[11px] text-ym-primary font-medium mr-2">
        <i class="pi pi-image text-[10px] mr-1" />
        Логотип
      </span>
      <button
        type="button"
        class="btn btn-xs"
        :class="currentImageAlign === 'left' ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="Слева, текст справа"
        @click="setImageAlign('left')"
      >
        <i class="pi pi-angle-double-left text-[10px]" />
        Слева
      </button>
      <button
        type="button"
        class="btn btn-xs"
        :class="currentImageAlign === 'center' ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="По центру"
        @click="setImageAlign('center')"
      >
        <i class="pi pi-align-center text-[10px]" />
        Центр
      </button>
      <button
        type="button"
        class="btn btn-xs"
        :class="currentImageAlign === 'right' ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="Справа, текст слева"
        @click="setImageAlign('right')"
      >
        <i class="pi pi-angle-double-right text-[10px]" />
        Справа
      </button>
      <button
        type="button"
        class="btn btn-xs"
        :class="currentImageAlign === 'none' ? 'btn-soft' : 'btn-ghost'"
        :disabled="disabled"
        title="Без обтекания"
        @click="setImageAlign('none')"
      >
        Без обтекания
      </button>
      <span class="flex-1" />
      <button
        type="button"
        class="btn btn-xs btn-danger"
        :disabled="disabled"
        @click="removeImage"
      >
        <i class="pi pi-trash text-[10px]" />
        Удалить
      </button>
    </div>

    <!--
      A4 multi-sheet preview. Decorative sheet backgrounds are stacked
      vertically with a visible gap; the real ProseMirror content is a
      single continuous flow overlaid on top, positioned with the same
      margins as the PDF (18mm top/bottom, 15mm sides). As the content
      grows past one sheet's content area (987 px), another sheet
      appears below it — exactly like Google Docs / Word.
    -->
    <div class="ym-page-canvas">
      <div
        ref="pageSheetRef"
        class="ym-page-stack"
        :style="{
          width: A4_WIDTH_PX + 'px',
          height: stackHeight + 'px',
        }"
      >
        <!-- Decorative A4 sheet backgrounds -->
        <div
          v-for="n in pageCount"
          :key="'sheet-' + n"
          class="ym-page-sheet"
          :style="{
            top: (n - 1) * (A4_HEIGHT_PX + PAGE_GAP_PX) + 'px',
            height: A4_HEIGHT_PX + 'px',
          }"
        >
          <span class="ym-page-sheet__label">A4 · {{ n }}</span>
        </div>

        <!-- Gap label between sheets -->
        <div
          v-for="n in pageCount - 1"
          :key="'gap-' + n"
          class="ym-page-gap-label"
          :style="{
            top: n * A4_HEIGHT_PX + (n - 1) * PAGE_GAP_PX + 'px',
            height: PAGE_GAP_PX + 'px',
          }"
        >
          <span>— разрыв страницы —</span>
        </div>

        <!-- ProseMirror content, positioned with PDF-accurate margins -->
        <div
          class="ym-page-content"
          :style="{
            top: PAGE_MARGIN_TOP_PX + 'px',
            left: PAGE_MARGIN_SIDE_PX + 'px',
            right: PAGE_MARGIN_SIDE_PX + 'px',
            width: A4_CONTENT_WIDTH_PX + 'px',
          }"
        >
          <EditorContent :editor="editor" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* A4 multi-sheet visualisation — editor looks like Google Docs / Word. */
.ym-page-canvas {
  background: oklch(0.94 0.01 285);
  padding: 24px 16px;
  overflow: auto;
  max-height: 70vh;
}
.ym-page-stack {
  position: relative;
  margin: 0 auto;
}

/* Each decorative sheet: pure white A4 rectangle with a soft shadow. */
.ym-page-sheet {
  position: absolute;
  left: 0;
  right: 0;
  background: #fff;
  box-shadow:
    0 2px 12px oklch(0 0 0 / 0.1),
    0 0 0 1px oklch(0.92 0.008 285);
  border-radius: 1px;
}
.ym-page-sheet__label {
  position: absolute;
  bottom: 14px;
  right: 18px;
  font-family: "JetBrains Mono", monospace;
  font-size: 10px;
  color: oklch(0.72 0.015 285);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  pointer-events: none;
}

/* "— разрыв страницы —" label sitting in the grey gap between sheets. */
.ym-page-gap-label {
  position: absolute;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.ym-page-gap-label span {
  font-family: "JetBrains Mono", monospace;
  font-size: 10px;
  color: oklch(0.55 0.015 285);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 2px 10px;
}

/* The actual editable content — single continuous ProseMirror view
   positioned on top of all sheets. Width matches the PDF content area;
   top offset matches the PDF top margin. */
.ym-page-content {
  position: absolute;
}

:deep(.ProseMirror) {
  /* Keep a generous clickable area but *under* one page-content worth,
     so the TOLERANCE_PX buffer in JS doesn't tip a near-empty editor
     into a 2-sheet render. A full sheet is still visible because the
     sheet background is 1123 px tall; ProseMirror just occupies less
     of it until there's content to fill. */
  min-height: 920px;
  line-height: 1.55;
}
:deep(.ProseMirror p) {
  margin: 0.4em 0;
}
:deep(.ProseMirror h1) {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0.6em 0 0.4em;
}
:deep(.ProseMirror h2) {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0.6em 0 0.4em;
}
:deep(.ProseMirror h3) {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0.6em 0 0.4em;
}
:deep(.ProseMirror ul),
:deep(.ProseMirror ol) {
  padding-left: 1.4em;
  margin: 0.4em 0;
}
:deep(.ProseMirror a) {
  color: oklch(0.38 0.1 155);
  text-decoration: underline;
}
:deep(.ProseMirror img) {
  max-width: 100%;
  max-height: 180px;
  height: auto;
  display: inline-block;
}
:deep(.ProseMirror img[data-align="left"]) {
  float: left;
  margin: 0 16px 8px 0;
  max-width: 50%;
}
:deep(.ProseMirror img[data-align="right"]) {
  float: right;
  margin: 0 0 8px 16px;
  max-width: 50%;
}
:deep(.ProseMirror img[data-align="center"]) {
  display: block;
  margin: 0.5em auto;
  float: none;
}
:deep(.ProseMirror img.ProseMirror-selectednode) {
  outline: 2px solid oklch(0.38 0.1 155);
  outline-offset: 2px;
}
/* Clear floats after a page break so subsequent content doesn't wrap
   against a logo from the prior section. */
:deep(.ProseMirror .page-break) {
  clear: both;
}
/* Page-break visualisation inside the editor. The node is an atomic
   empty div, so we have to give it real on-screen dimensions — an
   `height:0` version collapses. In the PDF output the class
   `page-break` is mapped to `break-before: page` by the server
   stylesheet (see `apps.contracts.services.docgen._BASE_CSS`). */
:deep(.ProseMirror div.page-break) {
  position: relative;
  display: block;
  height: 28px;
  margin: 1.2em 0;
  border-top: 1.5px dashed oklch(0.72 0.18 130);
  cursor: pointer;
  user-select: none;
}
:deep(.ProseMirror div.page-break::before) {
  content: "— Разрыв страницы —";
  position: absolute;
  top: -9px;
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  padding: 0 10px;
  font-size: 10.5px;
  font-family: "JetBrains Mono", monospace;
  color: oklch(0.52 0.018 285);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}
:deep(.ProseMirror div.page-break.ProseMirror-selectednode) {
  border-top-color: oklch(0.38 0.1 155);
  border-top-width: 2px;
  background: oklch(0.38 0.1 155 / 0.04);
}
:deep(.ProseMirror div.page-break.ProseMirror-selectednode::before) {
  color: oklch(0.38 0.1 155);
  font-weight: 600;
}
</style>
