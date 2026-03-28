interface SkeletonCardProps {
  className?: string
}

export function SkeletonCard({ className = '' }: SkeletonCardProps) {
  return (
    <div className={`bg-gray-800 rounded-lg p-6 ${className}`}>
      <div className="animate-pulse space-y-4">
        <div className="h-4 bg-gray-700 rounded w-1/3" />
        <div className="h-8 bg-gray-700 rounded w-1/2" />
        <div className="h-3 bg-gray-700 rounded w-2/3" />
      </div>
    </div>
  )
}

interface SkeletonTableProps {
  rows?: number
  columns?: number
  className?: string
}

export function SkeletonTable({ rows = 5, columns = 6, className = '' }: SkeletonTableProps) {
  return (
    <div className={`bg-gray-800 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gray-700 px-6 py-3 flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <div key={`h-${i}`} className="h-4 bg-gray-600 rounded animate-pulse flex-1" />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={`r-${rowIdx}`}
          className="px-6 py-4 flex gap-4 border-t border-gray-700"
        >
          {Array.from({ length: columns }).map((_, colIdx) => (
            <div
              key={`c-${rowIdx}-${colIdx}`}
              className="h-4 bg-gray-700 rounded animate-pulse flex-1"
              style={{ animationDelay: `${(rowIdx * columns + colIdx) * 50}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

interface SkeletonTextProps {
  lines?: number
  className?: string
}

export function SkeletonText({ lines = 3, className = '' }: SkeletonTextProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={`l-${i}`}
          className="h-4 bg-gray-700 rounded animate-pulse"
          style={{
            width: i === lines - 1 ? '60%' : '100%',
            animationDelay: `${i * 100}ms`,
          }}
        />
      ))}
    </div>
  )
}
