/**
 * Minimal markdown-to-HTML converter.
 * Handles: headers (h1-h4), bold, inline code, code blocks, bullet lists, ordered lists, hr, paragraphs.
 * No external dependency — avoids adding marked to the bundle.
 */
export function renderMarkdown(md: string): string {
  if (!md) return ''

  // Escape HTML first to prevent XSS in raw content
  function escapeHtml(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  // Process fenced code blocks first (preserve content as-is)
  const codeBlocks: string[] = []
  let result = md.replace(/```([^\n]*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    const langClass = lang ? ` class="language-${escapeHtml(lang.trim())}"` : ''
    const placeholder = `\x00CODEBLOCK${codeBlocks.length}\x00`
    codeBlocks.push(`<pre class="whitespace-pre-wrap text-xs font-mono bg-slate-900/50 rounded-xl p-4 overflow-auto my-3"><code${langClass}>${escapeHtml(code)}</code></pre>`)
    return placeholder
  })

  // Escape remaining HTML
  result = escapeHtml(result)

  // Headers
  result = result.replace(/^#### (.+)$/gm, '<h4 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mt-4 mb-1">$1</h4>')
  result = result.replace(/^### (.+)$/gm, '<h3 class="text-sm font-bold text-slate-700 dark:text-slate-300 mt-4 mb-1">$1</h3>')
  result = result.replace(/^## (.+)$/gm, '<h2 class="text-base font-bold text-slate-800 dark:text-slate-200 mt-5 mb-2">$1</h2>')
  result = result.replace(/^# (.+)$/gm, '<h1 class="text-lg font-bold text-slate-900 dark:text-white mt-5 mb-2">$1</h1>')

  // Horizontal rules
  result = result.replace(/^---+$/gm, '<hr class="border-slate-200 dark:border-slate-700 my-4" />')

  // Bold and italic
  result = result.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-slate-800 dark:text-slate-200">$1</strong>')
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Inline code
  result = result.replace(/`([^`]+)`/g, '<code class="text-xs font-mono bg-slate-100 dark:bg-slate-800 text-violet-700 dark:text-violet-300 px-1 py-0.5 rounded">$1</code>')

  // Bullet lists — collect consecutive list lines into <ul>
  result = result.replace(/((?:^[ \t]*[-*+] .+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map((line) => {
      const text = line.replace(/^[ \t]*[-*+] /, '')
      return `<li class="ml-4 list-disc">${text}</li>`
    })
    return `<ul class="my-2 space-y-0.5 text-slate-600 dark:text-slate-400">${items.join('')}</ul>`
  })

  // Ordered lists
  result = result.replace(/((?:^[ \t]*\d+\. .+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map((line) => {
      const text = line.replace(/^[ \t]*\d+\. /, '')
      return `<li class="ml-4 list-decimal">${text}</li>`
    })
    return `<ol class="my-2 space-y-0.5 text-slate-600 dark:text-slate-400">${items.join('')}</ol>`
  })

  // Paragraphs: wrap lines that aren't block-level elements
  const lines = result.split('\n')
  const output: string[] = []
  let inParagraph = false
  for (const line of lines) {
    const isBlock = /^\x00CODEBLOCK|^<h[1-6]|^<ul|^<ol|^<li|^<hr|^<pre/.test(line)
    if (isBlock) {
      if (inParagraph) { output.push('</p>'); inParagraph = false }
      output.push(line)
    } else if (line.trim() === '') {
      if (inParagraph) { output.push('</p>'); inParagraph = false }
    } else {
      if (!inParagraph) { output.push('<p class="text-sm text-slate-600 dark:text-slate-400 leading-relaxed my-1">'); inParagraph = true }
      output.push(line)
    }
  }
  if (inParagraph) output.push('</p>')
  result = output.join('\n')

  // Restore code blocks
  codeBlocks.forEach((block, i) => {
    result = result.replace(`\x00CODEBLOCK${i}\x00`, block)
  })

  return result
}
