import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import DataAnalysisMode from '../components/data-analysis/DataAnalysisMode'
import { parseExcelFile, type ParsedExcelData } from '../utils/excelParser'

export default function DataAnalysisPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<ParsedExcelData | null>(null)
  const [fileName, setFileName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setError(null)
    setIsLoading(true)

    try {
      const parsed = await parseExcelFile(file)
      if (parsed.rows.length === 0) {
        setError('The Excel file appears to be empty.')
        setIsLoading(false)
        return
      }
      setData(parsed)
      setFileName(file.name)
    } catch {
      setError('Failed to parse Excel file. Please ensure it is a valid .xlsx file.')
    }
    setIsLoading(false)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxSize: 50 * 1024 * 1024,
    multiple: false,
  })

  const handleBack = () => {
    setData(null)
    setFileName('')
    setError(null)
  }

  const handleLoadDemo = async () => {
    setError(null)
    setIsLoading(true)
    try {
      const demoData: ParsedExcelData = {
        headers: ['Month', 'Revenue', 'Expenses', 'Profit', 'Customers', 'Region'],
        rows: [
          { Month: 'Jan 2024', Revenue: 52000, Expenses: 38000, Profit: 14000, Customers: 120, Region: 'North' },
          { Month: 'Feb 2024', Revenue: 48000, Expenses: 35000, Profit: 13000, Customers: 115, Region: 'South' },
          { Month: 'Mar 2024', Revenue: 61000, Expenses: 42000, Profit: 19000, Customers: 142, Region: 'North' },
          { Month: 'Apr 2024', Revenue: 55000, Expenses: 40000, Profit: 15000, Customers: 130, Region: 'East' },
          { Month: 'May 2024', Revenue: 67000, Expenses: 45000, Profit: 22000, Customers: 155, Region: 'West' },
          { Month: 'Jun 2024', Revenue: 72000, Expenses: 48000, Profit: 24000, Customers: 168, Region: 'North' },
          { Month: 'Jul 2024', Revenue: 69000, Expenses: 46000, Profit: 23000, Customers: 160, Region: 'South' },
          { Month: 'Aug 2024', Revenue: 74000, Expenses: 49000, Profit: 25000, Customers: 175, Region: 'East' },
          { Month: 'Sep 2024', Revenue: 71000, Expenses: 47000, Profit: 24000, Customers: 165, Region: 'West' },
          { Month: 'Oct 2024', Revenue: 78000, Expenses: 51000, Profit: 27000, Customers: 185, Region: 'North' },
          { Month: 'Nov 2024', Revenue: 82000, Expenses: 54000, Profit: 28000, Customers: 192, Region: 'South' },
          { Month: 'Dec 2024', Revenue: 90000, Expenses: 58000, Profit: 32000, Customers: 210, Region: 'East' },
        ],
        rawRows: [],
        sheetName: 'Sales Data',
      }
      setData(demoData)
      setFileName('demo-sales-data.xlsx')
    } catch {
      setError('Failed to load demo data.')
    }
    setIsLoading(false)
  }

  if (data) {
    return <DataAnalysisMode data={data} fileName={fileName} onBack={handleBack} />
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Analysis</h1>
          <p className="text-gray-600 mt-1">
            Upload an Excel file to explore and analyze your data with AI
          </p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          ← Dashboard
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
        {/* Upload area */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-green-500 bg-green-50'
              : 'border-gray-300 hover:border-green-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />

          <div className="space-y-3">
            <div className="mx-auto w-16 h-16 text-green-500">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" className="w-full h-full">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </div>

            {isLoading ? (
              <div className="space-y-2">
                <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm text-gray-600">Parsing Excel file...</p>
              </div>
            ) : isDragActive ? (
              <p className="text-sm text-green-600 font-medium">Drop your Excel file here</p>
            ) : (
              <>
                <p className="text-sm text-gray-600">
                  <span className="text-green-600 font-medium">Click to upload</span> or drag
                  and drop an Excel file
                </p>
                <p className="text-xs text-gray-500">
                  .xlsx files up to 50MB
                </p>
              </>
            )}
          </div>
        </div>

        {/* Demo data button */}
        <div className="text-center">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white px-3 text-gray-400">or</span>
            </div>
          </div>
          <button
            onClick={handleLoadDemo}
            disabled={isLoading}
            className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 disabled:opacity-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Load Demo Sales Dataset
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Feature description */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
          <FeatureCard
            icon="💬"
            title="Chat with Data"
            description="Ask questions in natural language"
          />
          <FeatureCard
            icon="📊"
            title="Auto Charts"
            description="AI generates charts and graphs"
          />
          <FeatureCard
            icon="📋"
            title="Smart Tables"
            description="Filter and sort with AI"
          />
        </div>
      </div>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string
  title: string
  description: string
}) {
  return (
    <div className="text-center p-3">
      <div className="text-2xl mb-1">{icon}</div>
      <h3 className="text-sm font-medium text-gray-800">{title}</h3>
      <p className="text-xs text-gray-500 mt-0.5">{description}</p>
    </div>
  )
}
