# AI Model Comparison Report

## Summary
**Best Model**: GRU
**Selection Basis**: highest_macro_f1
**Generated At**: 2026-04-20T15:41:11.118701+00:00

## Model Performance Table

| Model | Mode | Rows | Train Rows | Test Rows | Accuracy | Macro F1 | Status |
|-------|------|------|-----------|-----------|----------|----------|--------|
| BASELINE | not_found | - | - | - | - | - | ❌ |
| MLP | bootstrap_heuristic_fallback | 0 | - | - | - | - | ✅ |
| RNN | rnn_v1 | 800 | 640 | 160 | 0.3563 | 0.3281 | ✅ |
| GRU | gru_v1 | 800 | 640 | 160 | 0.4125 | 0.3623 | ✅ |
| LSTM | lstm_v1 | 800 | 640 | 160 | 0.3563 | 0.2833 | ✅ |
| BILSTM | bilstm_v1 | 800 | 640 | 160 | 0.3688 | 0.3346 | ✅ |

## Production Manifest

- Selected model: **gru**
- Selected macro F1: **0.3623**
- Fallback model: **mlp**
