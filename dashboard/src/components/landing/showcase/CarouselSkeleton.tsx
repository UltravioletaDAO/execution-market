/**
 * CarouselSkeleton — Suspense fallback for EvidenceCarousel.
 *
 * Reserves the exact min-height the real carousel will take so loading never
 * pushes content down (CLS = 0). Pure structural placeholder — no shimmer.
 */

import { memo } from 'react'

const SLOTS = [0, 1, 2]

export const CarouselSkeleton = memo(function CarouselSkeleton() {
  return (
    <section
      aria-hidden="true"
      className="my-16 min-h-[520px] md:min-h-[480px]"
      data-testid="carousel-skeleton"
    >
      <div className="mb-6 flex flex-col gap-2">
        <span className="h-2.5 w-40 bg-slate-200 dark:bg-slate-800" />
        <span className="h-6 w-80 bg-slate-200 dark:bg-slate-800" />
      </div>
      <div className="flex gap-4 overflow-hidden">
        {SLOTS.map((i) => (
          <div
            key={i}
            className="flex-[0_0_85%] sm:flex-[0_0_60%] md:flex-[0_0_42%] lg:flex-[0_0_32%]"
          >
            <div className="w-full aspect-[4/5] bg-slate-100 dark:bg-slate-900" />
            <div className="mt-3 h-8 w-24 bg-slate-200 dark:bg-slate-800" />
            <div className="mt-2 h-4 w-full bg-slate-100 dark:bg-slate-900" />
          </div>
        ))}
      </div>
    </section>
  )
})
