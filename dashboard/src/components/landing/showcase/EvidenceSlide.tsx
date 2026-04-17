/**
 * EvidenceSlide — one card in the Proof Wall carousel.
 *
 * 4:5 vertical aspect, photo on top, metadata below. BlurHash placeholder
 * keeps CLS at zero while the JPEG streams in. Click opens a lightbox.
 */

import { memo, useEffect, useRef, useState } from 'react'
import { decode as decodeBlurhash } from 'blurhash'
import { safeSrc } from '../../../lib/safeHref'
import type { ShowcaseEvidence } from '../../../services/showcase'
import { PaymentBadge } from './PaymentBadge'
import { VerificationBadges } from './VerificationBadges'

interface EvidenceSlideProps {
  evidence: ShowcaseEvidence
  index: number
  total: number
  eager?: boolean
  onOpen: (evidence: ShowcaseEvidence) => void
  animatePrice?: boolean
}

function drawBlurhashToCanvas(canvas: HTMLCanvasElement, hash: string) {
  const width = 32
  const height = 40 // 4:5 ratio keeps aspect
  try {
    const pixels = decodeBlurhash(hash, width, height)
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const imageData = ctx.createImageData(width, height)
    imageData.data.set(pixels)
    canvas.width = width
    canvas.height = height
    ctx.putImageData(imageData, 0, 0)
  } catch {
    // Invalid hash — silently ignore, the slate fallback still covers the area.
  }
}

export const EvidenceSlide = memo(function EvidenceSlide({
  evidence,
  index,
  total,
  eager = false,
  onOpen,
  animatePrice = false,
}: EvidenceSlideProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!canvasRef.current || !evidence.evidence.blurhash) return
    drawBlurhashToCanvas(canvasRef.current, evidence.evidence.blurhash)
  }, [evidence.evidence.blurhash])

  const imgSrc = safeSrc(evidence.evidence.primaryImageUrl)
  const alt = `${evidence.taskTitle} — ${evidence.category.replace(/_/g, ' ')} evidence${
    evidence.executor.displayName ? ` by ${evidence.executor.displayName}` : ''
  }`
  const categoryLabel = evidence.category.replace(/_/g, ' ')

  return (
    <article
      role="group"
      aria-roledescription="slide"
      aria-label={`${index + 1} of ${total}`}
      className="flex-[0_0_85%] sm:flex-[0_0_60%] md:flex-[0_0_42%] lg:flex-[0_0_32%] min-w-0 pl-4 first:pl-4 last:pr-4"
      data-testid="evidence-slide"
    >
      <button
        type="button"
        onClick={() => onOpen(evidence)}
        className="group w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 dark:focus-visible:ring-white"
        aria-label={`Open evidence: ${alt}`}
      >
        <div className="relative w-full aspect-[4/5] overflow-hidden bg-slate-100 dark:bg-slate-900">
          {/* Blurhash placeholder */}
          {evidence.evidence.blurhash && !loaded && (
            <canvas
              ref={canvasRef}
              aria-hidden="true"
              className="absolute inset-0 w-full h-full"
              style={{ imageRendering: 'pixelated' }}
            />
          )}

          {imgSrc && (
            <img
              src={imgSrc}
              alt={alt}
              loading={eager ? 'eager' : 'lazy'}
              decoding="async"
              // React 18 does not recognize fetchPriority — pass as string prop.
              {...({ fetchpriority: eager ? 'high' : 'auto' } as Record<string, string>)}
              onLoad={() => setLoaded(true)}
              className={`relative w-full h-full object-cover transition-opacity duration-300 ${
                loaded ? 'opacity-100' : 'opacity-0'
              }`}
            />
          )}

          {/* Scan-line hover affordance (motion-gated by CSS) */}
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/70 opacity-0 group-hover:opacity-100 motion-safe:group-hover:animate-[scanline_600ms_ease-out_forwards] motion-reduce:hidden"
          />

          {/* Bottom-row chips anchored inside the photo area */}
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 px-3 py-2 bg-gradient-to-t from-black/60 via-black/20 to-transparent">
            <span className="font-mono text-[10px] uppercase tracking-widest text-white/90">
              {categoryLabel}
            </span>
            {evidence.paymentNetwork && (
              <span className="font-mono text-[10px] lowercase tracking-wider text-white/90">
                {evidence.paymentNetwork}
              </span>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2.5">
          <PaymentBadge
            amountUsd={evidence.bountyUsd}
            token={evidence.paymentToken}
            network={evidence.paymentNetwork}
            paidAt={evidence.paidAt}
            animate={animatePrice}
          />

          <h3 className="font-mono text-sm font-medium leading-snug text-slate-900 dark:text-white line-clamp-2">
            {evidence.taskTitle}
          </h3>

          {evidence.taskDescription && (
            <p className="font-mono text-xs leading-relaxed text-slate-500 dark:text-slate-400 line-clamp-2">
              {evidence.taskDescription}
            </p>
          )}

          <div className="flex items-center justify-between gap-3 pt-1">
            <div className="flex items-center gap-2 min-w-0">
              {evidence.executor.avatarUrl ? (
                <img
                  src={safeSrc(evidence.executor.avatarUrl)}
                  alt=""
                  aria-hidden="true"
                  className="w-5 h-5 rounded-full grayscale object-cover"
                />
              ) : (
                <span
                  aria-hidden="true"
                  className="w-5 h-5 rounded-full bg-slate-200 dark:bg-slate-800"
                />
              )}
              <span className="font-mono text-xs text-slate-700 dark:text-slate-300 truncate">
                {evidence.executor.displayName || 'anonymous'}
              </span>
              {evidence.executor.rating !== null &&
                Number.isFinite(evidence.executor.rating) && (
                  <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                    {evidence.executor.rating.toFixed(1)}
                  </span>
                )}
            </div>
            <VerificationBadges verification={evidence.evidence.verification} />
          </div>
        </div>
      </button>
    </article>
  )
})
