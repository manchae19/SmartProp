# Geographic search scope data

`danang-search-scopes.geojson` contains an unchanged subset of eleven ADM2 geometries from geoBoundaries `VNM-ADM2-81297802`, commit `9469f09`, representing **2020**. Only metadata was added; coordinates were neither invented nor simplified.

- Source: OCHA ROAP, Government of Viet Nam; geoBoundaries (Runfola et al., 2020).
- License: [CC BY 3.0 IGO](https://creativecommons.org/licenses/by/3.0/igo/).
- Metadata: https://www.geoboundaries.org/api/current/gbOpen/VNM/ADM2/
- Pinned data: https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/VNM/ADM2/geoBoundaries-VNM-ADM2.geojson
- Full published source SHA-256: `17db305257c1794fb5f3f4ff3c4f747a07cc5525774b8edb395d53f65219fc33` (checked against the repository's Git LFS pointer).

The city-wide search domain is the union of the eleven historical areas already listed in SmartProp: Hải Châu, Thanh Khê, Sơn Trà, Ngũ Hành Sơn, Cẩm Lệ, Liên Chiểu, Hòa Vang, Hội An, Điện Bàn, Tam Kỳ, Núi Thành. This is a **supported historical search catalog**, not a claim to cover every current administrative unit of the expanded city. Boundaries that changed after this source version require separate verified data. No survey accuracy, property boundary or cadastral precision is claimed.

The current Ngũ Hành Sơn ward was formed from the entire former wards Mỹ An, Khuê Mỹ, Hòa Hải and Hòa Quý: [Resolution 1659/NQ-UBTVQH15, paragraph 7](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1659-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-da-nang-nam-2025-119250616202714604.htm). The verified Geoapify place ID in the catalog was returned on 30/10/2026 for `Phường Ngũ Hành Sơn`, result type `suburb`, city `Thành phố Đà Nẵng`, OpenStreetMap relation provenance. That ID is used together with country and rectangle filters; local polygon membership is still required. A provider place filter is not treated as a replacement for the historical ward polygons.

**No historical ward polygon is bundled.** geoBoundaries currently returns 404 for VNM ADM3. Current HDX COD-AB v02 only has ADM0/ADM1 dated 01/07/2025. The supplied ArcGIS ADM3 item `64bc0640738f4256896c73816c3665b5` identifies GADM v2.8 / 2015 (Hijmans, UC Berkeley); its public metadata does not grant redistribution, and [GADM licensing](https://gadm.org/license.html) requires prior permission for redistribution. No geometry from that layer has been copied. GTEL documents legacy ward polygons but requires a separate API key; none was supplied or fabricated.

Hòa Hải and all other historical wards therefore remain unavailable for automatic suggestions until a properly licensed and verified polygon is supplied. The system fails closed and leaves manual pin placement available; it never replaces Hòa Hải with the larger current Ngũ Hành Sơn ward.

GeoJSON uses WGS84 `[longitude, latitude]`. Bounding rectangles are derived from actual geometry, not representative centers. Polygon interiors (including hole exclusion) are checked by JTS; points exactly on an ambiguous boundary are conservatively excluded. This dataset is for geographic search restrictions only and is not used to draw the green illustrative circle or to update existing property coordinates.
