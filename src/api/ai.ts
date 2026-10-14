import { request } from './client'
import type {
  AIAnswer,
  AIQueryAnswer,
  AIQuerySuggestion,
  Porcelain,
} from '../types/porcelain'
function context(p: Porcelain) {
  return {
    porcelainId: p.id,
    category: p.category,
    context:
      p.dynasty === 'unknown'
        ? JSON.stringify({
            visibleFeatures: p.formFeatures,
            decoration: p.decorationFeatures,
            category: p.category,
          })
        : '',
  }
}
export function fetchPartExplanation(
  p: Porcelain,
  partId: string,
  signal?: AbortSignal,
): Promise<AIAnswer> {
  return request('/ask/part', {
    method: 'POST',
    body: JSON.stringify({ ...context(p), partId }),
    signal,
  })
}
export function fetchSuggestions(): Promise<AIQuerySuggestion[]> {
  return request('/ask/suggestions')
}
export function askQuestion(
  question: string,
  p?: Porcelain,
  signal?: AbortSignal,
): Promise<AIQueryAnswer> {
  return request('/ask', {
    method: 'POST',
    body: JSON.stringify({ question, ...(p ? context(p) : {}) }),
    signal,
  })
}
