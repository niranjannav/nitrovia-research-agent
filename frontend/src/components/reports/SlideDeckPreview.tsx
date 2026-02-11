import type { GeneratedPresentation } from '../../types/report'

interface SlideDeckPreviewProps {
  presentation: GeneratedPresentation
  selectedPath: string | null
  onSelectSlide: (path: string | null) => void
}

export default function SlideDeckPreview({
  presentation,
  selectedPath,
  onSelectSlide,
}: SlideDeckPreviewProps) {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-lg font-semibold text-gray-800">{presentation.title}</h2>
        <p className="text-sm text-gray-400 mt-1">{presentation.slides.length} slides</p>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {presentation.slides.map((slide, idx) => {
          const path = `slides.${idx}`
          const isSelected = selectedPath === path

          return (
            <div
              key={idx}
              onClick={() => onSelectSlide(isSelected ? null : path)}
              className={`
                group relative bg-white rounded-xl cursor-pointer transition-all aspect-[16/10] p-5 flex flex-col
                ${isSelected
                  ? 'ring-2 ring-primary-500 ring-offset-2 shadow-soft-md'
                  : 'border border-gray-200 hover:border-gray-300 hover:shadow-soft'
                }
              `}
            >
              {/* Slide number */}
              <div className="absolute top-2 right-2.5">
                <span className={`text-xs font-medium ${isSelected ? 'text-primary-500' : 'text-gray-300'}`}>
                  {idx + 1}
                </span>
              </div>

              {isSelected && (
                <div className="absolute -top-2 -left-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-primary-500 text-white shadow-sm">
                    Selected
                  </span>
                </div>
              )}

              {/* Slide content */}
              <div className="flex-1 flex flex-col justify-center min-h-0">
                <div className={`text-xs font-medium uppercase tracking-wider mb-1.5 ${
                  isSelected ? 'text-primary-400' : 'text-gray-400'
                }`}>
                  {slide.type.replace('_', ' ')}
                </div>
                <h3 className="font-semibold text-gray-800 text-sm leading-snug mb-2 line-clamp-2">
                  {slide.title}
                </h3>
                {slide.subtitle && (
                  <p className="text-xs text-gray-500 mb-2 line-clamp-1">{slide.subtitle}</p>
                )}
                {slide.bullets && slide.bullets.length > 0 && (
                  <ul className="space-y-0.5 mt-auto">
                    {slide.bullets.slice(0, 3).map((bullet, bIdx) => (
                      <li key={bIdx} className="text-xs text-gray-500 flex items-start gap-1.5">
                        <span className="text-primary-400 mt-0.5">•</span>
                        <span className="line-clamp-1">{bullet}</span>
                      </li>
                    ))}
                    {slide.bullets.length > 3 && (
                      <li className="text-xs text-gray-400 italic pl-3.5">
                        +{slide.bullets.length - 3} more
                      </li>
                    )}
                  </ul>
                )}
                {slide.findings && slide.findings.length > 0 && (
                  <ul className="space-y-0.5 mt-auto">
                    {slide.findings.slice(0, 3).map((finding, fIdx) => (
                      <li key={fIdx} className="text-xs text-gray-500 flex items-start gap-1.5">
                        <span className="text-accent-400 mt-0.5">✦</span>
                        <span className="line-clamp-1">{finding}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
