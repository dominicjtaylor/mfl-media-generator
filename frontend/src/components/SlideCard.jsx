import React from 'react'
import HookPicker from './HookPicker.jsx'

// ---------------------------------------------------------------------------
// Slide type badge config
// ---------------------------------------------------------------------------
const TYPE_META = {
  first:     { label: 'Hook',      color: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300' },
  content:   { label: 'Content',   color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
  translate: { label: 'Translate', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  last:      { label: 'CTA',       color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
}

// ---------------------------------------------------------------------------
// Shared input styles
// ---------------------------------------------------------------------------
const INPUT_BASE = `
  w-full rounded-lg px-3 py-2.5 text-sm leading-relaxed
  bg-white dark:bg-gray-900
  border border-gray-200 dark:border-gray-700
  placeholder-gray-400 dark:placeholder-gray-600
  focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent
  transition-shadow
`

const LABEL_BASE = 'block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1'

// ---------------------------------------------------------------------------
// Field components
// ---------------------------------------------------------------------------
function TextArea({ label, value, onChange, placeholder, rows = 2 }) {
  return (
    <div>
      <label className={LABEL_BASE}>{label}</label>
      <textarea
        rows={rows}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className={`${INPUT_BASE} resize-none`}
      />
    </div>
  )
}

function TextInput({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className={LABEL_BASE}>{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className={INPUT_BASE}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// SlideCard
// ---------------------------------------------------------------------------
export default function SlideCard({
  index,
  slide,
  language,
  hooks,
  hookLoading,
  onChange,
  onRequestHooks,
}) {
  const meta  = TYPE_META[slide.type] || TYPE_META.content
  const num   = String(index + 1).padStart(2, '0')
  const lang  = language === 'italian' ? 'Italian' : 'Spanish'

  const field = (key) => (val) => onChange(index, key, val)

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 shadow-sm overflow-hidden">

      {/* Card header */}
      <div className="flex items-center gap-2.5 px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800">
        <span className="text-xs font-semibold text-gray-400 dark:text-gray-600 tabular-nums">{num}</span>
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide ${meta.color}`}>
          {meta.label}
        </span>
      </div>

      {/* Card body — type-specific inputs */}
      <div className="p-4 space-y-3">

        {slide.type === 'first' && (
          <>
            <TextArea
              label="Hook text"
              value={slide.text_main}
              onChange={field('text_main')}
              placeholder="e.g. English speakers say this wrong in every Spanish shop"
              rows={2}
            />

            <button
              type="button"
              onClick={onRequestHooks}
              disabled={hookLoading}
              className="
                flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold
                border border-accent text-accent
                hover:bg-accent hover:text-white
                disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors duration-150
              "
            >
              {hookLoading ? (
                <>
                  <svg className="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Generating…
                </>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  Generate Hook Ideas
                </>
              )}
            </button>

            <HookPicker
              hooks={hooks}
              loading={hookLoading}
              onSelect={(hook) => field('text_main')(hook)}
            />
          </>
        )}

        {slide.type === 'content' && (
          <>
            <TextArea
              label="Main text"
              value={slide.text_main}
              onChange={field('text_main')}
              placeholder="e.g. Most learners say 'Estoy caliente' — but this means something very different"
              rows={3}
            />
            <TextInput
              label="Cursive text (optional)"
              value={slide.text_cursive}
              onChange={field('text_cursive')}
              placeholder="e.g. caliente"
            />
            <TextInput
              label="Secondary text (optional)"
              value={slide.text_secondary}
              onChange={field('text_secondary')}
              placeholder="e.g. (this is important)"
            />
            <TextInput
              label="Underline (optional)"
              value={slide.underline}
              onChange={field('underline')}
              placeholder="e.g. never say this"
            />
          </>
        )}

        {slide.type === 'translate' && (
          <div className="grid grid-cols-2 gap-3">
            <TextInput
              label="English"
              value={slide.left_text}
              onChange={field('left_text')}
              placeholder="e.g. I'm just looking"
            />
            <TextInput
              label={lang}
              value={slide.right_text}
              onChange={field('right_text')}
              placeholder={lang === 'Spanish' ? 'e.g. Solo estoy mirando' : 'e.g. Sto solo guardando'}
            />
          </div>
        )}

        {slide.type === 'last' && (
          <>
            <TextArea
              label="CTA text"
              value={slide.text_main}
              onChange={field('text_main')}
              placeholder="e.g. Save this — follow @tutor_mia_mfl for daily Spanish phrases"
              rows={2}
            />
            <p className="text-xs text-gray-400 dark:text-gray-600">
              Include <code className="text-accent">@tutor_mia_mfl</code> and a save/follow action.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
