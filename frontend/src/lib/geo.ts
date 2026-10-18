/* Map layout for the seeded world. Positions only, never data. */
// Schematic positions (lon, lat) for the seeded world's cities, nudged so neighbours do not overlap. Layout only.
export const GEO: Record<string, [number, number]> = {
  Ayutthaya: [100.6, 14.6], Chonburi: [101.4, 12.9], Penang: [100.2, 5.6], 'Johor Bahru': [103.8, 1.6],
  'Hai Phong': [106.9, 20.6], Shenzhen: [114.5, 22.3], Dongguan: [113.2, 23.3], Wuhan: [114.3, 30.6],
  Shanghai: [121.8, 30.9], Suzhou: [120.3, 31.7], Taichung: [120.3, 24.1], Hsinchu: [121.3, 25.2], Tainan: [120.1, 22.8],
  Suwon: [126.7, 37.5], Cheongju: [127.6, 36.5], Gumi: [128.8, 35.7], Kumamoto: [130.8, 32.6],
}
export const PLANT_GEO: Record<string, [number, number]> = { 'PL-PEN': [101.3, 4.5], 'PL-BAC': [105.6, 21.9] }

/* The map plane: coastlines (lon, lat), a tilted isometric projection and the SVG view box. Layout only. */
export const LAND: [number, number][][] = [
  [[97, 41], [122, 41], [121.5, 39], [118.5, 38.5], [119, 37], [122.5, 37], [120, 35], [121.5, 32], [122, 29.5], [120, 26], [117, 23.5], [113.5, 22], [110, 21.2], [108.5, 21.6], [106, 20], [106.6, 17], [109, 15], [109.2, 11.6], [105, 8.6], [104.6, 10.5], [102.8, 12], [101, 12.6], [100, 13.4], [99.3, 10.5], [100.2, 8], [101.6, 6.6], [103.4, 4], [104.3, 1.4], [103.4, 1.2], [101, 2.9], [100.3, 5], [99, 7.6], [98.4, 9.6], [97.8, 13], [97, 16]],
  [[124.6, 40], [128.2, 41], [129.6, 37], [129.3, 35.2], [127.2, 34.5], [126.2, 34.6], [126.6, 37], [125.2, 37.8]],
  [[129.6, 33.5], [131, 34.1], [132.2, 34], [134, 34.5], [134, 33.5], [132, 32.8], [131.4, 31.3], [130.2, 31.2], [129.8, 32.7]],
  [[121.1, 25.3], [122, 25], [121.4, 22.4], [120.7, 21.9], [120.1, 23], [120.2, 24.3]],
  [[108.6, 19.2], [110.3, 20.1], [111, 19.6], [109.6, 18.2]],
  [[120.6, 18.5], [122.2, 18.5], [122, 16], [121.5, 14], [120.5, 14.4], [120, 16]],
  [[115.5, 5], [116.8, 7], [119, 5.2], [117.8, 4], [115.4, 4.3]],
  [[97, 5.2], [98, 4], [100.3, 2.2], [102, 0.8], [103, 0], [97, 0]],
]
export const COUNTRY_LABELS: [string, number, number][] = [['Thailand', 101.6, 17.2], ['Malaysia', 102.6, 3.0], ['Vietnam', 105.6, 16.2], ['China', 112, 30.5], ['Taiwan', 122.4, 23.4], ['South Korea', 128.4, 39.4], ['Japan', 132.2, 32.4]]
export const LON0 = 97, LAT0 = 41, GW = 37, GH = 41, SC = 18, TH = (12 * Math.PI) / 180, SQ = 0.68
export const EX = [Math.cos(TH) * SC, Math.sin(TH) * SQ * SC], SY = [-Math.sin(TH) * SC, Math.cos(TH) * SQ * SC]
export const grid = (lon: number, lat: number): [number, number] => [lon - LON0, LAT0 - lat]
export const iso = (gx: number, gy: number, z = 0): [number, number] => [gx * EX[0] + gy * SY[0], gx * EX[1] + gy * SY[1] - z]
export const P = (pts: number[][]) => pts.map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ')
export const VB = { x: -150, y: 0, w: 860, h: 560 }
