import { request } from './client'
import type { DynastyId, DynastyInfo, Porcelain } from '../types/porcelain'
export function fetchTimeline(): Promise<DynastyInfo[]> {
  return request('/timeline')
}
export function fetchPorcelain(id: string): Promise<Porcelain> {
  return request('/porcelain/' + id)
}
export function fetchDynastyPorcelain(dynasty: DynastyId): Promise<Porcelain> {
  return request('/timeline/' + dynasty)
}
