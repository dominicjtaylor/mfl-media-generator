import React, { useState } from 'react'

const LANGUAGES = ['spanish', 'italian']
const SLIDE_COUNTS = [4, 5, 6, 7, 8]

// Build a default slide types array for a given count.
// Slot 0 = first, slot n-1 = last, middle slots alternate content/translate.
function buildDefaultTypes(count) {
  const types = ['first']
  for (let i = 1; i < count - 1; i++) {
    types.push(i % 2 === 0 ? 'translate' : 'content')
  }
  types.push('last')
  return types
}

const MIDDLE_OPTIONS = ['content', 'translate']

export default function Form({ onConfigSubmit }) {
  const [language,  setLanguage]  = useState('spanish')
  const [count,     setCount]     = useState(5)
  const [types,     setTypes]     = useState(() => buildDefaultTypes(5))

  const handleCountChange = (n) => {
    setCount(n)
    setTypes(buildDefaultTypes(n))
  }

  const handleTypeChange = (index, value) => {
    setTypes(prev => {
      const next = [...prev]
      next[index] = value
      return next
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onConfigSubmit({ language, count, types })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Language */}
      <div>
        <label className="block text-sm font-semibold mb-2">Language</label>
        <div className="flex gap-2">
          {LANGUAGES.map(lang => (
            <button
              key={lang}
              type="button"
              onClick={() => setLanguage(lang)}
              className={`
                px-4 py-2 rounded-xl text-sm font-medium capitalize border transition-all
                ${language === lang
                  ? 'bg-accent text-white border-accent'
                  : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-accent hover:text-accent'
                }
              `}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>

      {/* Slide count */}
      <div>
        <label className="block text-sm font-semibold mb-2">Number of slides</label>
        <div className="flex gap-2 flex-wrap">
          {SLIDE_COUNTS.map(n => (
            <button
              key={n}
              type="button"
              onClick={() => handleCountChange(n)}
              className={`
                w-12 py-2 rounded-xl text-sm font-medium border transition-all
                ${count === n
                  ? 'bg-accent text-white border-accent'
                  : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-accent hover:text-accent'
                }
              `}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Slide type assignments */}
      <div>
        <label className="block text-sm font-semibold mb-2">Slide layout</label>
        <div className="space-y-2">
          {types.map((type, i) => {
            const isFirst = i === 0
            const isLast  = i === types.length - 1
            const isLocked = isFirst || isLast
            const num = String(i + 1).padStart(2, '0')

            return (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs font-semibold text-gray-400 tabular-nums w-5">{num}</span>
                {isLocked ? (
                  <span className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 capitalize">
                    {isFirst ? 'Hook (first)' : 'CTA (last)'}
                  </span>
                ) : (
                  <div className="flex gap-2">
                    {MIDDLE_OPTIONS.map(opt => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => handleTypeChange(i, opt)}
                        className={`
                          px-3 py-1.5 rounded-lg text-xs font-medium capitalize border transition-all
                          ${type === opt
                            ? 'bg-accent text-white border-accent'
                            : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:border-accent hover:text-accent'
                          }
                        `}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        className="
          w-full flex items-center justify-center gap-2
          bg-accent hover:bg-accent-hover
          text-white font-semibold text-sm
          px-5 py-3 rounded-xl
          transition-all active:scale-[0.98]
          shadow-sm
        "
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
        Start Building
      </button>
    </form>
  )
}
