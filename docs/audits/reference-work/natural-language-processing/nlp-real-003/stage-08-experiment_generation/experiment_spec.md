# Experiment Spec

- Topic: Transparent sentiment baselines across Amazon IMDb and Yelp reviews
- Metric: primary_metric
- Direction: maximize
- Time budget seconds: 30

## Trials
- `baseline-majority-seed0`: Majority-class baseline with bootstrap seed 0.
- `baseline-length-seed1`: Message-length heuristic with bootstrap seed 1.
- `baseline-lexicon-seed2`: Fixed sentiment lexicon with bootstrap seed 2.
- `baseline-unigram-seed3`: Laplace-smoothed unigram Naive Bayes with bootstrap seed 3.
- `ablation-unigram-alpha05-seed1`: Unigram smoothing ablation.
- `ablation-unigram-minfreq2-seed2`: Unigram vocabulary-frequency ablation.
- `ablation-bigram-seed3`: Add adjacent-token bigrams.
- `ablation-bigram-minfreq2-seed4`: Bigram frequency-filter ablation.
