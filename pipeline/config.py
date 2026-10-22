"""Configuration for the 18-861 data-cleaning pipeline.

Single place to change paths, scope and quality thresholds.
"""
from pathlib import Path

# This file lives in pipeline/, alongside both the code and its outputs.
HERE  = Path(__file__).resolve().parent      # pipeline/
BASE  = HERE.parent                          # repository root
RAW   = BASE / "original_data"               # untouched source downloads
CLEAN = HERE                                 # cleaned CSVs land beside the code
CLEAN.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- scope
# The project concerns one zone. DOM is the customer's zone; the PJM RTO
# total is required as well because capacity peaks (5CP) are set by SYSTEM
# load, not zonal load. Dropping RTO would make the peaks unidentifiable.
LOAD_ZONES = {"DOM", "RTO"}          # zone codes in hrl_load_metered
LMP_NODES  = {"DOM", "PJM-RTO"}      # pnode_name in da_hrl_lmps

# Which load series feeds the master panel.
#   "pjm" - PJM Data Miner metered load. Authoritative; NOT redistributable.
#   "eia" - EIA-930. Public domain; validated to within 1% of PJM.
# Set to "eia" to produce a fully publishable build.
LOAD_SOURCE = "pjm"

# PJM's 20 EIA-930 subregions. Summed to reconstruct the RTO total.
EIA_PJM_SUBREGIONS = {
    "AE","AEP","AP","ATSI","BC","CE","DAY","DEOK","DOM","DPL",
    "DUQ","EKPC","JC","ME","PE","PEP","PL","PN","PS","RECO",
}

# ---------------------------------------------------------------- weather
WEATHER_STATION = "72403093738"      # Washington Dulles (IAD), in Loudoun County
WEATHER_REPORT_TYPE = "FM-15"        # METAR - the standard hourly observation

# ---------------------------------------------------------------- quality
# Plausibility bounds. Values outside these are dropped and logged, never
# silently corrected. EIA-930 carried rows reporting ~1.5 billion MW.
BOUNDS = {
    "dom_load_mw":     (3_000, 40_000),
    "pjm_rto_load_mw": (40_000, 200_000),
    "temp_c":          (-40, 50),
    "dewpoint_c":      (-45, 35),
}

# ISD missing-value sentinels
ISD_MISSING = {"+9999", "9999", "99999", "+99999"}

# ---------------------------------------------------------------- input paths
P_LOAD      = RAW / "Hourly_Load_Metered"
P_LMP       = RAW / "Day_Ahead_Hourly_LMPs"
P_ANCILLARY = RAW / "Day_Ahead_Ancillary_Service_LMPs"
P_NSPL      = RAW / "Annual_Zonal_Network_Service_Peak_Loads"
P_EIA       = RAW / "pjm"
P_WEATHER   = RAW / "weather"
P_FORECAST  = RAW / "load_frcstd_hist.csv"
P_REG       = RAW / "reg_prices.csv"

PJM_DT_FMT = "%m/%d/%Y %I:%M:%S %p"   # e.g. 8/31/2025 4:00:00 AM
