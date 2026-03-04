import { useState } from 'react'
import type { SchemaMapping } from '../../types/analytics'

interface Props {
  mapping: SchemaMapping
  suggestedName?: string
  onConfirm: (mapping: SchemaMapping, name: string) => void
  onCancel: () => void
  isLoading?: boolean
}

const ROLE_LABELS: Record<string, string> = {
  product_code: 'Product Code',
  product_name: 'Product Name',
  customer_code: 'Customer Code',
  customer_name: 'Customer Name',
  salesperson: 'Salesperson',
  team: 'Team',
  channel: 'Channel',
  region: 'Region',
  revenue: 'Revenue',
  quantity_units: 'Quantity (Units)',
  quantity_litres: 'Quantity (Litres)',
  date_column: 'Date Column',
  metric_column: 'Metric Column',
  group_column: 'Group Column',
  batch_id: 'Batch ID',
  product: 'Product',
  shift: 'Shift',
  line: 'Production Line',
  test_id: 'Test ID',
  result: 'Test Result',
  inspector: 'Inspector',
  transaction_id: 'Transaction ID',
  account: 'Account',
  cost_center: 'Cost Center',
}

const TIME_STRUCTURE_LABELS: Record<string, string> = {
  wide_monthly: 'Wide monthly columns (Jan–Dec per sheet)',
  wide_weekly: 'Wide weekly columns',
  long_date_col: 'Long format — one row per date',
  quarterly_pivot: 'Quarterly pivot (Q1–Q4 columns)',
  annual_only: 'Annual totals only',
}

export default function SchemaMappingReview({
  mapping,
  suggestedName,
  onConfirm,
  onCancel,
  isLoading,
}: Props) {
  const [name, setName] = useState(
    suggestedName || `${mapping.domain.charAt(0).toUpperCase() + mapping.domain.slice(1)} Format`,
  )
  const [columnRoles, setColumnRoles] = useState<Record<string, string>>(mapping.column_roles)
  const [primaryMetric, setPrimaryMetric] = useState(mapping.primary_metric)

  const handleConfirm = () => {
    onConfirm({ ...mapping, column_roles: columnRoles, primary_metric: primaryMetric }, name)
  }

  const updateColumnRole = (role: string, value: string) => {
    setColumnRoles((prev) => ({ ...prev, [role]: value }))
  }

  return (
    <div className="space-y-6">
      {/* Mapping Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Mapping Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
          placeholder="e.g. SMILK Sales Format"
        />
        <p className="text-xs text-gray-500 mt-1">
          This name identifies the Excel format. It will be reused automatically for future uploads.
        </p>
      </div>

      {/* Warnings */}
      {mapping.warnings && mapping.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm font-medium text-amber-800 mb-1">Warnings</p>
          <ul className="text-sm text-amber-700 space-y-1">
            {mapping.warnings.map((w, i) => (
              <li key={i}>• {w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Source Sheets */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-2">Source Sheets Detected</p>
        <div className="flex flex-wrap gap-2">
          {mapping.source_sheets.map((sheet) => (
            <span
              key={sheet}
              className="px-2.5 py-1 bg-primary-50 text-primary-700 rounded-md text-sm border border-primary-200"
            >
              {sheet}
            </span>
          ))}
        </div>
        {mapping.exclude_sheets && mapping.exclude_sheets.length > 0 && (
          <p className="text-xs text-gray-400 mt-2">
            Excluded: {mapping.exclude_sheets.join(', ')}
          </p>
        )}
      </div>

      {/* Time Structure */}
      <div>
        <p className="text-sm font-medium text-gray-700 mb-1">Time Structure</p>
        <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 space-y-1">
          <p>
            <span className="font-medium">Type:</span>{' '}
            <span className="text-primary-700">
              {TIME_STRUCTURE_LABELS[mapping.time_structure.type] || mapping.time_structure.type}
            </span>
          </p>
          {mapping.time_structure.columns && mapping.time_structure.columns.length > 0 && (
            <p>
              <span className="font-medium">Columns:</span>{' '}
              {mapping.time_structure.columns.slice(0, 6).join(', ')}
              {mapping.time_structure.columns.length > 6 &&
                ` … (+${mapping.time_structure.columns.length - 6} more)`}
            </p>
          )}
          {mapping.time_structure.year_source && (
            <p>
              <span className="font-medium">Year from:</span> {mapping.time_structure.year_source}
            </p>
          )}
          {mapping.time_structure.date_column && (
            <p>
              <span className="font-medium">Date column:</span>{' '}
              {mapping.time_structure.date_column}
            </p>
          )}
        </div>
      </div>

      {/* Primary Metric */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Primary Metric</label>
        <input
          type="text"
          value={primaryMetric}
          onChange={(e) => setPrimaryMetric(e.target.value)}
          className="block w-full sm:w-64 px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-primary-500 focus:border-primary-500"
          placeholder="e.g. revenue, quantity_units"
        />
      </div>

      {/* Column Roles */}
      {Object.keys(columnRoles).length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-1">Column Mappings</p>
          <p className="text-xs text-gray-500 mb-3">
            Edit the Excel column name if the AI got it wrong. Leave blank to skip that field.
          </p>
          <div className="space-y-2">
            {Object.entries(columnRoles).map(([role, col]) => (
              <div key={role} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-44 flex-shrink-0">
                  {ROLE_LABELS[role] || role}
                </span>
                <span className="text-gray-400 text-sm">→</span>
                <input
                  type="text"
                  value={col}
                  onChange={(e) => updateColumnRole(role, e.target.value)}
                  className="flex-1 px-2 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Derived Fields */}
      {mapping.derived_fields && Object.keys(mapping.derived_fields).length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Derived Fields</p>
          <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600 space-y-1.5">
            {Object.entries(mapping.derived_fields).map(([field, def]) => (
              <p key={field}>
                <span className="font-medium text-gray-800">{field}</span>
                <span className="text-gray-500">
                  {' '}
                  — {def.method}
                  {def.source && ` from "${def.source}"`}
                  {def.mappings && (
                    <span className="ml-1 text-xs">
                      ({Object.entries(def.mappings).slice(0, 3).map(([k, v]) => `${k}→${v}`).join(', ')}
                      {Object.keys(def.mappings).length > 3 && '…'})
                    </span>
                  )}
                </span>
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isLoading || !name.trim()}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Saving…' : 'Confirm & Upload'}
        </button>
      </div>
    </div>
  )
}
