# References

Working list for the method, the tests and the paper. Add new entries in the matching section with one line on why
the source matters to us. **Bold** = closest to our problem (aggregate smart-meter data only, flexibility estimate).
Status: *read* = full text read; *abstract* = only abstract/summary seen; *to read* = found, not yet read.

## 1. Flexibility from smart-meter data (closest work)

- **[10] Ponoćko J., Milanović J.V., "Forecasting demand flexibility of aggregated residential load using smart meter data", IEEE Trans. Power Systems 33(5), 5446–5455, 2018.** Main comparison: needs >=5% sub-metering; AWFE metric; Pecan Street validation. *read*
- **[11] Wang J., Ding F., Zhu X., Xuan K., Yao Y., "Estimating flexibility envelopes for residential customers from utility smart meter data", IEEE PES T&D, 2026 (NREL preprint).** Flexibility envelopes from utility smart-meter data. *abstract*
- **[6] Albert A., Rajagopal R., "Thermal profiling of residential energy use", IEEE Trans. Power Systems 30(2), 2015.** Thermal response from smart-meter + weather; segmentation, no flexibility quantity. *abstract*
- **[7] Dyson M.E.H., Borgeson S.D., Tabone M.D., Callaway D.S., "Using smart meter data to estimate demand response potential, with application to solar energy integration", Energy Policy 73, 607–619, 2014.** AC DR potential from smart-meter data (30,000 CA homes). *abstract*
- [12] Bañales S., Dormido R., Duro N., "Explainable AI for predicting household demand flexibility: insights from smart meter data and price-based programs", Energy and AI 24, 2026. *abstract*
- [13] Zhou D., Balandat M., Tomlin C., "A Bayesian perspective on residential demand response using smart meter data", arXiv:1608.03862. *abstract*
- [17] Nespoli L., Medici V., "Quantification of residential flexibility potential using global forecasting models", arXiv:2306.02802, 2023. *abstract*
- [8] Najafi B., Di Narzo L., Rinaldi F., Arghandeh R., "Machine learning based disaggregation of air-conditioning loads using smart meter data", IET GTD, 2020. *abstract*
- [9] Kara E.C., Tabone M.D., MacDonald J.S., Callaway D.S., Kiliccote S., "Quantifying flexibility of residential thermostatically controlled loads for demand response: a data-driven approach", LBNL, 2014. *abstract*
- [20] Parti M., Parti C., "The total and appliance-specific conditional demand for electricity in the household", Bell J. Economics, 1980; also OSTI 103278 "Conditional demand analysis". Origin of end-use estimation from aggregate data. *abstract*

## 2. Flexibility concepts and aggregation

- [14] Junker R.G. et al., "Characterizing the energy flexibility of buildings and districts", Applied Energy 225, 175–182, 2018.
- [15] Hao H., Sanandaji B.M., Poolla K., Vincent T.L., "Aggregate flexibility of thermostatically controlled loads", IEEE Trans. Power Systems 30(1), 2015.
- [16] Müller F.L., Szabó J., Sundström O., Lygeros J., "Aggregation and disaggregation of energetic flexibility from distributed energy resources", arXiv:1705.02815, 2017.
- [18] Li R. et al., "Ten questions concerning energy flexibility in buildings", Building and Environment 223, 2022.
- [19] Lankeshwara G. et al., "A review on network-aware control of DER under the dynamic operating envelopes framework", RSER 217, 2025.
- [21] Wang Y., Chen Q., Hong T., Kang C., "Review of smart meter data analytics", IEEE Trans. Smart Grid, 2019 (arXiv:1802.04117).

## 3. Baselines, forecasting and evaluation

- [1] Coughlin K., Piette M.A., Goldman C., Kiliccote S., "Statistical analysis of baseline load models for non-residential buildings", Energy and Buildings, 2009.
- [2] Todd-Blick A. et al., "Spillover as a cause of bias in baseline evaluation methods for demand response programs", Applied Energy 250, 2019.
- **[3] Haben S. et al., "Review of low voltage load forecasting: methods, applications, and recommendations", Applied Energy 304, 2021 (arXiv:2106.00006).** Most papers use observed instead of forecast weather -> over-optimistic accuracy; point errors (RMSE/MAPE) misleading for single homes. Basis for T1 with forecast weather. *partly read*
- [4] Kath C., Ziel F., "Conformal prediction interval estimations with an application to day-ahead and intraday power markets", arXiv:1905.07886. Conformal calibration (M1).
- [5] Jensen V., Bianchi F.M., Anfinsen S.N., "Ensemble conformalized quantile regression for probabilistic time series forecasting", arXiv:2202.08756, 2022. Conformalized quantile regression (M1).
- [31] (authors to check), "Towards trustworthy energy disaggregation: a review of challenges, methods and perspectives for NILM", arXiv:2207.02009, 2022. Recommends per-home evaluation and testing on unseen homes; basis for the held-out homes in our split. *partly read*

## 4. Datasets

- [30] Pullinger M. et al., "The IDEAL household energy dataset ... for 255 UK homes", Scientific Data, 2021. Only 39 homes with appliance-level data. Not used for now.
- [32] Athanasoulias S. et al., "The Plegma dataset: domestic appliance-level and aggregate electricity demand with metadata from Greece", Scientific Data, 2024. DOI 10.15129/3b01a6c6-2efd-424a-b8b8-5fe7fa445ded (CC BY 4.0). **Used** (AC ground truth).
- [33] Murray D., Stankovic L., Stankovic V., "An electrical load measurements dataset of United Kingdom households from a two-year longitudinal study", Scientific Data 4, 2017 (REFIT; CC BY 4.0). **Used**.
- [34] Kelly J., Knottenbelt W., "The UK-DALE dataset, domestic appliance-level electricity demand and whole-house demand from five UK homes", Scientific Data 2, 2015 (CC BY 4.0). **Used**.
- [35] Pecan Street Dataport (access requested; metadata: ~850 homes with AC circuit, ~150 with EV; CCET pricing trial with DR signals).
- [36] CU-BEMS, Chulalongkorn University building energy dataset (commercial; to check).
- [37] Brudermueller T. et al., "HEAPO – an open dataset for heat pump optimization with smart electricity meter data and on-site inspection protocols", arXiv:2503.16993, 2025. 1,408 Swiss homes with heat pumps; licence to check. Not used for now.

## 5. Behaviour and time use (when people cook, wash, charge; who responds)

- [38] Harmonised European Time Use Survey (HETUS), Eurostat. Activity timing by country; source for meal and appliance-use hours (M3/M4). Greek coverage and microdata access to check. *to read*
- **[39] El Makroum R., Zwickl-Bernhard S., Kranzl L., Auer H., "Load scheduling optimization for user-centric residential demand response leveraging time use surveys", Applied Energy 403, 2026.** Uses HETUS to model when laundry, dishwashing, cooking happen; trade-off cost vs disruption. *abstract*
- [40] Satre-Meloy A., Diakonova M., Grünewald P., "Daily life and demand: an analysis of intra-day variations in residential electricity consumption with time-use data", Energy Efficiency 13, 2020. 173 UK homes; food, chores and recreation most linked to demand. *summary*
- [41] Torriti J., "Peak demand, price elasticity and intrinsic flexibility from time use activities" (University of Reading). *to read*
- [42] Lőrincz M.J., Torriti J., "Working more, consuming electricity differently? Activity network analysis of the 2014–2015 UK Time Use Survey" (CREDS). *to read*
- **[43] Klaassen E.A.M., Kobus C.B.A., Frunt J., Slootweg J.G., "Responsiveness of residential electricity demand to dynamic tariffs: experiences from a large field test in the Netherlands", Applied Energy 183, 1065–1074, 2016.** Most flexible demand came from washing machine, dryer, dishwasher; shift evening->midday stable >1 year. Numbers in full text. *abstract*
- [44] "Load profiles and flexibility in operation of washing machines and dishwashers in Europe", International Journal of Consumer Studies (12-country survey). Usage timing by country. *abstract*
- [45] Dupont B. et al., "LINEAR breakthrough project: large-scale implementation of smart grid technologies in distribution grids" (Belgium; smart wet appliances, ~2012–2013). Setup only; results in follow-up papers. *read (setup)*
- [46] Electric Nation (UK smart EV charging trial, Western Power Distribution / National Grid). Plug-in times and smart-charging response. *to read*
- [24] ESRI study on household appliance use in the evening peak, Ireland, Heliyon 7, e07559, 2021.
- [25] Octopus Energy, "Saving Sessions", BIEE 2023. Participation/response in a real DR scheme (input for M5).
- [26] Carbon Brief, "Q&A: How Great Britain's demand flexibility service is cutting costs and CO2 emissions", 2023. (M5)
- [27] University of Michigan CSS, "Quantifying the impact of participant override behavior in summer demand response". (M5)
- [28] CPUC, smart thermostat demand response evaluation presentation. (M5)
- [29] Nambiar et al., "Residential demand response case studies", UC Berkeley CBE, 2024. (M5)
- [22] Odyssee-Mure, "Unit consumption of air conditioning". (M2 plausibility)
- [23] University of Otago, "Estimating the technical potential for residential demand response in New Zealand".

Open gap: no source yet with measured enrolment/response rates to set the participation share (M5, default 0.3).
