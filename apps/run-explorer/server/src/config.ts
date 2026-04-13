import { join } from 'path'

export const PORT = parseInt(process.env['BUN_PORT'] ?? '3001', 10)

export const ORCH_BASE_DIR = '/tmp/caf_orch'

export const EVENTS_DB_PATH = join(import.meta.dir, '../../../../apps/observability/server/events.db')

export const RECENT_EVENTS_LIMIT = 10

export const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Content-Type': 'application/json',
}
