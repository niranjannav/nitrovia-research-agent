import readXlsxFile from 'read-excel-file'

export interface ParsedExcelData {
  headers: string[]
  rows: Record<string, string | number | boolean | null>[]
  rawRows: (string | number | boolean | null)[][]
  sheetName: string
}

/**
 * Parse an Excel file (.xlsx) into structured JSON data.
 * Uses read-excel-file for safe client-side parsing.
 */
export async function parseExcelFile(file: File): Promise<ParsedExcelData> {
  const rows = await readXlsxFile(file)

  if (rows.length === 0) {
    return { headers: [], rows: [], rawRows: [], sheetName: 'Sheet1' }
  }

  const headers = rows[0].map((cell) => String(cell ?? ''))

  const dataRows = rows.slice(1).map((row) => {
    const record: Record<string, string | number | boolean | null> = {}
    headers.forEach((header, i) => {
      const value = row[i]
      record[header] = value !== undefined ? (value as string | number | boolean | null) : null
    })
    return record
  })

  const rawRows = rows.slice(1).map((row) =>
    row.map((cell) => (cell as string | number | boolean | null))
  )

  return {
    headers,
    rows: dataRows,
    rawRows,
    sheetName: 'Sheet1',
  }
}

/**
 * Summarize Excel data for context (keeps it compact for AI).
 */
export function summarizeDataForContext(data: ParsedExcelData): string {
  const { headers, rows } = data
  const rowCount = rows.length
  const colCount = headers.length

  const sampleRows = rows.slice(0, 10)
  const sampleText = sampleRows
    .map((row) =>
      headers.map((h) => `${h}: ${row[h] ?? 'N/A'}`).join(', ')
    )
    .join('\n')

  const columnInfo = headers.map((h) => {
    const values = rows.map((r) => r[h]).filter((v) => v !== null && v !== undefined)
    const numericValues = values.filter((v) => typeof v === 'number') as number[]
    if (numericValues.length > 0) {
      const min = Math.min(...numericValues)
      const max = Math.max(...numericValues)
      const avg = numericValues.reduce((a, b) => a + b, 0) / numericValues.length
      return `${h} (numeric): min=${min}, max=${max}, avg=${avg.toFixed(2)}, count=${numericValues.length}`
    }
    const uniqueValues = [...new Set(values.map(String))]
    return `${h} (text): ${uniqueValues.length} unique values${uniqueValues.length <= 10 ? ` [${uniqueValues.join(', ')}]` : ''}`
  }).join('\n')

  return `Dataset: ${rowCount} rows, ${colCount} columns\n\nColumns:\n${columnInfo}\n\nSample rows (first 10):\n${sampleText}`
}
