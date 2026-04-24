# Phase 1: ML Models Implementation - Quick Start Guide

## What's Been Implemented

✅ **New Machine Learning Models:**
- `services/advisor-service/advisor/ml/behavior_lstm.py` - LSTM sequence model
- `services/advisor-service/advisor/ml/behavior_bilstm.py` - BiLSTM (bidirectional LSTM) model
- Django management commands for training both models
- Complete with inference, fallback handling, and metrics tracking

✅ **Model Comparison Suite:**
- `scripts/compare_models.py` - Compares all 5 models (Baseline, MLP, GRU, LSTM, BiLSTM)
- Auto-generates: comparison table, accuracy/F1 charts, metrics heatmap
- Selects "best model" based on macro F1 score
- Generates markdown report with recommendations

✅ **User Dataset Export:**
- `scripts/export_user500_csv.py` - Exports users to standardized CSV format
- Generates user500.csv with all behavior profiles
- Creates metadata JSON with distribution analysis
- Supports arbitrary user limits (default: 500)

✅ **Automated Pipeline:**
- `scripts/setup_ai_models.py` - Orchestrates complete workflow
- Runs all training steps sequentially
- Generates final comparison report
- Interactive error handling

---

## 🚀 Quick Start (Choose One Option)

### Option A: Full Automated Pipeline (Recommended)
```bash
# Navigate to project root
cd /Users/an/Documents/Ptit\ Docs/Kiến\ trúc\ và\ thiết\ kế\ pm/KIEMTRA01

# Run full pipeline (trains all models + generates report)
docker compose exec advisor-service python scripts/setup_ai_models.py

# Or from host (if docker is running):
cd services/advisor-service && python ../../scripts/setup_ai_models.py
```

### Option B: Step-by-Step Manual

#### 1. Ensure Project is Running
```bash
docker compose up -d --build
docker compose exec advisor-service python manage.py migrate
```

#### 2. Build Behavior Dataset
```bash
docker compose exec advisor-service python manage.py build_behavior_dataset
```

#### 3. Train Individual Models
```bash
# Baseline (LogisticRegression)
docker compose exec advisor-service python manage.py train_baseline

# MLP (existing)
docker compose exec advisor-service python manage.py train_behavior_v2

# GRU (existing)
docker compose exec advisor-service python manage.py train_behavior_gru

# LSTM (NEW)
docker compose exec advisor-service python manage.py train_behavior_lstm

# BiLSTM (NEW)
docker compose exec advisor-service python manage.py train_behavior_bilstm
```

#### 4. Export User500 Dataset
```bash
docker compose exec advisor-service python scripts/export_user500_csv.py
```

#### 5. Compare Models & Generate Report
```bash
docker compose exec advisor-service python scripts/compare_models.py
```

---

## 📊 Expected Output

### After Training (in `services/advisor-service/artifacts/`):
```
✅ behavior_lstm.pt              # LSTM weights
✅ behavior_lstm_config.pkl      # LSTM config
✅ behavior_lstm_metrics.json    # LSTM metrics (accuracy, F1, etc.)

✅ behavior_bilstm.pt            # BiLSTM weights
✅ behavior_bilstm_config.pkl    # BiLSTM config
✅ behavior_bilstm_metrics.json  # BiLSTM metrics
```

### After Comparison (generated charts):
```
✅ 01_accuracy_comparison.png    # Bar chart: all models accuracy
✅ 02_f1_comparison.png          # Bar chart: all models F1 scores
✅ 03_metrics_heatmap.png        # Heatmap: all metrics side-by-side
✅ model_comparison_report.md    # Detailed markdown report
```

### After User Export:
```
✅ user500.csv                   # 500 users with behavior profiles
✅ user500_metadata.json         # Distribution analysis & stats
```

---

## 🔍 Review Results

### 1. Check Metrics
```bash
# View all model metrics
cat services/advisor-service/artifacts/behavior_*_metrics.json | jq .

# Best model selection criteria: macro_f1 score
```

### 2. View Comparison Report
```bash
# Read markdown report (shows best model + recommendations)
cat services/advisor-service/artifacts/model_comparison_report.md
```

### 3. Inspect User Dataset
```bash
# View first 5 rows
head -6 services/advisor-service/artifacts/user500.csv

# Check distribution
cut -d',' -f2 services/advisor-service/artifacts/user500.csv | tail -n +2 | sort | uniq -c
```

---

## 🎯 Next Steps (Phase 2)

### Task 2.1: Update Recommendation Engine
- Modify `services/advisor-service/advisor/ml/recommend.py`
- Use best model from comparison for behavior classification
- Current: hardcoded behavior profile → **New: model-based inference**

### Task 2.2: Enhance Chat Widget
- Add behavior-specific greeting in chat
- Show top 3 recommended products for user's profile
- Add "Why we recommend this" explanation

### Task 3: Integration Testing
- Run full chat flow with new models
- Verify inference latency < 200ms
- Test fallback handling

---

## 🛠️ Troubleshooting

### PyTorch Not Available
```
Error: TORCH_AVAILABLE = False
Fix: pip install torch torchvision torchaudio
```

### Matplotlib Not Available
```
Warning: Matplotlib not available. Skipping visualization.
Fix: pip install matplotlib seaborn
```

### Insufficient Data
```
Error: Need ≥10 labeled sequences, got X
Fix: Seed more user events first:
     docker compose exec advisor-service python manage.py seed_behavior_events --count 100
```

### Memory Issues During Training
```
Solution: Reduce batch size in model files
         batch_size = min(16, len(X_train))  # Change 32 to 16
```

---

## 📋 Model Architecture Summary

| Model | Type | Layers | Parameters | Inference Speed |
|-------|------|--------|-----------|-----------------|
| Baseline | LogisticRegression | 1 | ~150 | ⚡⚡⚡ |
| MLP | MLPClassifier | 2 | ~2K | ⚡⚡ |
| GRU | Recurrent | 2 | ~4K | ⚡ |
| **LSTM** | Recurrent | 2 | ~5K | ⚡ |
| **BiLSTM** | Bidirectional | 2 | ~8K | ⚡ |

---

## ✨ What's Different in New Models

### LSTM vs GRU:
- **LSTM**: 4 gates (input, output, forget, cell) → captures longer dependencies
- **GRU**: 3 gates → simpler, faster training
- **Better for**: Complex temporal patterns in event sequences

### BiLSTM Advantage:
- Processes sequence forward **AND** backward
- Richer context: sees future events when processing past
- **Accuracy boost**: typically +2-4% vs unidirectional

---

## 🎓 How It Works

### Training Flow:
```
UserEvent data → Encode sequences → Split (train/val/test)
                                    ↓
                          Train model 25 epochs
                                    ↓
                          Evaluate on test set
                                    ↓
                          Save weights + metrics
```

### Inference Flow:
```
User events (recent) → Encode as sequence (max 30 steps)
                           ↓
                    Load model weights
                           ↓
                    Forward pass → logits
                           ↓
                    Softmax → probabilities
                           ↓
                    Return top class + confidence
```

---

Created: Phase 1 Implementation
Files: 7 new files + 3 updated Django commands
Status: ✅ Ready for testing
