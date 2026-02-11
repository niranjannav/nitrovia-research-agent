import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { fileService } from '../../services/fileService'
import { useReportStore } from '../../stores/reportStore'

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
}

const MAX_SIZE = 50 * 1024 * 1024 // 50MB

export default function FileUploader() {
  const { addFile } = useReportStore()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploadError(null)
      setIsUploading(true)

      for (const file of acceptedFiles) {
        try {
          const uploaded = await fileService.uploadFile(file)
          addFile({
            id: uploaded.file_id,
            name: uploaded.file_name,
            type: uploaded.file_type,
            size: uploaded.file_size,
            source: 'upload',
          })
        } catch (error) {
          setUploadError(
            error instanceof Error ? error.message : 'Failed to upload file'
          )
        }
      }

      setIsUploading(false)
    },
    [addFile]
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    multiple: true,
  })

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : isDragReject
            ? 'border-red-400 bg-red-50'
            : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />

        <div className="space-y-2">
          <div className="mx-auto w-12 h-12 text-gray-400">
            <svg
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              className="w-full h-full"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>

          {isUploading ? (
            <p className="text-sm text-gray-600">Uploading...</p>
          ) : isDragActive ? (
            <p className="text-sm text-primary-600">Drop files here</p>
          ) : (
            <>
              <p className="text-sm text-gray-600">
                <span className="text-primary-600 font-medium">Click to upload</span> or
                drag and drop
              </p>
              <p className="text-xs text-gray-500">
                PDF, DOCX, XLSX, PPTX (max 50MB each)
              </p>
            </>
          )}
        </div>
      </div>

      {uploadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {uploadError}
        </div>
      )}
    </div>
  )
}
