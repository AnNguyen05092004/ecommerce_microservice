# 📊 AI Architecture Assessment & Update Plan

## 🎯 Yêu Cầu từ Ảnh (Sơ đồ Bảng Đen)

Từ ảnh gửi, yêu cầu AI bao gồm:
1. **Deep Learning** → Behavior model, next-action prediction
2. **AI Server** → Advisor service xử lý requests
3. **Database** → Event store, KB store, feature store
4. **Knowledge Base** → FAQ, policies, products, scenarios
5. **RAG** → Retrieve source documents → Generate answer
6. **Click Tracking** → Browser events
7. **Search/Semantic** → Query understanding, document retrieval
8. **Recommendations** → Cross-category, time-aware, trend-based
9. **Session State** → User context, conversation history
10. **Observability** → Monitoring, metrics, quality gates

---

## ✅ Trạng Thái Hiện Tại (Từ plan_update.md)

### Hoàn tất (Phase 0-5):
- [x] Event tracking infrastructure (frontend → gateway → advisor-service)
- [x] ETL pipeline (`build_behavior_dataset`)
- [x] Baseline model (fallback heuristic)
- [x] GRU model (next-category prediction, fallback transition)
- [x] KB bootstrap + keyword retrieval
- [x] Hybrid KB (lexical + vector fallback)
- [x] Chat API with fallback (VI/EN)
- [x] Recommendation endpoint
- [x] Frontend widget integration
- [x] Docker full stack verification

### Trong Tiến Hành:
- [-] Phase 6: Reliability, Observability, Cost Control
- [-] Phase 7: Frontend UX Upgrade

---

## 🔍 Chi Tiết Thành Phần Hiện Tại

### 1. Advisor Service Stack

#### a) Event Tracking
**File:** `advisor/views.py` + `advisor/models.py`
- Track events: `page_view`, `product_click`, `search`, `chat_message`, `recommendation_click`
- Method: POST `/advisor/events/track/`
- Storage: SQLite UserEvent table

**Trạng thái:** ✅ Functional, nhưng thiếu:
- [ ] Event schema validation (chỉ có basic serializer)
- [ ] Real-time event stream (batch processing chỉ)
- [ ] Event deduplication & sampling
- [ ] Privacy/PII masking

#### b) Behavior Model
**File:** `advisor/ml/behavior_v2.py`
- Model: MLP classifier (fallback khi data < 12)
- Classes: `impulse_buyer`, `researcher`, `loyal_customer`, `price_sensitive`, `window_shopper`
- Training: từ UserEvent + product interactions
- Inference: predict behavior profile từ session history

**Trạng thái:** ✅ Functional, nhưng:
- [ ] Không log feature importance
- [ ] Không có online learning/update
- [ ] Không có A/B testing framework
- [ ] Không track model drift

#### c) Next-Category Model (GRU)
**File:** `advisor/ml/gru.py`
- Model: GRU RNN (fallback transition heuristic)
- Input: Sequence of product interactions
- Output: Next likely product category

**Trạng thái:** ✅ Functional nhưng:
- [ ] Không có attention visualization
- [ ] Không có confidence scores
- [ ] Không có per-user fine-tuning

#### d) Knowledge Base
**File:** `advisor/ml/kb.py` + `advisor/ml/kb_vector.py`
- KB source: `advisor/knowledge_base/default_documents.json`
- Retrieval: Hybrid (lexical BM25 + vector fallback)
- Chunking: 300 tokens with 50 token overlap
- Language: VI/EN

**Trạng thái:** ✅ Functional, nhưng:
- [ ] Không có metadata indexing (category, date, relevance)
- [ ] Không có reranking step
- [ ] Không có citation/source tracking
- [ ] KB content update không tự động (manual JSON)

#### e) RAG Chat
**File:** `advisor/views.py` (chat endpoint)
- API: POST `/advisor/chat/`
- Flow: retrieve → compose prompt → call LLM
- Provider: Google Cloud VertexAI (fallback local generation)
- Safety: Prompt injection + toxic content filtering

**Trạng thái:** ✅ Functional, nhưng:
- [ ] Cloud LLM disabled (quota exceeded)
- [ ] Local generation très simplistic
- [ ] Không có reranking
- [ ] Không có source attribution
- [ ] Không có response quality gates

#### f) Recommendation Engine
**File:** `advisor/ml/recommend.py`
- Strategy: behavior-aware + trending + stock filter
- Data source: product catalog từ gateway
- Personalization: user behavior profile + session
- Diversification: mix category, price range

**Trạng thái:** ✅ Functional, nhưng:
- [ ] Không cover cả 12 product types (mới có 3)
- [ ] Không có diversity metrics
- [ ] Không có novelty/serendipity
- [ ] Không track recommendation CTR/conversion

#### g) Cache & Performance
**File:** `advisor/views.py`
- Cache: Django cache (TTL 45s)
- Metrics: latency p50/p95 tracked in memory deque
- Circuit breaker: để tránh cascading failures

**Trạng thái:** ⚠️ Basic, cần:
- [ ] Cache invalidation strategy
- [ ] Metrics persistence (PostgreSQL)
- [ ] SLA monitoring
- [ ] Cost per query tracking

---

## 🛠️ Update Plan (Phase 6 & 7 + Enhancements)

### Phase 6A: Observability & Monitoring (3-4 ngày)

**Mục tiêu:** Add comprehensive logging, metrics, alerts.

#### 6A.1: Structured Logging
- [ ] Add logging để mỗi API call: request_id, user_id, operation, duration, result
- [ ] Log model inference: model_name, features, prediction, confidence
- [ ] Log retrieval: query, docs_retrieved, relevance_scores
- [ ] Format: JSON line logs để easy parsing

**File cần update:** `advisor/views.py` + tạo `advisor/logging_config.py`

#### 6A.2: Metrics Collection
- [ ] Endpoint latency: request/chat/recommendation → p50, p95, p99
- [ ] Model accuracy: behavior prediction vs actual, recommendation CTR
- [ ] Retrieval quality: MRR@10, NDCG@5 (từ event logs)
- [ ] Error rate: request errors, provider failures, fallback rate
- [ ] Cost: per request, per user, per day

**File cần update:** `advisor/ml/metrics.py` (new)

#### 6A.3: Observability API
- [ ] GET `/advisor/health` → detailed service status
- [ ] GET `/advisor/metrics/latest` → current metrics snapshot
- [ ] GET `/advisor/metrics/timeseries` → historical metrics
- [ ] POST `/advisor/admin/reset-metrics` → để testing

**File cần update:** `advisor/views.py` + `advisor/urls.py`

---

### Phase 6B: Quality Gates & Safety (2-3 ngày)

**Mục tiêu:** Add confidence thresholds, response validation, cost controls.

#### 6B.1: Response Confidence Thresholds
- [ ] Chat: nếu confidence < 0.6 → return "Tôi không chắc" + fallback
- [ ] Recommendation: filter < 0.4 confidence
- [ ] Behavior: add confidence score đến frontend

**File cần update:** `advisor/ml/behavior_v2.py` + `advisor/ml/recommend.py`

#### 6B.2: Hallucination Detection
- [ ] Verify retrieved docs chứa answer keywords
- [ ] Check generated text không trái với KB
- [ ] Add source attribution requirement

**File cần update:** `advisor/views.py` (chat endpoint)

#### 6B.3: Cost Control & Rate Limiting
- [ ] Per-user rate limit: max 50 requests/hour
- [ ] Per-session cost budget: max 500 tokens/session
- [ ] Model cache: reuse recent queries < 5min

**File cần update:** `advisor/views.py` + middleware

---

### Phase 7A: KB & Retrieval Enhancements (3-4 ngày)

**Mục tiêu:** Improve content coverage & retrieval quality.

#### 7A.1: Expand KB Coverage for 12 Product Groups
- [ ] Product specs template cho 12 categories
- [ ] FAQ per category (mua, bảo hành, thanh toán, vận chuyển)
- [ ] Promo/khuyến mãi policy
- [ ] Troubleshooting guides

**File cần update:** `advisor/knowledge_base/default_documents.json` (mở rộng 3x)

#### 7A.2: Add Metadata-Aware Retrieval
- [ ] Index documents với metadata (category, product_type, date, priority)
- [ ] Support category-specific queries
- [ ] Add temporal filtering (e.g., promo valid today)

**File cần update:** `advisor/ml/kb_vector.py`

#### 7A.3: Semantic Reranking
- [ ] Use cross-encoder (tiny model) để rerank top-5 docs
- [ ] Or use simple semantic matching (cosine similarity threshold)

**File cần update:** `advisor/ml/kb_vector.py`

---

### Phase 7B: Recommendation for 12 Product Groups (2-3 ngày)

**Mục tiêu:** Extend recommendation để cover toàn bộ catalog.

#### 7B.1: Expand Behavior Profile
- [ ] Add interaction types cho 12 groups (tablet, audio, accessory, etc.)
- [ ] Update behavior model training data
- [ ] Test trên diversified catalog

**File cần update:** `advisor/ml/behavior_v2.py` + `advisor/ml/recommend.py`

#### 7B.2: Cross-Category Recommendation
- [ ] Rule: nếu laptop → suggest charging + peripheral
- [ ] Trend-based: đếm cross-purchase frequently
- [ ] Diversity: không để 3 cái cùng category

**File cần update:** `advisor/ml/recommend.py`

#### 7B.3: Trending & Inventory-Aware
- [ ] Track daily trending (top 5 per category)
- [ ] Filter: exclude out-of-stock items
- [ ] Ranking: popular → but prefer in-stock

**File cần update:** `advisor/ml/recommend.py`

---

### Phase 7C: Frontend UX Enhancements (2-3 ngày)

**Mục tiêu:** Better user experience in chat & recommendations.

#### 7C.1: Chat Widget Improvements
- [ ] Add suggestion chips (quick questions)
- [ ] Show sources (KB doc title)
- [ ] Better error messages (thay vì "API error")
- [ ] Conversation context persistence (localStorage)

**File cần update:** `frontend/store/templates/store/home.html` + JS

#### 7C.2: Recommendation Cards
- [ ] Add "Why recommended? (behavioral reason)"
- [ ] Show confidence/score
- [ ] Add "Similar products" section

**File cần update:** `frontend/store/templates/store/product_detail.html`

#### 7C.3: Admin Dashboard
- [ ] Simple page để view recent metrics
- [ ] Endpoint status
- [ ] Model versions

**File cần update:** Create `frontend/store/views.py` (advisor admin endpoint)

---

## 📋 Implementation Checklist

### Must-Have (Core Requirements)
- [ ] Observability: structured logging + metrics API
- [ ] Safety gates: confidence thresholds + hallucination checks  
- [ ] KB expansion: cover 12 product groups
- [ ] Recommendation extension: all categories + diversification
- [ ] Frontend: basic UX improvement for chat & recommendation

### Nice-to-Have (Phase 8+)
- [ ] Fine-tuning behavior model trên real production data
- [ ] Online model updates (incremental learning)
- [ ] A/B testing framework
- [ ] Multi-turn conversation context
- [ ] Voice input support

---

## 🚀 Execution Order (Priority)

1. **Phase 6A (Observability)** → Start immediately to measure
2. **Phase 7B (12-group Recommendation)** → Product expansion
3. **Phase 6B (Safety)** → Quality gates before public
4. **Phase 7A (KB)** → Content coverage
5. **Phase 7C (Frontend)** → UX polish

**Estimated timeline:** 12-15 ngày total (nếu làm tuần tự)

---

## 🔄 Verification Strategy

Cho mỗi phase:
1. Unit test: logic correctness
2. Integration test: API E2E
3. Smoke test: basic flow functional
4. Load test: latency acceptable (< 500ms p95)
5. Quality test: metrics collected correctly

---

## 📞 Questions to Clarify

1. **Cloud LLM (Phase 6)**: còn muốn dùng Google Cloud VertexAI không hay chuyển sang local/OSS?
2. **KB Content**: update KB manual hay tích hợp từ product catalog API?
3. **Behavior Labeling**: còn dataset nào từ production để retrain behavior model không?
4. **Frontend**: prioritize chat UX hay recommendation UX trước?

