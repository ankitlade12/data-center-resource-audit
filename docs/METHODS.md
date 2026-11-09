# Methods and boundaries

## Forecasts

PUE baselines use last-quarter, prior-year mean, and same-quarter previous-year values. The geographic/climate model uses historical climate features, with forward-year and held-out-county evaluations. No realized target-year weather enters its predictors.

Annual resource methods are persistence, nonnegative two-point linear trend, and growth transferred from other states and prior years. Eligible targets have two consecutive preceding annual observations. Google consumption and Meta withdrawal are different targets and are never pooled. WAPE divides total absolute error by total observed volume; it is not the average of location percentage errors. Zero total volume makes WAPE undefined.

Paired state-cluster intervals use 2,000 draws and seed 20261010. Location/year observations are descriptive; a single observation does not support its own sampling interval. Follow-up diagnostics are exploratory and do not retune models.

## Conditional capacity

The Dalles screen compares additional average demand q with annual availability A and critical-day margin D: 365q <= A and pq <= D. The multiplier p refers to the increment on the baseline system's critical day divided by its own mean. Using its separate maximum instead assumes peak coincidence. The full requirement is baseline plus increment <= available capacity on every day. Negative baseline margins remain deficits.

Forest City's nominal treatment example uses average a, maximum m, and rating c. Average margin is c-a; under p=m/a, the peak-constrained added-average ceiling is (c-m)/p. These gross-load proxy calculations do not identify finished-water allocation, outage-adjusted supply, firm raw-water availability, or data-center-specific peaks.

## Cross-source water comparison

City and operator labels both indicate calendar 2024. Google lists 461.1 MG withdrawal, 99.7 MG discharge, and 361.4 MG net consumption; the city reports 434.42854 MG Google use. Rounding at 0.1 MG cannot explain the 26.67146 MG difference. Neither subtracting discharge nor substituting consumption reconciles it. Meter accounts, service/billing periods, adjustments, and source boundaries require further records.
