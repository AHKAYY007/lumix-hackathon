"""
Carbon credit calculation constants per Lumix requirements.
"""

# Emission factor: 1.2 kg CO2 per 1 kWh (Nigeria baseline: petrol/diesel generators)
EMISSION_FACTOR_KG_PER_KWH = 1.2

# Conversion: 1 Carbon Credit = 1 metric tonne CO2
TONNES_PER_CREDIT = 1.0

# Verification thresholds
MIN_CORRELATION_THRESHOLD = 0.90  # 90% correlation required for verification
FRAUD_FLAG_THRESHOLD = 1.0  # If inverter output > theoretical output, flag

# NASA POWER API parameter
NASA_PARAMETER = "ALLSKY_SFC_SW_DWN"  # All-sky surface shortwave downward irradiance

