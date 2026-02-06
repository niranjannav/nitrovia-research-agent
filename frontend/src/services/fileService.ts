import api from './api'
import type { UploadedFile, DriveFile, DriveSelectedFile } from '../types/file'

export const fileService = {
  async uploadFile(file: File): Promise<UploadedFile> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<UploadedFile>('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    return response.data
  },

  async listDriveFiles(folderId?: string): Promise<DriveFile[]> {
    const params = folderId ? { folder_id: folderId } : {}
    const response = await api.get<{ files: DriveFile[] }>('/files/drive/list', { params })
    return response.data.files
  },

  async selectDriveFiles(fileIds: string[]): Promise<DriveSelectedFile[]> {
    const response = await api.post<{ files: DriveSelectedFile[] }>('/files/drive/select', {
      file_ids: fileIds,
    })
    return response.data.files
  },
}
