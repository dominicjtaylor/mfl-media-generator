import React from 'react'

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4 text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
    </svg>
  )
}

const STYLE_LABELS = ['MISTAKE', 'REVEAL', 'CONTRAST', 'PHRASE', 'SCENARIO']

export default function HookPicker({ hooks, loading, onSelect }) {
  if (!loading && hooks.length === 0) return null

  return (
    <div className="mt-3 space-y-2 animate-fade-in">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
        Hook suggestions
      </p>

      {loading ? (
        <div className="flex items-center gap-2 py-3 text-sm text-gray-400">
          <Spinner />
          Generating hook ideas…
        </div>
      ) : (
        <div className="space-y-2">
          {hooks.map((hook, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onSelect(hook)}
              className="
                w-full text-left px-4 py-3 rounded-xl text-sm
                border border-gray-200 dark:border-gray-700
                bg-white dark:bg-gray-900
                hover:border-accent hover:bg-accent/5
                transition-all duration-150 group
              "
            >
              <div className="flex items-start gap-3">
                <span className="text-[10px] font-semibold text-gray-400 dark:text-gray-600 uppercase tracking-wide mt-0.5 shrink-0 w-16">
                  {STYLE_LABELS[i] || `Option ${i + 1}`}
                </span>
                <span className="text-gray-800 dark:text-gray-200 leading-snug group-hover:text-accent transition-colors">
                  {hook}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
