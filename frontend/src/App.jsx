import React, { useState, useEffect, useCallback } from 'react'
import Form from './components/Form.jsx'
import SlideEditor from './components/SlideEditor.jsx'
import Output from './components/Output.jsx'
import Toast from './components/Toast.jsx'

// ---------------------------------------------------------------------------
// Build an empty slides array from type assignments
// ---------------------------------------------------------------------------
function buildEmptySlides(types) {
  return types.map(type => ({
    type,
    text_main:      '',
    text_cursive:   '',
    text_secondary: '',
    underline:      '',
    left_text:      '',
    right_text:     '',
  }))
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
export default function App() {
  const [dark, setDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)

  // phase: "configure" | "edit" | "done"
  const [phase,         setPhase]         = useState('configure')
  const [language,      setLanguage]      = useState('spanish')
  const [slides,        setSlides]        = useState([])
  const [hooks,         setHooks]         = useState([])
  const [hookLoading,   setHookLoading]   = useState(false)
  const [renderLoading, setRenderLoading] = useState(false)
  const [images,        setImages]        = useState([])
  const [caption,       setCaption]       = useState('')
  const [errorMsg,      setErrorMsg]      = useState('')
  const [toast,         setToast]         = useState(null)

  // Sync dark class on <html>
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }, [])

  // ── Phase 1: Config submitted → initialise slides ────────────────────────
  const handleConfigSubmit = useCallback(({ language: lang, types }) => {
    setLanguage(lang)
    setSlides(buildEmptySlides(types))
    setHooks([])
    setImages([])
    setErrorMsg('')
    setPhase('edit')
  }, [])

  // ── Phase 2: Slide field change ──────────────────────────────────────────
  const handleSlideChange = useCallback((index, field, value) => {
    setSlides(prev => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }, [])

  // ── Phase 2: Request AI hook suggestions ────────────────────────────────
  const handleRequestHooks = useCallback(async () => {
    const contentSummary = slides
      .map(s => s.text_main || s.left_text || s.right_text)
      .filter(Boolean)
      .join(' | ')

    setHookLoading(true)
    setHooks([])

    try {
      const res = await fetch('/generate-hooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: contentSummary || 'carousel content', language }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Server error (${res.status})`)
      }
      const data = await res.json()
      setHooks(data.hooks || [])
    } catch (err) {
      showToast(err.message || 'Hook generation failed', 'error')
    } finally {
      setHookLoading(false)
    }
  }, [slides, language, showToast])

  // ── Phase 2: Render carousel → phase "done" ─────────────────────────────
  const handleRender = useCallback(async () => {
    setRenderLoading(true)
    setErrorMsg('')

    try {
      const res = await fetch('/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slides, language }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Server error (${res.status})`)
      }
      const data = await res.json()
      setImages(data.images || [])
      setCaption(data.caption || '')
      setPhase('done')
      showToast('Carousel rendered!')
    } catch (err) {
      const msg = err.message?.includes('Failed to fetch')
        ? 'Could not reach the server. Check your connection.'
        : err.message || 'Rendering failed.'
      setErrorMsg(msg)
      showToast(msg, 'error')
    } finally {
      setRenderLoading(false)
    }
  }, [slides, language, showToast])

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-6 h-6 rounded-md bg-accent flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="1" y="1" width="5" height="5" rx="1" fill="white"/>
                <rect x="8" y="1" width="5" height="5" rx="1" fill="white" fillOpacity=".6"/>
                <rect x="1" y="8" width="5" height="5" rx="1" fill="white" fillOpacity=".6"/>
                <rect x="8" y="8" width="5" height="5" rx="1" fill="white" fillOpacity=".3"/>
              </svg>
            </span>
            <span className="font-semibold text-sm tracking-tight">MFL Carousel</span>
          </div>

          <button
            onClick={() => setDark(d => !d)}
            aria-label="Toggle dark mode"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:hover:text-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            {dark ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/>
                <line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/>
                <line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-10 flex flex-col gap-8">

        {/* ── Configure phase ── */}
        {phase === 'configure' && (
          <>
            <div className="text-center space-y-2">
              <h1 className="text-3xl font-bold tracking-tight">Build your carousel</h1>
              <p className="text-gray-500 dark:text-gray-400 text-sm">
                Set up your slides, fill in the content, and let AI suggest your hook.
              </p>
            </div>
            <Form onConfigSubmit={handleConfigSubmit} />
          </>
        )}

        {/* ── Edit phase ── */}
        {phase === 'edit' && (
          <>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight">Fill in your slides</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 capitalize">{language} · {slides.length} slides</p>
              </div>
              <button
                type="button"
                onClick={() => setPhase('configure')}
                className="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              >
                ← Back
              </button>
            </div>

            <SlideEditor
              slides={slides}
              language={language}
              hooks={hooks}
              hookLoading={hookLoading}
              onChange={handleSlideChange}
              onRequestHooks={handleRequestHooks}
            />

            <div className="flex flex-col gap-3 pt-2">
              {errorMsg && (
                <p className="text-xs text-red-500 text-center">{errorMsg}</p>
              )}
              <button
                type="button"
                onClick={handleRender}
                disabled={renderLoading}
                className="
                  w-full flex items-center justify-center gap-2
                  bg-accent hover:bg-accent-hover
                  disabled:opacity-50 disabled:cursor-not-allowed
                  text-white font-semibold text-sm
                  px-5 py-3.5 rounded-xl
                  transition-all active:scale-[0.98]
                  shadow-sm
                "
              >
                {renderLoading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    Rendering…
                  </>
                ) : (
                  <>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                    </svg>
                    Render Carousel
                  </>
                )}
              </button>
            </div>
          </>
        )}

        {/* ── Done phase ── */}
        {phase === 'done' && (
          <>
            <Output
              images={images}
              caption={caption}
              onCaptionChange={setCaption}
              renderLoading={renderLoading}
              errorMsg={errorMsg}
              onToast={showToast}
            />
            <button
              type="button"
              onClick={() => { setPhase('edit'); setImages([]); setCaption(''); setErrorMsg('') }}
              className="
                w-full py-3 rounded-xl text-sm font-medium
                border border-gray-200 dark:border-gray-700
                text-gray-500 dark:text-gray-400
                hover:text-gray-900 dark:hover:text-gray-100
                hover:border-gray-300 dark:hover:border-gray-600
                transition-colors
              "
            >
              ← Edit slides
            </button>
          </>
        )}

      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="text-center text-xs text-gray-400 dark:text-gray-600 py-6">
        MFL Media Generator
      </footer>

      {/* ── Toast ──────────────────────────────────────────────── */}
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}
