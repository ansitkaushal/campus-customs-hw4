/**
 * Merch badges for product cards ("Fan Favorite", "New Drop").
 * The catalogue has no sales or release-date data, so these are hand-picked
 * here. Edit the lists to change which products get a badge.
 */
const FAN_FAVORITES = new Set([
  'basic-hoodie-big-yale',
  'champion-reverse-weave-hoodie-1',
  'yale-grandpa-crewneck',
  'boola-boola-t-shirt',
  'yale-mom-hoodie',
])

const NEW_DROPS = new Set(['2025-yale-vs-harvard-t-shirt', 'yale-bowl-t-shirt', 'yale-maplehouse-diana-mockneck'])

export function merchBadge(productId: string): 'Fan Favorite' | 'New Drop' | null {
  if (NEW_DROPS.has(productId)) return 'New Drop'
  if (FAN_FAVORITES.has(productId)) return 'Fan Favorite'
  return null
}
