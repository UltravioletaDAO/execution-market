/**
 * EvidenceCarousel — the "Proof Wall" on the landing page.
 *
 * Renders the last N accepted+paid evidence submissions as 4:5 cards that
 * idle-drift every 6s. Pause on hover; if the user prefers reduced motion,
 * autoplay is disabled entirely.
 *
 * If the backend returns fewer than MIN_ITEMS_TO_RENDER, the whole section
 * returns null so the landing never shows a half-empty wall (see plan,
 * "Empty state gate").
 *
 * This is a **default export** so it plays nicely with `React.lazy`.
 */

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import useEmblaCarousel from 'embla-carousel-react'
import Autoplay from 'embla-carousel-autoplay'
import { useShowcaseData } from '../../hooks/useShowcaseData'
import { useReducedMotion } from '../../hooks/useReducedMotion'
import { EvidenceModal } from '../EvidenceModal'
import type { ShowcaseEvidence } from '../../services/showcase'
import { EvidenceSlide } from './showcase/EvidenceSlide'
import { CarouselSkeleton } from './showcase/CarouselSkeleton'

const MIN_ITEMS_TO_RENDER = 5
const AUTOPLAY_DELAY_MS = 6000
const RESUME_AFTER_INTERACTION_MS = 20_000

interface EvidenceCarouselProps {
  /** Override the default page size (useful for tests). */
  limit?: number
}

function EvidenceCarousel({ limit = 12 }: EvidenceCarouselProps) {
  const reducedMotion = useReducedMotion()
  const { data, isLoading, isError } = useShowcaseData({ limit, order: 'recent' })

  const items = data?.items ?? []
  const slides = useMemo(() => items, [items])

  const autoplayRef = useRef(
    Autoplay({
      delay: AUTOPLAY_DELAY_MS,
      stopOnInteraction: false,
      stopOnMouseEnter: true,
      playOnInit: !reducedMotion,
    })
  )

  const [emblaRef, emblaApi] = useEmblaCarousel(
    {
      loop: true,
      align: 'start',
      containScroll: 'trimSnaps',
      dragFree: false,
      skipSnaps: false,
    },
    reducedMotion ? [] : [autoplayRef.current]
  )

  const [activeIndex, setActiveIndex] = useState(0)
  const [lightbox, setLightbox] = useState<ShowcaseEvidence | null>(null)

  useEffect(() => {
    if (!emblaApi) return
    const sync = () => setActiveIndex(emblaApi.selectedScrollSnap())
    sync()
    emblaApi.on('select', sync)
    emblaApi.on('reInit', sync)
    return () => {
      emblaApi.off('select', sync)
      emblaApi.off('reInit', sync)
    }
  }, [emblaApi])

  // Pause autoplay for RESUME_AFTER_INTERACTION_MS whenever the user touches
  // the carousel, then resume. Embla's stopOnInteraction is too binary.
  useEffect(() => {
    if (!emblaApi || reducedMotion) return
    const autoplay = autoplayRef.current
    let timer: number | null = null

    const pauseThenResume = () => {
      autoplay.stop()
      if (timer !== null) window.clearTimeout(timer)
      timer = window.setTimeout(() => autoplay.play(), RESUME_AFTER_INTERACTION_MS)
    }

    emblaApi.on('pointerDown', pauseThenResume)
    emblaApi.on('select', pauseThenResume)

    return () => {
      emblaApi.off('pointerDown', pauseThenResume)
      emblaApi.off('select', pauseThenResume)
      if (timer !== null) window.clearTimeout(timer)
    }
  }, [emblaApi, reducedMotion])

  const handleOpen = useCallback((evidence: ShowcaseEvidence) => {
    setLightbox(evidence)
  }, [])

  const handleClose = useCallback(() => {
    setLightbox(null)
  }, [])

  const handlePrev = useCallback(() => emblaApi?.scrollPrev(), [emblaApi])
  const handleNext = useCallback(() => emblaApi?.scrollNext(), [emblaApi])

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        handlePrev()
      } else if (event.key === 'ArrowRight') {
        event.preventDefault()
        handleNext()
      }
    },
    [handlePrev, handleNext]
  )

  if (isLoading) return <CarouselSkeleton />

  // Honest hiding: if the DB doesn't have enough verified submissions yet,
  // don't render a half-empty wall. The endpoint is still live for debugging.
  if (isError || slides.length < MIN_ITEMS_TO_RENDER) return null

  const liveIndicatorLabel = `Slide ${activeIndex + 1} of ${slides.length}`

  return (
    <section
      aria-roledescription="carousel"
      aria-label="Verified evidence showcase"
      className="my-16 min-h-[520px] md:min-h-[480px]"
      data-testid="evidence-carousel"
    >
      <header className="mb-8 flex flex-col gap-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400">
          LIVE · PROOF OF WORK
        </span>
        <h2 className="font-mono text-2xl sm:text-3xl font-semibold text-slate-900 dark:text-white">
          Every photo on this wall was paid for.
        </h2>
        <p className="font-mono text-sm text-slate-600 dark:text-slate-400 max-w-2xl">
          Agents post tasks. Humans and robots complete them. Settlement is 500ms.
          Scroll the last {slides.length}.
        </p>
      </header>

      <div
        ref={emblaRef}
        className="overflow-hidden focus:outline-none"
        tabIndex={0}
        onKeyDown={handleKeyDown}
        aria-label="Evidence carousel — use arrow keys to navigate"
      >
        <div className="flex -ml-4">
          {slides.map((evidence, index) => (
            <EvidenceSlide
              key={evidence.id}
              evidence={evidence}
              index={index}
              total={slides.length}
              eager={index === 0}
              animatePrice={index === activeIndex && !reducedMotion}
              onOpen={handleOpen}
            />
          ))}
        </div>
      </div>

      {/* Polite live region announces slide changes for screen readers */}
      <div aria-live="polite" className="sr-only">
        {liveIndicatorLabel}
      </div>

      {lightbox && (
        <EvidenceModal
          imageUrl={lightbox.evidence.primaryImageUrl}
          alt={`${lightbox.taskTitle} — evidence photograph`}
          onClose={handleClose}
        />
      )}
    </section>
  )
}

// Exported wrapper that also works stand-alone with Suspense if ever needed.
export function EvidenceCarouselWithSuspense(props: EvidenceCarouselProps) {
  return (
    <Suspense fallback={<CarouselSkeleton />}>
      <EvidenceCarousel {...props} />
    </Suspense>
  )
}

export { EvidenceCarousel }
export default EvidenceCarousel
