import { readFile, readdir } from 'fs/promises'
import { join } from 'path'

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length
}

export function estimateTokens(text: string): number {
  return Math.ceil(wordCount(text) * 1.3)
}

export async function estimateFileTokens(filePath: string): Promise<number> {
  try {
    const text = await readFile(filePath, 'utf-8')
    return estimateTokens(text)
  } catch {
    return 0
  }
}

async function collectMdFiles(dirPath: string): Promise<string[]> {
  const results: string[] = []
  let entries: string[]
  try {
    entries = await readdir(dirPath)
  } catch {
    return results
  }
  for (const entry of entries) {
    const full = join(dirPath, entry)
    if (entry.endsWith('.md')) {
      results.push(full)
    } else {
      // recurse into subdirectories
      try {
        const sub = await readdir(full)
        if (sub.length >= 0) {
          const nested = await collectMdFiles(full)
          results.push(...nested)
        }
      } catch {
        // not a directory, skip
      }
    }
  }
  return results
}

export async function estimateDirectoryTokens(dirPath: string): Promise<number> {
  const files = await collectMdFiles(dirPath)
  const counts = await Promise.all(files.map(estimateFileTokens))
  return counts.reduce((sum, n) => sum + n, 0)
}
