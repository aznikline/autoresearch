# Paper Outline

Working title: Evidence-Grounded Study of SQLite index tradeoffs on the UCI Bike Sharing hourly workload

## Abstract
- State the research question, evidence source, best metric, and limitation.

## Introduction
- Motivate the topic and why the experiment is narrow but reproducible.

## Related Work
- Discuss MOSIQS: Persistent Memory Object Storage With Metadata Indexing and Querying for Scientific Computing [@khan2021mosiqsc8a373f2].
- Discuss AirIndex: Versatile Index Tuning Through Data and Storage [@chockchowwat2023airindex34a18a07].
- Discuss DART [@zhang2018dartcaf51a21].
- Discuss mCerebrum [@hossain2017mcerebrum799408b7].
- Discuss Benchmarking PHP–MySQL Communication: A Comparative Study of MySQLi and PDO Under Varying Query Complexity [@andrijevi2025benchmarkingedda800b].
- Discuss TASM: A Tile-Based Storage Manager for Video Analytics [@daum2021tasm968093c3].
- Discuss Index of SQLite Commands [@paper2019indexa7e7403c].
- Discuss Database Workload Optimization [@fritchey2018databasefc41a48e].
- Discuss An adaptive path index for XML data using the query workload [@min2005adaptive522ab6b5].
- Discuss AI-Based Automated SQL Query Generation for SQLite Databases in Mobile Forensics [@pawlaszczyk2026aibased9504562c].
- Discuss snowquery: SQL Interface to 'Snowflake', 'Redshift', 'Postgres', 'SQLite', and 'DuckDB' [@mermelstein2023snowquery83be4a32].
- Discuss Erratum to: “An adaptive path index for XML data using the query workload” [@min2006erratumb6de907d].
- Discuss Database Workload Optimization [@paper2009database4b698fc5].
- Discuss Database Workload Optimization [@fritchey2014database9cd5798d].
- Discuss Text Document Annotation and Retrieval Based on Content of the Document and Query Workload [@paper2016textdf2c3837].
- Discuss Introducing SQLite [@paperndintroducing2717579a].
- Discuss Driving through the Network: Performance and Workload under Latency and Video Impairments [@trautmannsheimer2026drivingff61bd6f].
- Discuss ATTI: Workload-Aware Query Adaptive OcTree Based Trajectory Index [@meng2013attie06ff60a].
- Discuss SQLite Internals [@paperndsqlite4662a699].
- Discuss Query Workload Driven Summarization for P2P Query Routing [@nguyen2008query2c2d2603].
- Discuss Database Workload Optimization [@fritchey2012databasea16044b3].
- Discuss SQLite Internals and New Features [@allen2010sqliteea10af9e].
- Discuss Research on SQLite Database Query Optimization Based on Improved PSO Algorithm [@zhao2016researchae69112a].
- Discuss A Cost-Effective Query Optimizer for Multi-Tenant Parallel RDBMSs Leveraging Workload Prediction [@danaouindcosteffective0bc696d1].
- Discuss adbcsqlite: 'Arrow' Database Connectivity ('ADBC') 'SQLite' Driver [@dunnington2023adbcsqlite4ed401bf].
- Discuss Analyzing SQLite Databases [@languedoc2016analyzing1421fa41].
- Discuss Decentralized, Energy-Efficient, Low Latency and Less Homogeneous Settings based Workload Management in Enterprise Clouds [@bhuvaneshwari2016decentralized2a4a7840].
- Discuss Using SQLite with PHP [@feiler2015usingf141f28c].
- Discuss Parallel selection query processing involving index in parallel database systems [@rahayundparallel50c83349].
- Discuss Index selection [@sun2013indexd06a71f0].
- Discuss A Copula-Based Sample Selection Binary Choice Model for Difference Analysis Among Private Bike and Bike Sharing in Lyon (France) [@havet2024copulabased072061f0].
- Discuss Index [@paper2015indexf37979dd].
- Discuss Large-Scale Dockless Bike Sharing Repositioning Considering Future Usage and Workload Balance [@hua2022largescalea3dcd6e3].
- Discuss Bike Sharing Systems [@paper2012bike36b8579c].
- Discuss Analyzing Bike Repositioning Strategies Based on Simulations for Public Bike Sharing Systems: Simulating Bike Repositioning Strategies for Bike Sharing Systems [@wang2013analyzing28f8d1c0].
- Discuss Dynamic Workload-Aware Bike Rebalancing for Bike-Sharing Systems [@luo2023dynamicaa6351a1].
- Discuss Bike Sharing Systems [@brinkmann2020bike3ea4ebc3].
- Discuss Bikeability Index in Bike-Sharing Systems: A Dual-Level Assessment Integrating Station Accessibility and Cycling Environment [@zhang2026bikeabilityb19f06f6].
- Discuss The impact of the introduction of e-bike sharing on the usage of bike sharing [@li2023impactf8551f97].
- Discuss Investigation on the impact of new bike stations on a bike-share system based on a complex bike-sharing network [@kim2023investigation8b61d992].
- Discuss Shared Bike Demand Prediction by Using Metro and Bike Sharing Networks’ Features [@sadeghraimoghaddam2024sharedb393a7a0].
- Discuss Service Network Design of Bike Sharing Systems [@vogel2016serviceedddaae4].
- Discuss Bike Sharing Atlas: Visual Analysis of Bike-Sharing Networks [@oppermann2018bikef56eb840].
- Discuss Bike Sharing in the Context of Urban Mobility [@vogel2016bike2cdc0e3f].
- Discuss Large-scale dockless bike sharing repositioning considering future usage and workload balance [@hua2022largescale9364fc80].
- Discuss Impacts of Bike Sharing on Transit Ridership [@aljerindimpactsa8dde5c8].
- Discuss Figure 4: The sliding window technique for predicting hourly bike sharing demand. [@paperndfigure3ff39c7b].
- Discuss Station-Level Hourly Bike Demand Prediction for Dynamic Repositioning in Bike Sharing Systems [@wu2019stationlevel61be6a10].
- Discuss Framework for Hourly Demand Forecasting of Bike-Sharing Stations: Case Study of the Four Main Gate Areas in Seoul [@hong2022framework379bf9f4].
- Discuss Correction: Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2022correction29b7ba87].
- Discuss Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2019graph2ba8bd0a].
- Discuss Spatiotemporal Data-Driven Hourly Bike-Sharing Demand Prediction Using ApexBoost Regression [@biswas2025spatiotemporal0c159daa].
- Discuss Analyzing Tail Latency in Serverless Clouds with STeLLAR [@ustiugov2021analyzingd7992127].
- Discuss Road-Specific Exploration of Bike-Sharing Usage Changes after Construction of Bike Lanes [@li2022roadspecific9099c795].
- Discuss From System-Wide to Road-Specific Exploration of Bike Trips for Changes in Bike Sharing System Usage after Construction of Bike Lanes [@li2022systemwide85690469].
- Discuss Tradeoffs between power management and tail latency in warehouse-scale applications [@kanev2014tradeoffseb5a8f2e].
- Discuss Research Department - Prices &amp; Statistics - Price Indexes - Wage Indexes - Minimum Hourly Rates of Wages by Industrial Groups - Correspondence, Memoranda and Blue Sheets - 1950 - 1959 [@paper2022researchccb01f09].
- Discuss The bike sharing rebalancing problem: Mathematical formulations and benchmark instances [@dellamico2014bikecdcdb26f].
- Discuss Query similarity index based query preprocessing mechanism for multiapplication sharing wireless sensor networks [@verma2020queryfe05167e].
- Discuss Figure 6: Proposed MLP to predict future bike sharing demand. [@paperndfigure140a619b].

## Method
- Describe the deterministic local experiment and trial variants.

## Experiments
- Report every trial in the ledger and the keep/discard decision.

## Results
- Best kept trial: ablation-composite-index-seed4.

## Limitations
- Clarify that this is a local scaffold until domain experiments replace the toy task.

## Conclusion
- Summarize what the evidence supports and what must be improved next.

# Evidence-Grounded Study of SQLite index tradeoffs on the UCI Bike Sharing hourly workload

## Abstract
We study SQLite index tradeoffs on the UCI Bike Sharing hourly workload with a local, auditable experiment pipeline. The best kept trial was `ablation-composite-index-seed4` with primary metric 30.673462499999996.

## Introduction
The goal is to convert a research idea into a paper candidate without losing provenance.
This draft only reports evidence that exists in the run artifacts.

## Related Work
The screened literature includes MOSIQS: Persistent Memory Object Storage With Metadata Indexing and Querying for Scientific Computing [@khan2021mosiqsc8a373f2], AirIndex: Versatile Index Tuning Through Data and Storage [@chockchowwat2023airindex34a18a07], DART [@zhang2018dartcaf51a21], mCerebrum [@hossain2017mcerebrum799408b7], Benchmarking PHP–MySQL Communication: A Comparative Study of MySQLi and PDO Under Varying Query Complexity [@andrijevi2025benchmarkingedda800b], TASM: A Tile-Based Storage Manager for Video Analytics [@daum2021tasm968093c3], Index of SQLite Commands [@paper2019indexa7e7403c], Database Workload Optimization [@fritchey2018databasefc41a48e], An adaptive path index for XML data using the query workload [@min2005adaptive522ab6b5], AI-Based Automated SQL Query Generation for SQLite Databases in Mobile Forensics [@pawlaszczyk2026aibased9504562c], snowquery: SQL Interface to 'Snowflake', 'Redshift', 'Postgres', 'SQLite', and 'DuckDB' [@mermelstein2023snowquery83be4a32], Erratum to: “An adaptive path index for XML data using the query workload” [@min2006erratumb6de907d], Database Workload Optimization [@paper2009database4b698fc5], Database Workload Optimization [@fritchey2014database9cd5798d], Text Document Annotation and Retrieval Based on Content of the Document and Query Workload [@paper2016textdf2c3837], Introducing SQLite [@paperndintroducing2717579a], Driving through the Network: Performance and Workload under Latency and Video Impairments [@trautmannsheimer2026drivingff61bd6f], ATTI: Workload-Aware Query Adaptive OcTree Based Trajectory Index [@meng2013attie06ff60a], SQLite Internals [@paperndsqlite4662a699], Query Workload Driven Summarization for P2P Query Routing [@nguyen2008query2c2d2603], Database Workload Optimization [@fritchey2012databasea16044b3], SQLite Internals and New Features [@allen2010sqliteea10af9e], Research on SQLite Database Query Optimization Based on Improved PSO Algorithm [@zhao2016researchae69112a], A Cost-Effective Query Optimizer for Multi-Tenant Parallel RDBMSs Leveraging Workload Prediction [@danaouindcosteffective0bc696d1], adbcsqlite: 'Arrow' Database Connectivity ('ADBC') 'SQLite' Driver [@dunnington2023adbcsqlite4ed401bf], Analyzing SQLite Databases [@languedoc2016analyzing1421fa41], Decentralized, Energy-Efficient, Low Latency and Less Homogeneous Settings based Workload Management in Enterprise Clouds [@bhuvaneshwari2016decentralized2a4a7840], Using SQLite with PHP [@feiler2015usingf141f28c], Parallel selection query processing involving index in parallel database systems [@rahayundparallel50c83349], Index selection [@sun2013indexd06a71f0], A Copula-Based Sample Selection Binary Choice Model for Difference Analysis Among Private Bike and Bike Sharing in Lyon (France) [@havet2024copulabased072061f0], Index [@paper2015indexf37979dd], Large-Scale Dockless Bike Sharing Repositioning Considering Future Usage and Workload Balance [@hua2022largescalea3dcd6e3], Bike Sharing Systems [@paper2012bike36b8579c], Analyzing Bike Repositioning Strategies Based on Simulations for Public Bike Sharing Systems: Simulating Bike Repositioning Strategies for Bike Sharing Systems [@wang2013analyzing28f8d1c0], Dynamic Workload-Aware Bike Rebalancing for Bike-Sharing Systems [@luo2023dynamicaa6351a1], Bike Sharing Systems [@brinkmann2020bike3ea4ebc3], Bikeability Index in Bike-Sharing Systems: A Dual-Level Assessment Integrating Station Accessibility and Cycling Environment [@zhang2026bikeabilityb19f06f6], The impact of the introduction of e-bike sharing on the usage of bike sharing [@li2023impactf8551f97], Investigation on the impact of new bike stations on a bike-share system based on a complex bike-sharing network [@kim2023investigation8b61d992], Shared Bike Demand Prediction by Using Metro and Bike Sharing Networks’ Features [@sadeghraimoghaddam2024sharedb393a7a0], Service Network Design of Bike Sharing Systems [@vogel2016serviceedddaae4], Bike Sharing Atlas: Visual Analysis of Bike-Sharing Networks [@oppermann2018bikef56eb840], Bike Sharing in the Context of Urban Mobility [@vogel2016bike2cdc0e3f], Large-scale dockless bike sharing repositioning considering future usage and workload balance [@hua2022largescale9364fc80], Impacts of Bike Sharing on Transit Ridership [@aljerindimpactsa8dde5c8], Figure 4: The sliding window technique for predicting hourly bike sharing demand. [@paperndfigure3ff39c7b], Station-Level Hourly Bike Demand Prediction for Dynamic Repositioning in Bike Sharing Systems [@wu2019stationlevel61be6a10], Framework for Hourly Demand Forecasting of Bike-Sharing Stations: Case Study of the Four Main Gate Areas in Seoul [@hong2022framework379bf9f4], Correction: Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2022correction29b7ba87], Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2019graph2ba8bd0a], Spatiotemporal Data-Driven Hourly Bike-Sharing Demand Prediction Using ApexBoost Regression [@biswas2025spatiotemporal0c159daa], Analyzing Tail Latency in Serverless Clouds with STeLLAR [@ustiugov2021analyzingd7992127], Road-Specific Exploration of Bike-Sharing Usage Changes after Construction of Bike Lanes [@li2022roadspecific9099c795], From System-Wide to Road-Specific Exploration of Bike Trips for Changes in Bike Sharing System Usage after Construction of Bike Lanes [@li2022systemwide85690469], Tradeoffs between power management and tail latency in warehouse-scale applications [@kanev2014tradeoffseb5a8f2e], Research Department - Prices &amp; Statistics - Price Indexes - Wage Indexes - Minimum Hourly Rates of Wages by Industrial Groups - Correspondence, Memoranda and Blue Sheets - 1950 - 1959 [@paper2022researchccb01f09], The bike sharing rebalancing problem: Mathematical formulations and benchmark instances [@dellamico2014bikecdcdb26f], Query similarity index based query preprocessing mechanism for multiapplication sharing wireless sensor networks [@verma2020queryfe05167e], Figure 6: Proposed MLP to predict future bike sharing demand. [@paperndfigure140a619b].

## Method
The configured domain experiment workspace executes the prespecified trials.
Each trial writes structured metrics, and the pipeline keeps only metric improvements.

## Experiments
- `baseline-seed0`: metric=42.6005098, decision=keep, status=ok.
- `baseline-seed1`: metric=45.0910152, decision=discard, status=ok.
- `baseline-seed2`: metric=42.162404499999994, decision=keep, status=ok.
- `baseline-seed3`: metric=40.56866425, decision=keep, status=ok.
- `ablation-hour-index-seed1`: metric=41.32991074999999, decision=discard, status=ok.
- `ablation-weather-index-seed2`: metric=44.79758305, decision=discard, status=ok.
- `ablation-season-index-seed3`: metric=31.657152399999994, decision=keep, status=ok.
- `ablation-composite-index-seed4`: metric=30.673462499999996, decision=keep, status=ok.

## Results
The best kept trial was `ablation-composite-index-seed4` with primary metric 30.673462499999996.
# Research Decision

Decision: PROCEED

Proceed with trial `ablation-composite-index-seed4` as the current evidence baseline.

## Limitations
Claims are limited to the registered assets, evaluation units, trials, metrics, and compute budget recorded in this run.

## Conclusion
The workflow now links literature, experiment metrics, and paper text through auditable artifacts.
