"""Operational attribution only. Inputs must share a period and documented boundary."""
import math


def nonnegative(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return value


def operational_footprint(it_energy_kwh, pue, *, direct_consumption_l_per_it_kwh=None,
                          grid_water_l_per_facility_kwh=None,
                          grid_carbon_kg_per_facility_kwh=None):
    """Unknown factors remain None; water factors mean consumption, not withdrawal.

    Electricity factors must already be on a delivered-facility-kWh basis.
    eGRID generation-output factors need a separately documented loss treatment.
    This does not attribute a causal marginal impact or an AI-only footprint.
    """
    nonnegative('it_energy_kwh', it_energy_kwh)
    nonnegative('pue', pue)
    if pue < 1:
        raise ValueError('PUE cannot be below one for this accounting boundary')
    energy = it_energy_kwh * pue
    nonnegative('facility_energy_kwh', energy)
    def impact(name, factor, basis):
        if factor is None:
            return None
        value = nonnegative(name, factor) * basis
        return nonnegative(name + '_result', value)
    direct = impact('direct_consumption_intensity', direct_consumption_l_per_it_kwh, it_energy_kwh)
    indirect = impact('grid_water', grid_water_l_per_facility_kwh, energy)
    total = None if direct is None or indirect is None else direct + indirect
    if total is not None:
        nonnegative('total_water', total)
    return dict(facility_energy_kwh=energy, overhead_energy_kwh=energy - it_energy_kwh,
                direct_consumption_l=direct, indirect_consumption_l=indirect,
                total_consumption_l=total,
                electricity_carbon_kg=impact('grid_carbon', grid_carbon_kg_per_facility_kwh, energy))
