# Behind-the-Meter Battery as a Capacity Service for PJM Data Centers

A feasibility study and 15-year project-finance model for a 50 MW / 500 MWh battery that would supply the new capacity a 50 MW data center in Loudoun County, Virginia, must bring under a proposed PJM rule.

*Work in progress. Started as the course project for 18-861 Energy Project Development and Finance at Carnegie Mellon University (Aug.–Oct. 2026) and continuing as an independent study. Advisor: Prof. Nathan Williams.*

## Status: redesign after the FERC order

The report and model in this repository assume PJM's proposed Interim Resource Adequacy Service (IRAS), under which a new large load that does not bring its own new capacity (BYONC) is curtailed first in a capacity shortage. On October 9, 2026, the day the report was submitted, FERC accepted PJM's definition of Large Load and the Large Load Registry but rejected IRAS and the BYONC rules (197 FERC ¶ 61,019, Docket No. ER26-3515-000). The service studied here therefore has no market under the current rules.

The study is now being redesigned around the data center operator's least-cost on-site backup among diesel, gas, battery and hybrid options under three regulatory scenarios. A second strand forecasts load peaks: `pipeline/` builds the hourly dataset for comparing GAM, tree-based and Transformer models on extrapolating to record peaks. Only the data-preparation stage is complete so far.

## Phase 1 results (report dated October 9, 2026)

- **Design.** A 50 MW / 500 MWh lithium iron phosphate battery behind the customer's meter, registered as the load's demand response. At PJM's 90% demand-resource rating it accredits 45.0 MW, 97.5% of the load's 46.16 MW obligation, and its 10 hours cover 15 of the 16 recorded Dominion-zone dispatch days.
- **Price.** The minimum availability fee that gives equity a 12% return is **$27.65/kW-month** over a 15-year contract.
- **Financing.** CAPEX of $135.1M is funded by $55.7M of debt and $79.4M of equity; selling the 30% investment tax credit returns $36.5M in the first year. Project IRR is 8.68% and the minimum debt service coverage ratio is 1.42x.
- **Sensitivity.** Installed cost moves the fee most, from $20.22 to $35.62/kW-month across NREL's 2028 low and high cost projections.
- **Recommendation.** Study further on a limited budget up to a go/no-go gate on March 31, 2027, conditional on FERC accepting IRAS. That condition failed (see above).

## Repository contents

| Path | Contents |
|---|---|
| `report/BTM_Battery_Capacity_Service_Report.pdf` | Feasibility report: market, technical, financial, sensitivity, environmental and social, regulatory, risk and development plan |
| `model/BTM_Battery_Capacity_Service_Model.xlsx` | Excel model: Inputs, Events, Technical, Costs, CashFlow, Results, Sensitivity and Customer sheets. Orange cells are inputs; the ReadMe sheet explains the layout and the Goal Seek step that solves the fee |
| `pipeline/` | Python pipeline that cleans ten years of hourly load, price and weather data for the Dominion zone and builds the modelling panel |

## Data pipeline

`pipeline/run_all.py` cleans each raw source to its own CSV and joins load, day-ahead prices and weather into an hourly panel keyed on UTC, hour-beginning:

| Source | Content | Redistribution |
|---|---|---|
| PJM Data Miner 2 | Metered load (Dominion zone and PJM total), day-ahead zonal LMPs, ancillary reserve prices, regulation prices, network service peak loads, historical load forecasts | Not allowed; download your own copy |
| EIA-930 Hourly Electric Grid Monitor | Load for PJM's 20 subregions, used as a public substitute for PJM load | Public domain |
| NOAA NCEI Global Hourly (ISD) | Temperature, dew point and pressure at Washington Dulles (station 72403093738) | Public domain |
| Iowa Environmental Mesonet ASOS archive | The same Dulles observations, used for recent hours that ISD has not yet published | Not included; cite the Iowa Environmental Mesonet |

No data files are included. With PJM files, the main panel runs from August 2016. `python pipeline/run_all.py --public` builds a second panel of load and weather only, from EIA-930 (2019 onward), NOAA ISD and the Iowa Environmental Mesonet, so it can be reproduced and shared without any PJM file. Each step's row counts and the reasons for dropped or missing values are written to `pipeline/data_quality_report.md`.

To run it, put the raw downloads under `original_data/` at the repository root:

```
original_data/
  Hourly_Load_Metered/*.csv                      PJM hrl_load_metered
  Day_Ahead_Hourly_LMPs/*.csv                    PJM da_hrl_lmps, zonal nodes
  Day_Ahead_Ancillary_Service_LMPs/*.csv         PJM da_ancillary_services
  Annual_Zonal_Network_Service_Peak_Loads/*.csv  PJM annual_zonal_nspl
  load_frcstd_hist.csv                           PJM historical load forecasts
  reg_prices.csv                                 PJM reg_market_results
  pjm/EIA930_SUBREGION_*.csv.gz                  EIA-930 six-month subregion files
  weather/iad_<year>.csv                         NOAA ISD, one file per year
  weather/iem_iad_*.csv                          Iowa Environmental Mesonet ASOS, station IAD
```

Missing sources are skipped. Then run:

```bash
pip install -r pipeline/requirements.txt
python pipeline/run_all.py --public
```

The cleaned CSVs are written to `pipeline/`.
