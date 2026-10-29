import { delay, request, USE_MOCK } from './client'
import { dynasties, getDynastyPorcelain, getPorcelainById } from '../mock/data'
import { getPersonalizedMatches } from '../mock/personalizedEvolutionData'
import type { DynastyId, DynastyInfo, PersonalizedMatch, Porcelain } from '../types/porcelain'

interface TimelineResponse {
  dynasties: DynastyInfo[]
}

interface PersonalizedMatchResponse {
  matches: PersonalizedMatch[]
}

/** 获取时间轴朝代列表。未来对接 `GET /api/timeline`。 */
export async function fetchTimeline(): Promise<DynastyInfo[]> {
  if (USE_MOCK) {
    await delay(120)
    return dynasties
  }
  const response = await request<TimelineResponse>('/timeline')
  return response.dynasties
}

/** 获取单件瓷器详情。未来对接 `GET /api/porcelain/:id`。 */
export async function fetchPorcelain(id: string): Promise<Porcelain> {
  if (USE_MOCK) {
    await delay(120)
    return getPorcelainById(id)
  }
  return request<Porcelain>(`/porcelain/${id}`)
}

/** 获取某朝代的代表性瓷器。未来对接 `GET /api/timeline/:dynasty`。 */
export async function fetchDynastyPorcelain(dynasty: DynastyId): Promise<Porcelain> {
  if (USE_MOCK) {
    await delay(120)
    return getDynastyPorcelain(dynasty)
  }
  return request<Porcelain>(`/timeline/${dynasty}`)
}

/** 获取上传器物的跨朝代历史匹配。 */
export async function fetchPersonalizedMatches(category: string): Promise<PersonalizedMatch[]> {
  if (USE_MOCK) {
    await delay(120)
    return getPersonalizedMatches(category)
  }
  const response = await request<PersonalizedMatchResponse>('/evolution/match', {
    method: 'POST',
    body: JSON.stringify({ category }),
  })
  return response.matches
}
