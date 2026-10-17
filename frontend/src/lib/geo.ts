/* Map layout for the seeded world. Positions only, never data. */
// Schematic positions (lon, lat) for the seeded world's cities, nudged so neighbours do not overlap. Layout only.
export const GEO: Record<string, [number, number]> = {
  Ayutthaya: [100.6, 14.6], Chonburi: [101.4, 12.9], Penang: [100.2, 5.6], 'Johor Bahru': [103.8, 1.6],
  'Hai Phong': [106.9, 20.6], Shenzhen: [114.5, 22.3], Dongguan: [113.2, 23.3], Wuhan: [114.3, 30.6],
  Shanghai: [121.8, 30.9], Suzhou: [120.3, 31.7], Taichung: [120.3, 24.1], Hsinchu: [121.3, 25.2], Tainan: [120.1, 22.8],
  Suwon: [126.7, 37.5], Cheongju: [127.6, 36.5], Gumi: [128.8, 35.7], Kumamoto: [130.8, 32.6],
}
export const PLANT_GEO: Record<string, [number, number]> = { 'PL-PEN': [101.3, 4.5], 'PL-BAC': [105.6, 21.9] }
