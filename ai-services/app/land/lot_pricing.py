"""Traceable prices: exact listing, confirmed road, then project reference."""
from decimal import Decimal, ROUND_HALF_UP

def resolve_price(lot, road_reference=None, project_reference=None):
    area = lot.get('areaSqm', lot.get('combinedAreaSqm'))
    if lot.get('askingPriceVnd'):
        return dict(method='EXACT_LOT_HISTORICAL_ASKING', valueVnd=lot['askingPriceVnd'],
                    sourceUrl=lot['sourceUrl'], date=lot['sourceDate'], currentSaleConfirmed=False)
    if not area or area <= 0:
        return None
    reference = road_reference if lot.get('roadConfirmed') and road_reference else project_reference
    if not reference or not reference.get('unitMillionPerSqm') or not reference.get('sourceUrl'):
        return None
    value = int((Decimal(str(area))*Decimal(str(reference['unitMillionPerSqm']))*1000000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return dict(method='ROAD_UNIT_ESTIMATE' if reference is road_reference else 'PROJECT_UNIT_ESTIMATE',
                valueVnd=value, unitMillionPerSqm=reference['unitMillionPerSqm'], areaSqm=area,
                sourceUrl=reference['sourceUrl'], date=reference.get('date'),
                valueMeaning=reference.get('valueMeaning','INDICATIVE_ESTIMATE'), currentSaleConfirmed=False)
