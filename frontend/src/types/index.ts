export interface LogEntry { id: number; timestamp: string; level: string; source: string; message: string; raw: string }
export interface TimeWindow { start: number; end: number; count: number; levels: Record<string,number>; sources: Record<string,number> }
export interface AnomalyScore { windowIndex: number; sigmaScore: number; iqrScore: number; isAnomaly: boolean; timestamp: string }
export interface AlertRule { id: number; name: string; type: string; threshold: number; enabled: boolean }
export interface Alert { id: number; ruleName: string; severity: string; message: string; timestamp: string }
export interface AnalysisResult { logs: LogEntry[]; windows: TimeWindow[]; anomalies: AnomalyScore[]; alerts: Alert[]; totalLogs: number }

// ---- 数据权限 / 大屏 ----
export type Effect = 'allow' | 'deny'
export interface ScopeEntry { resource: string; effect: Effect }
export interface Scope { version: number; enabled: boolean; entries: ScopeEntry[] }
export interface AccountInfo {
  username: string; name: string; role: string; isAdmin: boolean
  scope: Scope | null
  resourceCatalog: { sources: string[]; panels: string[] }
}
export interface ScreenPanel {
  panel: string
  title: string
  status: 'granted' | 'denied'
  denyReason: string | null
  // 各面板 data 形态不同，由具体面板组件按需取值
  data: Record<string, unknown> | null
}
export interface ScreenData {
  account: { username: string; name: string; role: string }
  logType: string
  scope: { version: number; enabled: boolean }
  sources: { granted: string[]; denied: string[] }
  panels: ScreenPanel[]
}
