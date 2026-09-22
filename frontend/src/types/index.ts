export interface LogEntry { id: number; timestamp: string; level: string; source: string; message: string; raw: string }
export interface TimeWindow { start: number; end: number; count: number; levels: Record<string,number>; sources: Record<string,number> }
export interface AnomalyScore { windowIndex: number; sigmaScore: number; iqrScore: number; isAnomaly: boolean; timestamp: string }
export interface AlertRule { id: number; name: string; type: string; threshold: number; enabled: boolean }
export interface Alert { id: number; ruleName: string; severity: string; message: string; timestamp: string }
export interface AnalysisResult { logs: LogEntry[]; windows: TimeWindow[]; anomalies: AnomalyScore[]; alerts: Alert[]; totalLogs: number }

// ---- 大屏数据权限 ----
export type GrantDimension = 'source' | 'level'
export type GrantAction = 'allow' | 'deny'
export interface Grant { dimension: GrantDimension; value: string; action: GrantAction }
export interface EffectiveScope { sources: string[]; levels: string[] }
export interface ScreenAccount {
  account: string
  name: string
  enabled: boolean
  version: number
  updatedAt: string
  grants: Grant[]
  effectiveScope: EffectiveScope
}
export interface ScreenCatalog { sources: string[]; levels: string[] }
export interface ScreenData {
  account: string
  version: number
  generatedAt: string
  scope: EffectiveScope
  totalLogs: number
  sourceCounts: Record<string, number>
  levelCounts: Record<string, number>
  windows: TimeWindow[]
  anomalies: AnomalyScore[]
  alerts: Alert[]
  logs: LogEntry[]
}
export interface ScreenApiError {
  code: string
  message: string
  errors?: string[]
  denied?: { dimension: string; value: string }[]
  version?: number
}
