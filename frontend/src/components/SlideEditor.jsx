import React from 'react'
import SlideCard from './SlideCard.jsx'

export default function SlideEditor({
  slides,
  language,
  hooks,
  hookLoading,
  onChange,
  onRequestHooks,
}) {
  return (
    <div className="space-y-4">
      {slides.map((slide, i) => (
        <SlideCard
          key={i}
          index={i}
          slide={slide}
          language={language}
          hooks={slide.type === 'first' ? hooks : []}
          hookLoading={slide.type === 'first' ? hookLoading : false}
          onChange={onChange}
          onRequestHooks={slide.type === 'first' ? onRequestHooks : undefined}
        />
      ))}
    </div>
  )
}
