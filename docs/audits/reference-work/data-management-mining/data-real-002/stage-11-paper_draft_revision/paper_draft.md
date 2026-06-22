# Paper Outline

Working title: Evidence-Grounded Study of SQLite index tradeoffs on the UCI Bike Sharing hourly workload

## Abstract
- State the research question, evidence source, best metric, and limitation.

## Introduction
- Motivate the topic and why the experiment is narrow but reproducible.

## Related Work
- Discuss MOSIQS: Persistent Memory Object Storage With Metadata Indexing and Querying for Scientific Computing [@khan2021mosiqs].
- Discuss AirIndex: Versatile Index Tuning Through Data and Storage [@chockchowwat2023airindex].
- Discuss DART [@zhang2018dart].
- Discuss mCerebrum [@hossain2017mcerebrum].
- Discuss Benchmarking PHP–MySQL Communication: A Comparative Study of MySQLi and PDO Under Varying Query Complexity [@andrijevi2025benchmarking].
- Discuss TASM: A Tile-Based Storage Manager for Video Analytics [@daum2021tasm].
- Discuss Index of SQLite Commands [@paper2019index].
- Discuss Database Workload Optimization [@fritchey2018database].
- Discuss An adaptive path index for XML data using the query workload [@min2005adaptive].
- Discuss AI-Based Automated SQL Query Generation for SQLite Databases in Mobile Forensics [@pawlaszczyk2026aibased].
- Discuss snowquery: SQL Interface to 'Snowflake', 'Redshift', 'Postgres', 'SQLite', and 'DuckDB' [@mermelstein2023snowquery].
- Discuss Erratum to: “An adaptive path index for XML data using the query workload” [@min2006erratum].
- Discuss Database Workload Optimization [@paper2009database].
- Discuss Database Workload Optimization [@fritchey2014database].
- Discuss Text Document Annotation and Retrieval Based on Content of the Document and Query Workload [@paper2016text].
- Discuss Introducing SQLite [@paperndintroducing].
- Discuss Driving through the Network: Performance and Workload under Latency and Video Impairments [@trautmannsheimer2026driving].
- Discuss ATTI: Workload-Aware Query Adaptive OcTree Based Trajectory Index [@meng2013atti].
- Discuss Query Workload Driven Summarization for P2P Query Routing [@nguyen2008query].
- Discuss Database Workload Optimization [@fritchey2012database].
- Discuss SQLite Internals [@paperndsqlite].
- Discuss Research on SQLite Database Query Optimization Based on Improved PSO Algorithm [@zhao2016research].
- Discuss A Cost-Effective Query Optimizer for Multi-Tenant Parallel RDBMSs Leveraging Workload Prediction [@danaouindcosteffective].
- Discuss SQLite Internals and New Features [@allen2010sqlite].
- Discuss adbcsqlite: 'Arrow' Database Connectivity ('ADBC') 'SQLite' Driver [@dunnington2023adbcsqlite].
- Discuss Analyzing SQLite Databases [@languedoc2016analyzing].
- Discuss Decentralized, Energy-Efficient, Low Latency and Less Homogeneous Settings based Workload Management in Enterprise Clouds [@bhuvaneshwari2016decentralized].
- Discuss Using SQLite with PHP [@feiler2015using].
- Discuss Parallel selection query processing involving index in parallel database systems [@rahayundparallel].
- Discuss Index selection [@sun2013index].
- Discuss A Copula-Based Sample Selection Binary Choice Model for Difference Analysis Among Private Bike and Bike Sharing in Lyon (France) [@havet2024copulabased].
- Discuss Index [@paper2015index].
- Discuss Large-Scale Dockless Bike Sharing Repositioning Considering Future Usage and Workload Balance [@hua2022largescale].
- Discuss Bike Sharing Systems [@paper2012bike].
- Discuss Dynamic Workload-Aware Bike Rebalancing for Bike-Sharing Systems [@luo2023dynamic].
- Discuss Analyzing Bike Repositioning Strategies Based on Simulations for Public Bike Sharing Systems: Simulating Bike Repositioning Strategies for Bike Sharing Systems [@wang2013analyzing].
- Discuss Bike Sharing Systems [@brinkmann2020bike].
- Discuss Bikeability Index in Bike-Sharing Systems: A Dual-Level Assessment Integrating Station Accessibility and Cycling Environment [@zhang2026bikeability].
- Discuss The impact of the introduction of e-bike sharing on the usage of bike sharing [@li2023impact].
- Discuss Investigation on the impact of new bike stations on a bike-share system based on a complex bike-sharing network [@kim2023investigation].
- Discuss Shared Bike Demand Prediction by Using Metro and Bike Sharing Networks’ Features [@sadeghraimoghaddam2024shared].
- Discuss Service Network Design of Bike Sharing Systems [@vogel2016service].
- Discuss Bike Sharing Atlas: Visual Analysis of Bike-Sharing Networks [@oppermann2018bike].
- Discuss Bike Sharing in the Context of Urban Mobility [@vogel2016bike].
- Discuss Large-scale dockless bike sharing repositioning considering future usage and workload balance [@hua2022largescale].
- Discuss Impacts of Bike Sharing on Transit Ridership [@aljerindimpacts].
- Discuss Figure 4: The sliding window technique for predicting hourly bike sharing demand. [@paperndfigure].
- Discuss Station-Level Hourly Bike Demand Prediction for Dynamic Repositioning in Bike Sharing Systems [@wu2019stationlevel].
- Discuss Framework for Hourly Demand Forecasting of Bike-Sharing Stations: Case Study of the Four Main Gate Areas in Seoul [@hong2022framework].
- Discuss Correction: Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2022correction].
- Discuss Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2019graph].
- Discuss Spatiotemporal Data-Driven Hourly Bike-Sharing Demand Prediction Using ApexBoost Regression [@biswas2025spatiotemporal].
- Discuss Analyzing Tail Latency in Serverless Clouds with STeLLAR [@ustiugov2021analyzing].
- Discuss Road-Specific Exploration of Bike-Sharing Usage Changes after Construction of Bike Lanes [@li2022roadspecific].
- Discuss From System-Wide to Road-Specific Exploration of Bike Trips for Changes in Bike Sharing System Usage after Construction of Bike Lanes [@li2022systemwide].
- Discuss Tradeoffs between power management and tail latency in warehouse-scale applications [@kanev2014tradeoffs].
- Discuss Research Department - Prices &amp; Statistics - Price Indexes - Wage Indexes - Minimum Hourly Rates of Wages by Industrial Groups - Correspondence, Memoranda and Blue Sheets - 1950 - 1959 [@paper2022research].
- Discuss The bike sharing rebalancing problem: Mathematical formulations and benchmark instances [@dellamico2014bike].
- Discuss Query similarity index based query preprocessing mechanism for multiapplication sharing wireless sensor networks [@verma2020query].
- Discuss Figure 6: Proposed MLP to predict future bike sharing demand. [@paperndfigure].

## Method
- Describe the deterministic local experiment and trial variants.

## Experiments
- Report every trial in the ledger and the keep/discard decision.

## Results
- Best kept trial: ablation-season-index-seed3.

## Limitations
- Clarify that this is a local scaffold until domain experiments replace the toy task.

## Conclusion
- Summarize what the evidence supports and what must be improved next.

# Evidence-Grounded Study of SQLite index tradeoffs on the UCI Bike Sharing hourly workload

## Abstract
We study SQLite index tradeoffs on the UCI Bike Sharing hourly workload with a local, auditable experiment pipeline. The best kept trial was `ablation-season-index-seed3` with primary metric 32.412629149999994.

## Introduction
The goal is to convert a research idea into a paper candidate without losing provenance.
This draft only reports evidence that exists in the run artifacts.

## Related Work
The screened literature includes MOSIQS: Persistent Memory Object Storage With Metadata Indexing and Querying for Scientific Computing [@khan2021mosiqs], AirIndex: Versatile Index Tuning Through Data and Storage [@chockchowwat2023airindex], DART [@zhang2018dart], mCerebrum [@hossain2017mcerebrum], Benchmarking PHP–MySQL Communication: A Comparative Study of MySQLi and PDO Under Varying Query Complexity [@andrijevi2025benchmarking], TASM: A Tile-Based Storage Manager for Video Analytics [@daum2021tasm], Index of SQLite Commands [@paper2019index], Database Workload Optimization [@fritchey2018database], An adaptive path index for XML data using the query workload [@min2005adaptive], AI-Based Automated SQL Query Generation for SQLite Databases in Mobile Forensics [@pawlaszczyk2026aibased], snowquery: SQL Interface to 'Snowflake', 'Redshift', 'Postgres', 'SQLite', and 'DuckDB' [@mermelstein2023snowquery], Erratum to: “An adaptive path index for XML data using the query workload” [@min2006erratum], Database Workload Optimization [@paper2009database], Database Workload Optimization [@fritchey2014database], Text Document Annotation and Retrieval Based on Content of the Document and Query Workload [@paper2016text], Introducing SQLite [@paperndintroducing], Driving through the Network: Performance and Workload under Latency and Video Impairments [@trautmannsheimer2026driving], ATTI: Workload-Aware Query Adaptive OcTree Based Trajectory Index [@meng2013atti], Query Workload Driven Summarization for P2P Query Routing [@nguyen2008query], Database Workload Optimization [@fritchey2012database], SQLite Internals [@paperndsqlite], Research on SQLite Database Query Optimization Based on Improved PSO Algorithm [@zhao2016research], A Cost-Effective Query Optimizer for Multi-Tenant Parallel RDBMSs Leveraging Workload Prediction [@danaouindcosteffective], SQLite Internals and New Features [@allen2010sqlite], adbcsqlite: 'Arrow' Database Connectivity ('ADBC') 'SQLite' Driver [@dunnington2023adbcsqlite], Analyzing SQLite Databases [@languedoc2016analyzing], Decentralized, Energy-Efficient, Low Latency and Less Homogeneous Settings based Workload Management in Enterprise Clouds [@bhuvaneshwari2016decentralized], Using SQLite with PHP [@feiler2015using], Parallel selection query processing involving index in parallel database systems [@rahayundparallel], Index selection [@sun2013index], A Copula-Based Sample Selection Binary Choice Model for Difference Analysis Among Private Bike and Bike Sharing in Lyon (France) [@havet2024copulabased], Index [@paper2015index], Large-Scale Dockless Bike Sharing Repositioning Considering Future Usage and Workload Balance [@hua2022largescale], Bike Sharing Systems [@paper2012bike], Dynamic Workload-Aware Bike Rebalancing for Bike-Sharing Systems [@luo2023dynamic], Analyzing Bike Repositioning Strategies Based on Simulations for Public Bike Sharing Systems: Simulating Bike Repositioning Strategies for Bike Sharing Systems [@wang2013analyzing], Bike Sharing Systems [@brinkmann2020bike], Bikeability Index in Bike-Sharing Systems: A Dual-Level Assessment Integrating Station Accessibility and Cycling Environment [@zhang2026bikeability], The impact of the introduction of e-bike sharing on the usage of bike sharing [@li2023impact], Investigation on the impact of new bike stations on a bike-share system based on a complex bike-sharing network [@kim2023investigation], Shared Bike Demand Prediction by Using Metro and Bike Sharing Networks’ Features [@sadeghraimoghaddam2024shared], Service Network Design of Bike Sharing Systems [@vogel2016service], Bike Sharing Atlas: Visual Analysis of Bike-Sharing Networks [@oppermann2018bike], Bike Sharing in the Context of Urban Mobility [@vogel2016bike], Large-scale dockless bike sharing repositioning considering future usage and workload balance [@hua2022largescale], Impacts of Bike Sharing on Transit Ridership [@aljerindimpacts], Figure 4: The sliding window technique for predicting hourly bike sharing demand. [@paperndfigure], Station-Level Hourly Bike Demand Prediction for Dynamic Repositioning in Bike Sharing Systems [@wu2019stationlevel], Framework for Hourly Demand Forecasting of Bike-Sharing Stations: Case Study of the Four Main Gate Areas in Seoul [@hong2022framework], Correction: Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2022correction], Graph convolutional network approach applied to predict hourly bike-sharing demands considering spatial, temporal, and global effects [@kim2019graph], Spatiotemporal Data-Driven Hourly Bike-Sharing Demand Prediction Using ApexBoost Regression [@biswas2025spatiotemporal], Analyzing Tail Latency in Serverless Clouds with STeLLAR [@ustiugov2021analyzing], Road-Specific Exploration of Bike-Sharing Usage Changes after Construction of Bike Lanes [@li2022roadspecific], From System-Wide to Road-Specific Exploration of Bike Trips for Changes in Bike Sharing System Usage after Construction of Bike Lanes [@li2022systemwide], Tradeoffs between power management and tail latency in warehouse-scale applications [@kanev2014tradeoffs], Research Department - Prices &amp; Statistics - Price Indexes - Wage Indexes - Minimum Hourly Rates of Wages by Industrial Groups - Correspondence, Memoranda and Blue Sheets - 1950 - 1959 [@paper2022research], The bike sharing rebalancing problem: Mathematical formulations and benchmark instances [@dellamico2014bike], Query similarity index based query preprocessing mechanism for multiapplication sharing wireless sensor networks [@verma2020query], Figure 6: Proposed MLP to predict future bike sharing demand. [@paperndfigure].

## Method
The configured domain experiment workspace executes the prespecified trials.
Each trial writes structured metrics, and the pipeline keeps only metric improvements.

## Experiments
- `baseline-seed0`: metric=46.5152229, decision=keep, status=ok.
- `baseline-seed1`: metric=38.69099614999999, decision=keep, status=ok.
- `baseline-seed2`: metric=45.3883545, decision=discard, status=ok.
- `baseline-seed3`: metric=53.22321424999999, decision=discard, status=ok.
- `ablation-hour-index-seed1`: metric=42.04770625, decision=discard, status=ok.
- `ablation-weather-index-seed2`: metric=49.67862115, decision=discard, status=ok.
- `ablation-season-index-seed3`: metric=32.412629149999994, decision=keep, status=ok.
- `ablation-composite-index-seed4`: metric=35.3873705, decision=discard, status=ok.

## Results
The best kept trial was `ablation-season-index-seed3` with primary metric 32.412629149999994.
# Research Decision

Decision: PROCEED

Proceed with trial `ablation-season-index-seed3` as the current evidence baseline.

## Limitations
Claims are limited to the registered assets, evaluation units, trials, metrics, and compute budget recorded in this run.

## Conclusion
The workflow now links literature, experiment metrics, and paper text through auditable artifacts.
