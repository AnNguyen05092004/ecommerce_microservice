# 🎬 AI Update - Action Plan (Phase 6 & 7)

## Overview Phase 6: Observability & Quality Gates

**Goal:** Make AI system measurable, reliable, production-ready.
**Timeline:** 5-6 ngày
**Deliverable:** Metrics API + quality gates + structured logging

---

## PHASE 6A: Structured Logging & Metrics (Days 1-2)

### Task 6A.1: Create logging config
- [x] Location: `services/advisor-service/advisor/logging_config.py`
- [x] What: JSON formatter for structured logs
- [x] Needs:
  - request_id (UUID generator)
  - timestamp, level, logger, message
  - Custom fields: user_id, operation, duration_ms, result_code

### Task 6A.2: Update views.py with structured logging
- [ ] Add logging decorator cho mỗi endpoint
- [ ] Format: `{request_id} {operation} {duration_ms}ms {status_code} {details}`
- [ ] Examples:
  - Chat request: log query, retrieval time, LLM time, response
  - Recommendation: log user_id, behavior_profile, items_returned
  - Event track: log event_type, user_id, session_id

### Task 6A.3: Create metrics collector
- [x] Location: `services/advisor-service/advisor/ml/metrics.py`
- [x] Class: `MetricsCollector`
- [x] Methods:
  - `record_latency(operation, duration_ms)` → track p50, p95, p99
  - `record_error(operation, error_code)` → track error rate
  - `record_model_prediction(model_name, confidence)` → track prediction distribution
  - `get_snapshot()` → return aggregated metrics dict
- [x] Storage: in-memory ring buffer (keep last 1000 records)

### Task 6A.4: Add metrics API endpoints
- [x] GET `/health` → include `advisor_status` (ok/degraded/error)
- [x] GET `/metrics/latest` → current snapshot (p50 chat latency, error rate, etc.)
- [x] GET `/metrics/timeseries?operation=chat&window=1h` → historical metrics
- [x] Update: `advisor/urls.py` + `advisor/views.py`

---

## PHASE 6B: Quality Gates & Safety (Days 3-4)

### Task 6B.1: Add confidence scores to behavior model
- [x] File: `services/advisor-service/advisor/ml/behavior_v2.py`
- [x] Modify: `predict_proba()` to return (class, confidence, top3_classes)
- [x] Rule: if max_prob < 0.4 → return `"uncertain"` class + low confidence

### Task 6B.2: Add confidence threshold to recommendation
- [x] File: `services/advisor-service/advisor/ml/recommend.py`
- [x] Filter items with score < min_confidence
- [x] Min confidence: 0.5 for exact recommendations, 0.3 for trending
- [x] Return confidence score in response (for frontend display)

### Task 6B.3: Enhance chat safety gates
- [x] File: `services/advisor-service/advisor/views.py` (chat endpoint)
- [x] Before response: check source grounding
  - Verify retrieved docs contain answer keywords
  - If not found → return "Tôi không tìm được thông tin chính xác"
- [x] Add source attribution:
  - Include source document title/URL in response
  - Format: `"Dựa trên: [FAQ - Chính sách bảo hành]"`

### Task 6B.4: Rate limiting & cost control
- [x] File: Create `services/advisor-service/advisor/middleware.py`
- [x] Per-user limit: max 50 requests/hour
- [x] Per-session: max 500 tokens total
- [x] On exceed: return 429 + helpful message
- [x] Update: `advisor_service/settings.py` (add middleware)

---

## PHASE 7A: KB & Retrieval Enhancements (Days 5-7)

### Task 7A.1: Expand KB content for 12 product groups
- [x] File: `services/advisor-service/advisor/knowledge_base/default_documents.json`
- [x] For each of 12 groups (computer, mobile, clothes, tablet, audio, wearable, component, peripheral, monitor, accessory, charging, book):
  - Add 2-3 FAQ entries (e.g., "How to choose", "Warranty", "Returns")
  - Add product specs template
  - Add common issues & troubleshooting
- [x] Target: 40-50 documents total (currently ~20)
- [x] Format: keep existing schema (id, title, content, category, metadata)

### Task 7A.2: Add metadata indexing
- [x] File: `services/advisor-service/advisor/ml/kb_vector.py`
- [x] Update `KBChunk` NamedTuple: add metadata (category, tags, priority, date)
- [x] Update retrieval:
  - Category filter: if user interested in "laptop" → boost KB docs with category="computer"
  - Temporal: if query about "promo today" → filter docs with current_date in date_range
  - Priority: multiply relevance_score by priority weight (1.0 default, 1.5 for important)

### Task 7A.3: Add semantic reranking (optional, Phase 8)
- [x] File: `services/advisor-service/advisor/ml/kb_vector.py`
- [x] Placeholder: add function `rerank_documents(query, docs, method='simple')`
- [x] Method `simple`: use cosine similarity threshold (0.6)
- [x] Method `cross_encoder`: (skip in MVP, Phase 8)

---

## PHASE 7B: Recommendation for 12 Product Groups (Days 6-8)

### Task 7B.1: Update behavior model for new categories
- [x] File: `services/advisor-service/advisor/ml/behavior_v2.py`
- [x] Modify: interaction features now include 12 categories (not just 3)
- [x] Update: `_build_training_frame()` to handle new categories
- [x] Retrain: run `train_behavior_v2()` with seed data

### Task 7B.2: Expand recommendation logic
- [x] File: `services/advisor-service/advisor/ml/recommend.py`
- [x] Change: `recommend_products()` to accept `product_types=(...)` parameter
- [x] Add strategy: cross-category recommendations
  - If user viewed "laptop" → suggest "charging", "peripheral"
  - If user viewed "phone" → suggest "accessory", "charging"
  - Build cross_category_rules dict
- [x] Add diversity: ensure < 30% same category in results

### Task 7B.3: Add trending & inventory awareness
- [x] File: `services/advisor-service/advisor/ml/recommend.py`
- [x] Add function: `get_trending_products(category, days=7)` 
  - Query events from last 7 days, count clicks per product
  - Return top 3 per category
- [x] Add filter: exclude items with stock=0
- [x] Ranking boost: in-stock items get +0.2 score

### Task 7B.4: Update recommendation API
- [x] File: `services/advisor-service/advisor/views.py`
- [x] Modify `/advisor/recommendations/` endpoint:
  - Now return confidence score for each item
  - Include reason field: `"Bình thường được xem cùng laptop"` or `"Đang trending"`
  - Include category diversity stats

---

## PHASE 7C: Frontend UX Enhancements (Days 9-10)

### Task 7C.1: Improve chat widget
- [x] File: `frontend/store/templates/store/home.html` + `frontend/store/static/store/js/advisor-widget.js` (create new)
- [x] Changes:
  - Add suggestion chips at bottom: `["Laptop nào tốt?", "Pin trâu?", "Giá dưới 10tr?"]`
  - Show source in message: `[Source: FAQ - Chính sách bảo hành]` link
  - Better error UI: instead of generic error → `"Hệ thống tạm gặp quá tải, vui lòng thử lại"`
  - Persist chat history: localStorage for recent 10 messages per session

### Task 7C.2: Better recommendation display
- [x] File: `frontend/store/templates/store/product_detail.html`
- [x] Update recommendation section:
  - Add confidence badge (⭐ Matching: 85%)
  - Add reason text: `"Customers who liked this also viewed..."`
  - Add "Similar products" link

### Task 7C.3: Admin metrics dashboard (optional, Phase 8)
- [x] File: Create `frontend/store/templates/store/admin/ai_metrics.html`
- [x] Show:
  - Last 10 events (chat, recommendation, errors)
  - Current metrics: p95 latency, error rate, fallback rate
  - Model versions & status
- [x] Access: `/admin/ai-metrics` (staff only)

---

## Files Summary Table

| Phase | File | Task | Lines | Priority | Risk |
|-------|------|------|-------|----------|------|
| 6A | advisor/logging_config.py | New logging formatter | ~50 | High | Low |
| 6A | advisor/ml/metrics.py | New metrics collector | ~150 | High | Low |
| 6A | advisor/views.py | Add logging decorator | ~100 | High | Medium |
| 6A | advisor/urls.py | Add metrics endpoints | ~10 | High | Low |
| 6B | advisor/ml/behavior_v2.py | Confidence scores | ~20 | Medium | Low |
| 6B | advisor/ml/recommend.py | Confidence threshold | ~30 | Medium | Low |
| 6B | advisor/views.py | Chat safety gates | ~40 | High | Medium |
| 6B | advisor/middleware.py | Rate limiting (NEW) | ~60 | Medium | Medium |
| 7A | advisor/knowledge_base/default_documents.json | Expand KB | +30 docs | High | Low |
| 7A | advisor/ml/kb_vector.py | Metadata indexing | ~80 | Medium | Medium |
| 7B | advisor/ml/recommend.py | 12-group expansion | ~100 | High | Medium |
| 7B | advisor/views.py | Update recommendation API | ~30 | High | Low |
| 7C | frontend/store/templates/home.html | Chat widget UX | ~50 | Medium | Low |
| 7C | frontend/store/static/js/advisor-widget.js | Chat JS (NEW) | ~200 | Medium | Medium |

---

## Testing Plan per Phase

### 6A Testing
- Unit: test logging formatter → check JSON, required fields
- Integration: call chat API → check metrics recorded
- Acceptance: metrics API returns valid data

### 6B Testing
- Unit: test confidence threshold logic
- Integration: recommend with low confidence items → filtered
- Acceptance: rate limiter blocks >50 requests/hour

### 7A Testing
- Unit: test metadata filter → category matches
- Integration: search "laptop" → KB returns computer docs first
- Acceptance: KB covers 40+ docs, all 12 categories

### 7B Testing
- Unit: test cross-category rule logic
- Integration: recommend for "laptop" → include charging + peripheral
- Acceptance: diversify < 30% same category

### 7C Testing
- Manual: chat widget loads, suggestion chips clickable
- Manual: recommendation cards show confidence badge
- Acceptance: no JS errors in console

---

## Success Criteria (Definition of Done per Phase)

### Phase 6 Done When:
- [x] Structured logs appear in docker logs
- [x] GET /metrics/latest returns non-empty dict
- [x] Chat confidence < 0.6 returns fallback response
- [x] Rate limit blocks 51st request

### Phase 7 Done When:
- [x] KB has 40+ documents covering 12 groups
- [x] Recommendation includes "recommended because" reason
- [x] Cross-category ratio tracked in metrics
- [x] Chat widget shows source attribution
- [x] All E2E flows pass smoke test

---

## Estimated Effort & Timeline

| Phase | Days | Notes | Blocking |
|-------|------|-------|----------|
| 6A (Logging) | 1-2 | Simple; no dependencies | No |
| 6B (Safety) | 1-2 | Medium; touch views.py | 6A done |
| 7A (KB) | 2 | Content work; low code | 6A done |
| 7B (Recommend) | 2-3 | Logic work; test tricky | 6A + 7A |
| 7C (Frontend) | 1-2 | UX; simple JS | Any time |
| **Total** | **7-11 days** | Parallel possible for 6A+7A+7C | - |

**Can parallelize:** 6A, 7A+7C (frontend)  
**Must sequence:** 6B → 7B

---

## Next Steps After This Plan

1. **Approve tasks** → confirm priority order
2. **Assign dates** → target completion per phase
3. **Start 6A** → logging infrastructure first (enables rest)
4. **Weekly reviews** → update plan_update.md with progress, blockers

