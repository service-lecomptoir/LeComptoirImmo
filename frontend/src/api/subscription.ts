import { apiClient } from './client'

export interface SubscriptionInfo {
  plan_name: string | null
  is_blocked: boolean
  property_limit: number | null
  property_count: number
  can_create_property: boolean
}

export const subscriptionApi = {
  get: () => apiClient.get<SubscriptionInfo>('/subscription'),
}
