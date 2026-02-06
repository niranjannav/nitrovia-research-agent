export interface UploadedFile {
  file_id: string
  file_name: string
  file_type: string
  file_size: number
  storage_path: string
}

export interface DriveFile {
  id: string
  name: string
  mimeType: string
  size: number | null
}

export interface DriveSelectedFile {
  file_id: string
  file_name: string
  status: string
}

export interface SourceFile {
  id: string
  name: string
  type: string
  size: number
  source: 'upload' | 'google_drive'
}
