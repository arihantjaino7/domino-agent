"""Fixed reference data for the Kestrel Devices world (PLAN §5.1).

Places are real (approximate coordinates); every company and person is fictional.
Nothing here is random. The generator draws only demand, orders and the filler
supply chains from WORLD_SEED.
"""

from __future__ import annotations

# (id, name, hazard, aliases)
HAZARD_ZONES = [
    ("Z-CPB", "Chao Phraya Basin", "flood", "Chao Phraya River floodplain, Central Thailand"),
    ("Z-KYU", "Kyushu", "quake", "Kyushu island, Kumamoto fault zone"),
    ("Z-STC", "Southern Taiwan coast", "typhoon", "South Taiwan, Kaohsiung Tainan coast"),
    ("Z-PRD", "Pearl River Delta", "typhoon", "PRD, Greater Bay Area, Guangdong"),
    ("Z-GLF", "Gulf Coast", "hurricane", "US Gulf Coast, Texas coast"),
]

# (id, name, country, lat, lng, zone or None, aliases)
REGIONS = [
    ("R-AYU", "Ayutthaya", "TH", 14.35, 100.57, "Z-CPB", "Phra Nakhon Si Ayutthaya, Krung Kao, Rojana"),
    ("R-PTH", "Pathum Thani", "TH", 14.02, 100.53, "Z-CPB", "Rangsit, Navanakorn"),
    ("R-CHB", "Chonburi", "TH", 13.36, 100.98, None, "Laem Chabang, Amata City, Si Racha"),
    ("R-HPG", "Hai Phong", "VN", 20.86, 106.68, None, "Haiphong, Hai Phong City"),
    ("R-BNH", "Bac Ninh", "VN", 21.19, 106.08, None, "Bắc Ninh, Yen Phong, Hanoi area"),
    ("R-PEN", "Penang", "MY", 5.41, 100.33, None, "Pulau Pinang, Bayan Lepas, George Town"),
    ("R-JHB", "Johor Bahru", "MY", 1.49, 103.74, None, "Johor, JB, Iskandar, Tanjung Pelepas"),
    ("R-CJU", "Cheongju", "KR", 36.64, 127.49, None, "Chungcheongbuk-do, Ochang"),
    ("R-SWN", "Suwon", "KR", 37.26, 127.03, None, "Gyeonggi-do, Yeongtong"),
    ("R-GUM", "Gumi", "KR", 36.12, 128.34, None, "Gyeongsangbuk-do"),
    ("R-ICN", "Incheon", "KR", 37.46, 126.44, None, "Incheon, Songdo"),
    ("R-PUS", "Busan", "KR", 35.10, 129.04, None, "Pusan, Busan New Port"),
    ("R-KUM", "Kumamoto", "JP", 32.80, 130.71, "Z-KYU", "Kumamoto, Kikuyo, Kyushu"),
    ("R-FUK", "Fukuoka", "JP", 33.59, 130.40, "Z-KYU", "Hakata, Kyushu"),
    ("R-HSC", "Hsinchu", "TW", 24.80, 120.97, None, "Hsinchu Science Park"),
    ("R-TYN", "Taoyuan", "TW", 25.01, 121.30, None, "Taoyuan, Taipei area"),
    ("R-TXG", "Taichung", "TW", 24.15, 120.67, None, "Central Taiwan Science Park"),
    ("R-KHH", "Kaohsiung", "TW", 22.63, 120.30, "Z-STC", "Kaohsiung, Nanzih"),
    ("R-TNN", "Tainan", "TW", 22.99, 120.21, "Z-STC", "Southern Taiwan Science Park"),
    ("R-SHA", "Shanghai", "CN", 31.23, 121.47, None, "Shanghai, Pudong, Yangshan"),
    ("R-SUZ", "Suzhou", "CN", 31.30, 120.59, None, "Suzhou Industrial Park, Jiangsu"),
    ("R-WUH", "Wuhan", "CN", 30.59, 114.31, None, "Hubei, Optics Valley"),
    ("R-SZX", "Shenzhen", "CN", 22.54, 114.06, "Z-PRD", "Shenzhen, Bao'an, Yantian"),
    ("R-DGN", "Dongguan", "CN", 23.02, 113.75, "Z-PRD", "Dongguan, Songshan Lake"),
    ("R-GDL", "Guadalajara", "MX", 20.67, -103.35, None, "Jalisco, El Salto, Guadalajara"),
    ("R-MZO", "Manzanillo", "MX", 19.05, -104.32, None, "Colima, Manzanillo"),
    ("R-MTY", "Monterrey", "MX", 25.69, -100.32, None, "Nuevo León, Apodaca"),
    ("R-HOU", "Houston", "US", 29.76, -95.37, "Z-GLF", "Houston, Texas, Gulf Coast"),
    ("R-BRN", "Brno", "CZ", 49.20, 16.61, None, "South Moravia, Jihomoravský"),
]

# (id, name, country, kind, region, aliases)
PORTS = [
    ("P-HPH", "Hai Phong Port", "VN", "sea", "R-HPG", "Lach Huyen, Haiphong port"),
    ("P-PEN", "Penang Port", "MY", "sea", "R-PEN", "Butterworth, North Butterworth Container Terminal"),
    ("P-TPP", "Port of Tanjung Pelepas", "MY", "sea", "R-JHB", "PTP, Tanjung Pelepas"),
    ("P-LCB", "Laem Chabang Port", "TH", "sea", "R-CHB", "Laem Chabang, LCB"),
    ("P-KHH", "Port of Kaohsiung", "TW", "sea", "R-KHH", "Kaohsiung harbor, KHH"),
    ("P-TXG", "Port of Taichung", "TW", "sea", "R-TXG", "Taichung harbor"),
    ("P-PUS", "Port of Busan", "KR", "sea", "R-PUS", "Busan New Port, Pusan"),
    ("P-SHA", "Port of Shanghai", "CN", "sea", "R-SHA", "Yangshan, Waigaoqiao"),
    ("P-YTN", "Yantian Port", "CN", "sea", "R-SZX", "Yantian International Container Terminals, Shenzhen port"),
    ("P-HKT", "Hakata Port", "JP", "sea", "R-FUK", "Fukuoka port, Hakata"),
    ("P-ZLO", "Port of Manzanillo", "MX", "sea", "R-MZO", "Manzanillo, Colima port"),
    ("P-HOU", "Port Houston", "US", "sea", "R-HOU", "Houston Ship Channel"),
    ("A-HAN", "Noi Bai International Airport", "VN", "air", "R-BNH", "HAN, Hanoi airport"),
    ("A-PEN", "Penang International Airport", "MY", "air", "R-PEN", "PEN, Bayan Lepas airport"),
    ("A-ICN", "Incheon International Airport", "KR", "air", "R-ICN", "ICN, Seoul Incheon"),
    ("A-TPE", "Taoyuan International Airport", "TW", "air", "R-TYN", "TPE, Taipei Taoyuan"),
    ("A-GDL", "Guadalajara International Airport", "MX", "air", "R-GDL", "GDL, Miguel Hidalgo airport"),
]

# (id, name, country, region, aliases, sea port, air port)
PLANTS = [
    ("PL-BAC", "Kestrel Bac Ninh", "VN", "R-BNH", "Bac Ninh plant, Kestrel Vietnam, BAC", "P-HPH", "A-HAN"),
    ("PL-PEN", "Kestrel Penang", "MY", "R-PEN", "Penang plant, Kestrel Malaysia, PEN", "P-PEN", "A-PEN"),
    ("PL-GDL", "Kestrel Guadalajara", "MX", "R-GDL", "Guadalajara plant, Kestrel Mexico, GDL", "P-ZLO", "A-GDL"),
]

# (id, name, family, unit, unit_cost_cents)
COMPONENTS = [
    # Monsoon battery chain (§5.6)
    ("CELL-21700", "21700 Li-ion cell", "cell", "cells", 350),
    ("BAT-4S", "4S battery pack (KB14)", "battery", "packs", 3800),
    ("BAT-6S", "6S battery pack (KBP16)", "battery", "packs", 5200),
    # Panel Fire display chain (§5.8)
    ("PNL-14", "14-inch LCD panel", "panel", "panels", 2900),
    ("DSP-14", "14-inch display module (KB14)", "display", "modules", 6200),
    ("DSP-14-HB", "14-inch high-brightness display module", "display", "modules", 5900),
    # Filler finished parts (K7 is filler tonight; the Scarce Silicon motif, §5.7, is deferred)
    ("K7", "K7 SoC", "soc", "pcs", 6800),
    ("DSP-16", "16-inch display module", "display", "modules", 9400),
    ("DSP-11", "11-inch display module", "display", "modules", 4800),
    ("DSP-6", "6.1-inch OLED module", "display", "modules", 7600),
    ("PNL-27", "27-inch monitor panel", "display", "panels", 8800),
    ("K9", "K9 SoC (Pro)", "soc", "pcs", 12500),
    ("A6", "A6 phone SoC", "soc", "pcs", 5400),
    ("BAT-2S", "2S tablet battery", "battery", "packs", 2100),
    ("BAT-1S", "1S phone/wearable battery", "battery", "packs", 900),
    ("BAT-E", "Earbud battery", "battery", "packs", 150),
    ("ENC-14", "14-inch aluminium enclosure", "enclosure", "pcs", 2400),
    ("ENC-16", "16-inch aluminium enclosure", "enclosure", "pcs", 3100),
    ("SEN-W", "Wearable sensor module", "module", "pcs", 1300),
    ("BT-E", "Bluetooth audio module", "module", "pcs", 600),
    ("PCB-H", "Smart-hub main board", "pcb", "pcs", 1500),
    ("PSU-H", "Power supply unit", "pcb", "pcs", 900),
    # Filler sub-parts (tier 2) and raw inputs (tier 3)
    ("GLS-CVR", "Cover glass", "glass", "pcs", 400),
    ("CELL-POUCH", "Pouch cell", "cell", "cells", 300),
    ("WFR-N7", "N7 die", "wafer", "dies", 2600),
    ("DIE-K7", "K7 die (N5 wafer)", "wafer", "dies", 4100),
    ("AL-SHEET", "Aluminium sheet blank", "metal", "pcs", 700),
    ("PCB-LAM", "PCB laminate panel", "laminate", "pcs", 250),
    ("CATH-NMC", "NMC cathode lot", "chemical", "lots", 120),
    ("CU-FOIL", "Copper foil sheet", "metal", "pcs", 60),
]

# (id, name, unit_price_cents, build_days, {component: qty})
PRODUCTS = [
    ("KB14", "Kestrel Book 14", 89_900, 2, {"BAT-4S": 1, "DSP-14": 1, "K7": 1, "ENC-14": 1}),
    ("KBP16", "Kestrel Book Pro 16", 199_900, 3, {"BAT-6S": 1, "DSP-16": 1, "K9": 1, "ENC-16": 1}),
    ("KT11", "Kestrel Tab 11", 49_900, 2, {"BAT-2S": 1, "DSP-11": 1, "K7": 1}),
    ("KP6", "Kestrel Phone 6", 69_900, 2, {"BAT-1S": 1, "DSP-6": 1, "A6": 1}),
    ("KW2", "Kestrel Watch 2", 24_900, 1, {"BAT-1S": 1, "SEN-W": 1}),
    ("KE3", "Kestrel Earbuds 3", 12_900, 1, {"BAT-E": 2, "BT-E": 2}),
    ("KH1", "Kestrel Hub 1", 9_900, 1, {"PCB-H": 1, "PSU-H": 1}),
    ("KD27", "Kestrel Display 27", 34_900, 2, {"PNL-27": 1, "PSU-H": 1}),
]

# Filler demand: (plant, product, low, high) units/week, drawn from the seed.
# Hero demand (KB14, KBP16) is fixed in motifs.py.
FILLER_DEMAND = [
    ("PL-BAC", "KT11", 200, 300),
    ("PL-PEN", "KT11", 150, 250),
    ("PL-BAC", "KP6", 500, 900),
    ("PL-BAC", "KE3", 600, 1200),
    ("PL-PEN", "KW2", 250, 500),
    ("PL-GDL", "KH1", 200, 450),
    ("PL-GDL", "KD27", 120, 260),
]

# Filler part -> (sub-part made by tier 2, qty per unit). Sub-part -> (raw input from tier 3, qty).
FILL_SUBPART = {
    "DSP-16": ("GLS-CVR", 1), "DSP-11": ("GLS-CVR", 1), "DSP-6": ("GLS-CVR", 1), "PNL-27": ("GLS-CVR", 1),
    "K9": ("WFR-N7", 1), "A6": ("WFR-N7", 1), "K7": ("DIE-K7", 1),
    "BAT-2S": ("CELL-POUCH", 2), "BAT-1S": ("CELL-POUCH", 1), "BAT-E": ("CELL-POUCH", 1),
    "ENC-14": ("AL-SHEET", 1), "ENC-16": ("AL-SHEET", 1),
    "SEN-W": ("PCB-LAM", 1), "BT-E": ("PCB-LAM", 1), "PCB-H": ("PCB-LAM", 1), "PSU-H": ("PCB-LAM", 1),
}
FILL_RAW = {"CELL-POUCH": ("CATH-NMC", 1), "PCB-LAM": ("CU-FOIL", 1)}

# Where each kind of filler site may be placed. The Chao Phraya Basin regions are never used,
# so VoltCell is the only site in the Monsoon flood zone (tier-1 view = 0 is a real result).
FILL_REGIONS = {
    "display": ["R-SUZ", "R-WUH", "R-GUM", "R-TXG", "R-TNN", "R-DGN"],
    "soc": ["R-HSC", "R-TNN", "R-KHH", "R-SWN"],
    "battery": ["R-DGN", "R-SZX", "R-CJU", "R-HPG", "R-JHB"],
    "enclosure": ["R-DGN", "R-SUZ", "R-HPG", "R-MTY"],
    "module": ["R-SZX", "R-TYN", "R-PEN", "R-CHB", "R-BRN"],
    "pcb": ["R-SZX", "R-TYN", "R-MTY", "R-CHB", "R-BRN"],
    "glass": ["R-WUH", "R-GUM", "R-TXG", "R-FUK"],
    "wafer": ["R-HSC", "R-TNN", "R-CJU"],
    "cell": ["R-CJU", "R-DGN", "R-SHA"],
    "metal": ["R-SHA", "R-MTY", "R-HOU", "R-BRN"],
    "laminate": ["R-TYN", "R-SZX", "R-SUZ"],
    "chemical": ["R-SHA", "R-PUS", "R-HOU"],
}
FILL_SITE_KIND = {
    "display": "module_line", "soc": "osat", "battery": "pack_line", "enclosure": "machining",
    "module": "smt_line", "pcb": "smt_line", "glass": "glass_fab", "wafer": "wafer_fab",
    "cell": "cell_fab", "metal": "mill", "laminate": "laminate", "chemical": "chemical_plant",
}

# Fictional filler companies: (code, name, hq_country)
FILL_SUPPLIERS = [
    ("ORIN", "Orinda Components", "TW"), ("TALS", "Talsen Industrial", "CN"), ("MIRO", "Mirovia Tech", "KR"),
    ("QUIL", "Quillon Materials", "JP"), ("SEVR", "Severn Microsystems", "TW"), ("HALC", "Halcyon Glassworks", "KR"),
    ("BRIX", "Brixford Metals", "MX"), ("CORA", "Coralis Electronics", "MY"), ("VANT", "Vantor Power", "CN"),
    ("ELMS", "Elmstead Circuits", "CZ"), ("PIKE", "Pikeway Assembly", "VN"), ("ZEPH", "Zephyr Optics", "CN"),
    ("NOMA", "Nomad Cell Co", "KR"), ("ARDN", "Arden Laminates", "TW"), ("KILN", "Kilnworth Chemicals", "US"),
    ("SOLA", "Solara Devices", "TH"), ("RIVA", "Rivale Precision", "MX"), ("TERN", "Ternstone Silicon", "TW"),
    ("OKAP", "Okapi Modules", "CN"), ("LUXA", "Luxa Display Tech", "KR"),
]

# Customers: (id, name, country, tier, penalty_per_day_cents). Meridian is the Monsoon strategic customer.
CUSTOMERS = [
    ("CU-MER", "Meridian Schools Consortium", "US", "strategic", 2_500_000),
    ("CU-HLX", "Helix Health Systems", "US", "strategic", 800_000),
    ("CU-ATL", "Atlas Telecom", "MX", "strategic", 600_000),
    ("CU-SKY", "Skyline Retail Group", "US", "strategic", 500_000),
    ("CU-BRP", "Bright Path Education", "IN", "standard", 0),
    ("CU-ORB", "Orbit Electronics Retail", "DE", "standard", 0),
    ("CU-NWV", "Northwave Mobile", "GB", "standard", 0),
    ("CU-PCF", "Pacific Office Supply", "AU", "standard", 0),
    ("CU-LMN", "Lumina Hospitality", "SG", "standard", 0),
    ("CU-GRD", "Gridline Logistics", "US", "standard", 0),
    ("CU-VRT", "Vertex Field Services", "CA", "standard", 0),
    ("CU-SOL", "Solstice Media", "ES", "standard", 0),
    ("CU-HRB", "Harbor Credit Union", "US", "standard", 0),
    ("CU-TKO", "Tokai Retail", "JP", "standard", 0),
    ("CU-AND", "Andes Telecom", "CL", "standard", 0),
    ("CU-KVN", "Kavana Schools", "IN", "standard", 0),
]
# Standard customers draw their daily penalty from this range (cents).
STANDARD_PENALTY_RANGE = (20_000, 100_000)
