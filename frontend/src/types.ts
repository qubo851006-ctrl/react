export type Stage =
  | 'idle'
  | 'thinking'
  | 'waiting_files'
  | 'waiting_dept'
  | 'processing'
  | 'waiting_ledger_files'
  | 'processing_ledger'
  | 'waiting_auth_file'
  | 'processing_auth'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface TrainingResult {
  topic: string
  location: string
  date: string
  department: string
  count: number
  category: string
  archive_path: string
  excel_path: string
}
