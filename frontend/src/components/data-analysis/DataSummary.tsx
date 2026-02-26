interface StatItem {
  label: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
}

interface DataSummaryProps {
  title: string
  stats: StatItem[]
  description?: string
}

export default function DataSummary({ title, stats, description }: DataSummaryProps) {
  if (!stats || stats.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
        No statistics available
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-sm font-semibold text-gray-800 mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-gray-500 mb-3">{description}</p>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {stats.map((stat, i) => (
          <div
            key={i}
            className="bg-gray-50 rounded-lg p-3 border border-gray-100"
          >
            <p className="text-xs text-gray-500 font-medium">{stat.label}</p>
            <p className="text-lg font-bold text-gray-900 mt-0.5">
              {typeof stat.value === 'number'
                ? stat.value.toLocaleString()
                : stat.value}
            </p>
            {stat.change && (
              <p
                className={`text-xs mt-0.5 ${
                  stat.changeType === 'positive'
                    ? 'text-green-600'
                    : stat.changeType === 'negative'
                    ? 'text-red-600'
                    : 'text-gray-500'
                }`}
              >
                {stat.change}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
