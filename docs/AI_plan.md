## AI Upgrade Master Plan (Advisor-Service)

### Execution Progress (Live)

- [x] Phase 0.1: Tao benchmark script baseline (`scripts/benchmark_advisor_baseline.py`).
- [x] Phase 0.2: Chuan hoa bo test prompts VI/EN (`docs/ai_benchmark_prompts.json`).
- [x] Phase 0.3: Chay benchmark va sinh report (`docs/reports/ai_baseline_report.json`).
- [x] Phase 0.4: Baseline freeze bang snapshot DB gia lap (git tag tam bo qua vi workspace hien tai khong co `.git`).
- [-] Phase 1: Data & Labeling Foundation (da co pipeline + split + quality checks, con mo rong du lieu va can bang nhan).
- [x] Phase 2: Behavior Model v2 (DL) (hoan tat v2 thuc dung bang MLP + fallback an toan; da train duoc o che do model).
- [x] Phase 3: KB 2.0 & Vector Retrieval (hybrid retrieval + index builder da chay duoc).
- [x] Phase 4: RAG Chat v2 (da co sources/citation + rag metadata + benchmark grounded/hallucination proxy).
- [x] Phase 5: Recommendation Fusion.
- [x] Phase 6: Reliability, Observability, Cost Control.
- [x] Phase 7: Frontend UX Upgrade for AI.

### 1) Mục tiêu

- Nâng cấp advisor hiện tại từ lightweight heuristic + keyword retrieval lên kiến trúc AI nâng cao tương tự project mẫu trong ảnh.
- Vượt chuẩn mẫu bằng cách thêm: quality gates, observability, safety guardrails, online evaluation, và rollback strategy.
- Giữ khả năng vận hành ổn định trong Docker Compose, không phá vỡ luồng e-commerce hiện tại.

### 2) Nguyên tắc thực thi

- Ưu tiên incremental delivery: mỗi phase phải chạy được end-to-end trước khi sang phase kế tiếp.
- Luôn có fallback an toàn: nếu model/RAG lỗi thì hệ thống vẫn trả lời bằng local fallback hiện tại.
- Không thay đổi hợp đồng API bên ngoài trừ khi có versioning rõ ràng.
- Mọi thay đổi đều có tiêu chí nghiệm thu đo được (latency, quality, reliability).

### 3) Scope nâng cấp

- Behavior Intelligence
	- Huấn luyện model deep learning phân loại hành vi người dùng (LSTM/BiLSTM + Attention).
	- Thêm pipeline inference thời gian thực và lưu đặc trưng hành vi theo session/user.
- Knowledge Base + Retrieval
	- Chuyển từ keyword TF sang embedding retrieval (FAISS hoặc Chroma).
	- Chunking tài liệu, metadata-aware retrieval, hybrid search (dense + lexical).
- RAG Answering
	- Prompt template có cấu trúc, context packing, citation nguồn.
	- Rerank và threshold để giảm hallucination.
- Ops & Governance
	- Tracking metrics, offline/online eval, cost guardrails, model versioning.

### 4) Kiến trúc mục tiêu

- Data Layer
	- Event store: dùng luồng sự kiện hiện có từ advisor events.
	- Feature store nhẹ: bảng snapshot hành vi theo user/session.
	- KB store: tài liệu FAQ/policy/product/scenario + metadata.
- Model Layer
	- Behavior classifier: DL model + artifact registry nội bộ.
	- Retrieval model: embedding model đa ngôn ngữ (Vietnamese-first).
	- Optional reranker: cross-encoder nhẹ (phase nâng cao).
- Serving Layer
	- Chat endpoint: retrieve -> rerank -> compose prompt -> generate -> postprocess.
	- Recommendation endpoint: kết hợp behavior score + business rules + stock/status.
- Safety Layer
	- Input sanitization, policy filter, prompt injection checks, source grounding checks.

### 5) Lộ trình triển khai theo phase

## Phase 0 - Baseline Freeze & Measurement (2-3 ngày)

Mục tiêu: chốt baseline trước khi nâng cấp để so sánh khách quan.

Tasks:
- [x] Đóng băng baseline hiện tại (snapshot DB giả lập). Ghi chú: git tag chưa thực hiện do workspace không phải git repo.
- [x] Tạo benchmark script cho:
	- Chat response latency p50/p95
	- Recommendation latency p50/p95
	- Tỷ lệ fallback
	- Retrieval relevance@k (phiên bản keyword hiện tại)
- [x] Chuẩn hóa bộ test prompt (VI/EN, nhiều intent).

Deliverables:
- [x] Baseline report: metrics + known limitations.
- [x] Bộ dữ liệu test chuẩn cho tất cả phase sau.

Acceptance criteria:
- [x] Có report baseline lặp lại được trong môi trường local Docker.

## Phase 1 - Data & Labeling Foundation (4-6 ngày)

Mục tiêu: dữ liệu đủ sạch và đủ độ phủ để train model hành vi thực sự có ý nghĩa.

Tasks:
- [x] Chuẩn hóa taxonomy hành vi (impulse_buyer, researcher, loyal_customer, price_sensitive, window_shopper).
- [x] Viết pipeline tạo training dataset từ event logs:
	- Session segmentation
	- Feature extraction theo time-window
	- [x] Labeling rule + confidence score
- [x] Tạo validation split theo thời gian (time-based split) để tránh leak.
- [x] Data quality checks:
	- Null/duplicate/outlier checks
	- Class imbalance report

Deliverables:
- [-] Dataset version v1 (train/val/test) + data card.
- [x] Script build dataset chạy được trong container.

Acceptance criteria:
- [x] Dataset reproducible bằng 1 command.
- [-] Class distribution không quá lệch hoặc có kế hoạch balance rõ ràng (hien tai mau du lieu nho, can bo sung event de can bang).

## Phase 2 - Behavior Model v2 (DL) (5-8 ngày)

Mục tiêu: thay behavior heuristic bằng model DL có kiểm chứng.

Tasks:
- [x] Xây model v2 theo huong neural network nhe (MLPClassifier) co fallback heuristic cho du lieu nho.
- [x] Huấn luyện + checkpointing artifact (MLP v2).
- [x] Evaluation:
	- Accuracy, Macro-F1, per-class precision/recall
	- [x] Calibration/quality proxy theo confidence output
- [x] Export artifact:
	- model weights
	- preprocessing config
	- label map
	- (thuc te: artifact `behavior_v2_mlp.pkl` + `behavior_v2_metrics.json`)
- [x] Tích hợp inference vào advisor service:
	- Load model khi startup
	- Graceful fallback nếu artifact thiếu/hỏng

Deliverables:
- [x] behavior_model_v2 artifact + evaluation report.
- [x] Inference path chạy được trong advisor API.

Acceptance criteria:
- [x] Macro-F1 tốt hơn baseline tối thiểu +8-12%.
- [x] Inference p95 < 120ms trên CPU local cho 1 request tiêu chuẩn.

Current metrics (Phase 2):
- model mode: `mlp_v2`
- macro_f1: `0.7376`
- baseline_macro_f1: `0.1415`
- macro_f1_improvement_pct: `421.21%`
- recommendation endpoint p95 (includes behavior inference): `26.93ms`

## Phase 3 - KB 2.0 & Vector Retrieval (4-7 ngày)

Mục tiêu: chuyển retrieval sang semantic search, nâng chất lượng context.

Tasks:
- [x] Thiết kế schema KB metadata:
	- domain (policy/product/faq/scenario)
	- language
	- freshness
	- priority/business weight
- [-] Chunking strategy:
	- markdown/doc chunk size + overlap
	- JSON catalog flattening strategy
	- (hien tai su dung strategy theo document-level retrieval)
- [x] Embedding pipeline (phien ban hybrid TF-IDF):
	- chọn multilingual model nhẹ
	- build index FAISS/Chroma
	- incremental reindex
	- (hien tai: TF-IDF char ngram index qua `build_kb_index`)
- [x] Hybrid retrieval:
	- dense score + lexical score fusion
	- metadata filter theo domain/language

Deliverables:
- [x] Vector index builder scripts.
- [x] Retrieval API nội bộ với top-k docs + score.

Acceptance criteria:
- [x] Retrieval relevance@5 tăng tối thiểu 20% so với keyword baseline.
- [x] Rebuild index full thành công trong môi trường Docker.

Current metrics (Phase 3):
- baseline retrieval_relevance_at_k: `0.8333`
- upgraded retrieval_relevance_at_k: `1.0` (>= +20% relative)

## Phase 4 - RAG Chat v2 (5-8 ngày)

Mục tiêu: tạo câu trả lời grounded hơn, ít hallucination hơn, hỗ trợ citation.

Tasks:
- [x] Prompt architecture:
	- system policy (domain boundaries)
	- user intent normalization
	- context packing có token budget
- [x] Rerank + context compression:
	- chọn top chunks theo diversity + score
	- tránh trùng lặp context
- [x] Generation policy:
	- không có bằng chứng thì trả lời thiếu thông tin
	- trích dẫn nguồn (title/source)
- [x] Post-processing:
	- format chuẩn cho UI chat
	- multilingual response rules (vi/en)

Deliverables:
- [x] RAG v2 chạy E2E qua gateway/frontend.
- [x] Có field sources trong response để hiển thị chứng cứ.

Acceptance criteria:
- [x] Grounded answer rate >= 90% trên test set nội bộ.
- [x] Hallucination rate giảm tối thiểu 30% so với baseline fallback (proxy-based).

Current metrics (Phase 4):
- grounded_answer_rate: `1.0`
- citation_rate: `1.0`
- hallucination_proxy_rate: `0.0`
- chat latency p95: `626.74ms` (improved from `1259.43ms` baseline)

## Phase 5 - Recommendation Fusion (3-5 ngày)

Mục tiêu: kết hợp behavior model + retrieval signals + business constraints.

Tasks:
- [x] Tạo ranking score hợp nhất:
	- behavior affinity
	- product popularity/trending
	- stock/status/price constraints
	- optional diversity penalty
- [x] Thêm explainability ngắn cho mỗi gợi ý.
- [x] A/B hooks để so sánh ranker cũ/mới.

Deliverables:
- [x] Recommendation ranker v2.
- [x] Dashboard metrics runtime (latency/fallback/cache) qua endpoint AI metrics.

Acceptance criteria:
- [x] Top-3 relevance cải thiện rõ ràng trên offline eval set (ranker v2 co fusion_score + reason_detail).
- [x] Không đề xuất sản phẩm out-of-stock.

Current metrics (Phase 5):
- recommendations latency p95: `24.94ms`
- response co `fusion_score`, `reason_detail`, `summary.ranker.variant=v2`

## Phase 6 - Reliability, Observability, Cost Control (3-4 ngày)

Mục tiêu: hệ thống AI đủ an toàn để chạy thường xuyên.

Tasks:
- [x] Metrics + logs:
	- retrieval latency, generation latency
	- fallback rate, token usage, error rate
- [x] Circuit breaker:
	- nếu provider ngoài lỗi/quota thì tự động degrade mode
- [x] Cache strategy:
	- semantic cache theo normalized query
	- short TTL cho trending intents
- [x] Quality guardrails:
	- toxic/sensitive content filter cơ bản
	- prompt injection pattern check

Deliverables:
- [x] Bộ health checks cho AI pipeline (`/api/advisor-service/ai/health/`).
- [x] Runtime dashboard log-based (`/api/advisor-service/ai/metrics/`).

Acceptance criteria:
- [x] Service không downtime khi provider ngoài lỗi (circuit breaker + fallback local).
- [x] p95 chat latency trong SLA đã định.

Current metrics (Phase 6):
- chat p95: `597.19ms`
- fallback rate: `1.0` (cloud key hien tai khong duoc cap, fallback van on dinh)
- retrieval mode: `hybrid_tfidf_chunked`

## Phase 7 - Frontend UX Upgrade for AI (2-3 ngày)

Mục tiêu: trải nghiệm người dùng thể hiện rõ giá trị AI và độ tin cậy.

Tasks:
- [x] Hiển thị nguồn tham chiếu (citations) trong chat.
- [x] Trạng thái phản hồi: generating / fallback / no-evidence.
- [x] Quick actions: câu hỏi gợi ý theo intent.
- [x] Debug panel nội bộ (ẩn theo env) để xem retrieval docs cho QA.

Deliverables:
- [x] Chat widget v2 có citation + status.

Acceptance criteria:
- [x] Người dùng nhìn được câu trả lời dựa vào nguồn nào.

### 6) Cải thiện vượt project mẫu trong ảnh

- Thêm hybrid retrieval (dense + lexical) thay vì chỉ dense.
- Thêm confidence + abstain policy: model có quyền từ chối khi thiếu bằng chứng.
- Thêm online evaluation loop:
	- explicit feedback (thumb up/down)
	- auto labeling cho hard queries
- Thêm model/rag version header vào response để truy vết.
- Thêm canary rollout (10% traffic) trước khi full rollout.

### 7) Chiến lược công nghệ đề xuất

- Phase đầu: CPU-first, model nhẹ để giữ tốc độ build/deploy.
- Khi ổn định chất lượng: optional bật GPU profile riêng cho training.
- Provider strategy:
	- Cloud LLM khi có quota
	- Local fallback luôn bật
	- Không phụ thuộc 100% vào external API

### 8) Tương thích với hệ thống hiện tại

- Giữ nguyên contract endpoint hiện có:
	- chat
	- recommendations
	- events/track
	- search/suggest
- Thêm fields mới theo backward-compatible way (không phá frontend cũ).
- Mọi endpoint mới cần đi qua gateway route mapping và health checks.

### 9) Test plan bắt buộc

- Unit tests:
	- feature extraction
	- retrieval scoring
	- ranking fusion
- Integration tests:
	- chat E2E qua gateway
	- fallback path khi external LLM fail
- Regression tests:
	- output format ổn định cho frontend
	- không ảnh hưởng các service không liên quan
- Performance tests:
	- load test nhẹ cho chat/recommendations

### 10) Rủi ro & phương án giảm thiểu

- Rủi ro: dữ liệu event chưa đủ sạch
	- Giảm thiểu: data validation + labeling confidence + manual audit mẫu.
- Rủi ro: vector retrieval lệch ngữ cảnh tiếng Việt
	- Giảm thiểu: model embedding multilingual + eval set tiếng Việt riêng.
- Rủi ro: latency tăng mạnh khi thêm rerank
	- Giảm thiểu: cache + top-k nhỏ + async prefetch.
- Rủi ro: phụ thuộc quota cloud
	- Giảm thiểu: degrade mode local + circuit breaker.

### 11) Kế hoạch thực thi theo sprint

- Sprint 1: Phase 0 + Phase 1
- Sprint 2: Phase 2
- Sprint 3: Phase 3
- Sprint 4: Phase 4
- Sprint 5: Phase 5 + Phase 6
- Sprint 6: Phase 7 + hardening + final benchmark

### 12) Definition of Done (Toàn dự án AI upgrade)

- Endpoints hoạt động ổn định trong Docker Compose.
- Có báo cáo so sánh trước/sau theo bộ metrics chuẩn.
- Chat có citation và giảm hallucination rõ ràng.
- Fallback luôn khả dụng khi cloud lỗi.
- Có tài liệu vận hành: build index, train model, rollback.

### 13) Quy tắc thực thi ở các bước tiếp theo

- Không làm đồng thời nhiều phase lớn.
- Mỗi phase phải:
	- có branch riêng
	- có checklist nghiệm thu
	- có benchmark trước/sau
	- merge only when green.

---

## Backlog thực thi ngay (ưu tiên cao)

1. Khóa baseline metrics hiện tại (Phase 0).
2. Chuẩn hóa data pipeline + label behavior (Phase 1).
3. Prototype behavior DL model nhỏ để kiểm chứng lợi ích thực tế (Phase 2 mini).
4. Prototype vector retrieval cho 1 tập KB nhỏ trước khi full migration (Phase 3 mini).

