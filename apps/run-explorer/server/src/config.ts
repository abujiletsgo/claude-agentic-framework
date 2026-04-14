import { homedir } from 'node:os'
import { join } from 'path'
import os from 'os'

export const PORT = parseInt(process.env.RUN_EXPLORER_PORT ?? '3001', 10)

export const ORCH_BASE_DIR = process.env.CAF_ORCH_DIR ?? join(os.homedir(), '.caf', 'orch')

export const SESSIONS_BASE_DIR = process.env.CAF_SESSIONS_DIR ?? join(os.homedir(), '.caf', 'sessions')

export const EVENTS_DB_PATH = process.env.CAF_EVENTS_DB ?? join(homedir(), '.caf', 'events.db')

export const RECENT_EVENTS_LIMIT = 10

export const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Content-Type': 'application/json',
}
