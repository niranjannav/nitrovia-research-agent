import { z } from 'zod'
import type { TamboComponent } from '@tambo-ai/react'
import DataChart from './DataChart'
import DataTable from './DataTable'
import DataSummary from './DataSummary'

export const dataAnalysisComponents: TamboComponent[] = [
  {
    name: 'DataChart',
    description:
      'Renders a chart (bar, line, or pie) from structured data. Use this when the user asks to visualize, plot, or chart data. The data array should contain objects with the keys referenced by xKey and yKeys.',
    component: DataChart,
    propsSchema: z.object({
      title: z.string().describe('Chart title'),
      chartType: z
        .enum(['bar', 'line', 'pie'])
        .describe('Type of chart to render'),
      data: z
        .array(z.unknown())
        .describe('Array of data objects for the chart'),
      xKey: z.string().describe('Key in data objects for the X axis / labels'),
      yKeys: z
        .array(z.string())
        .describe('Keys in data objects for Y axis values'),
    }),
  },
  {
    name: 'DataTable',
    description:
      'Renders a filtered or sorted sub-table from the data. Use this when the user asks to filter, sort, search, or display specific rows or columns from the dataset.',
    component: DataTable,
    propsSchema: z.object({
      title: z.string().describe('Table title describing the filter/view'),
      headers: z.array(z.string()).describe('Column headers to display'),
      rows: z
        .array(z.unknown())
        .describe('Array of row objects matching the headers'),
    }),
  },
  {
    name: 'DataSummary',
    description:
      'Displays summary statistics as cards. Use this when the user asks for summary, overview, averages, totals, counts, or statistical analysis of the data.',
    component: DataSummary,
    propsSchema: z.object({
      title: z.string().describe('Summary title'),
      stats: z
        .array(
          z.object({
            label: z.string().describe('Stat label'),
            value: z
              .union([z.string(), z.number()])
              .describe('Stat value'),
            change: z
              .string()
              .optional()
              .describe('Optional change indicator text'),
            changeType: z
              .enum(['positive', 'negative', 'neutral'])
              .optional()
              .describe('Change direction for styling'),
          })
        )
        .describe('Array of statistics to display'),
      description: z
        .string()
        .optional()
        .describe('Optional description text below the title'),
    }),
  },
]
