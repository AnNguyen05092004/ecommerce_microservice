# 2. Sử dụng tập data để xây dựng AISERVICE

## 2a) Xây dựng 3 mô hình RNN, LSTM, biLSTM để dự đoán và phân loại

### Mục tiêu
- Dự đoán và phân loại hành vi người dùng từ dữ liệu tương tác trong hệ e-commerce.
- So sánh 3 mô hình tuần tự: RNN, LSTM, biLSTM.
- Chọn mô hình tốt nhất `model_best` dựa trên độ đo phù hợp.

### Dữ liệu sử dụng
- Dữ liệu gốc: `services/advisor-service/data_user500.csv` (500 user, dạng event-level gồm `user_id`, `product_id`, `action`, `timestamp`).
- Dữ liệu đặc trưng tổng hợp: `services/advisor-service/data_user500_features.csv` (các cột đếm hành vi).
- Trong pipeline huấn luyện model tuần tự, dữ liệu được đưa về dạng chuỗi sự kiện theo user và lưu tại:
	- `services/advisor-service/artifacts/behavior_sequences.json`
	- `services/advisor-service/artifacts/behavior_dataset.csv`
	- `services/advisor-service/artifacts/behavior_train.csv`
	- `services/advisor-service/artifacts/behavior_val.csv`
	- `services/advisor-service/artifacts/behavior_test.csv`

### Quy trình xử lý và huấn luyện
1. Chuẩn hóa dữ liệu hành vi theo từng user.
2. Gán nhãn hành vi theo taxonomy: `impulse_buyer`, `researcher`, `loyal_customer`, `price_sensitive`, `window_shopper`.
3. Mã hóa chuỗi sự kiện thành vector đầu vào cho mô hình tuần tự.
4. Huấn luyện 3 mô hình:
	 - RNN: `services/advisor-service/advisor/ml/behavior_rnn.py`
	 - LSTM: `services/advisor-service/advisor/ml/behavior_lstm.py`
	 - biLSTM: `services/advisor-service/advisor/ml/behavior_bilstm.py`
5. Đánh giá bằng các độ đo:
	 - Accuracy
	 - Macro F1
6. Tổng hợp kết quả và chọn `model_best` tự động trong:
	 - `services/advisor-service/artifacts/behavior_model_manifest.json`
	 - `services/advisor-service/advisor/ml/model_selection_report.py`

### Kết quả đánh giá thực nghiệm
Kết quả thu được sau huấn luyện (30 epochs):

| Mô hình | Accuracy | Macro F1 |
|---|---:|---:|
| RNN | 0.3937 | 0.3529 |
| LSTM | 0.3500 | 0.2806 |
| biLSTM | **0.4375** | **0.4087** |

Kết luận chọn mô hình tốt nhất:
- `model_best = biLSTM`
- Lý do chọn:
	- biLSTM có `Macro F1` cao nhất (0.4087), phản ánh khả năng cân bằng trên nhiều lớp hành vi tốt hơn.
	- Accuracy cũng cao nhất trong 3 mô hình.
	- Phù hợp bài toán chuỗi hành vi vì biLSTM khai thác được cả ngữ cảnh thuận và nghịch trong chuỗi sự kiện.

### Visualization
- Biểu đồ so sánh Accuracy/Macro F1 được xuất tại:
	- `services/advisor-service/artifacts/model_comparison_plot.png`
- Biểu đồ đường thể hiện Validation Accuracy theo từng epoch của RNN, LSTM, biLSTM được xuất tại:
	- `services/advisor-service/artifacts/model_validation_accuracy_curve.png`
- Báo cáo chi tiết:
	- `services/advisor-service/artifacts/model_comparison_report.html`
	- `services/advisor-service/artifacts/model_comparison_report.md`

### Đánh giá bằng lời
Trong bài toán phân loại hành vi người dùng, dữ liệu thường có sự chồng lấp giữa các lớp (ví dụ người dùng vừa tìm kiếm nhiều vừa có thể mua hàng). Vì vậy chỉ nhìn Accuracy là chưa đủ, cần dùng thêm Macro F1 để đánh giá công bằng theo từng lớp. Kết quả cho thấy biLSTM vượt trội so với RNN và LSTM, chứng tỏ việc học ngữ cảnh hai chiều giúp mô hình hiểu chuỗi hành vi tốt hơn. Do đó biLSTM được chọn làm mô hình vận hành chính cho hệ thống gợi ý và chat tư vấn.

---

## 2b) Xây dựng Knowledge Base Graph (KB_Graph) với Neo4j

### Mục tiêu
- Tổ chức tri thức sản phẩm và hành vi người dùng thành đồ thị để truy vấn ngữ nghĩa tốt hơn.
- Làm nền cho RAG và chat tư vấn theo ngữ cảnh mua sắm.

### Công nghệ và thành phần
- Neo4j để lưu trữ đồ thị tri thức.
- Tầng xử lý graph:
	- `services/advisor-service/advisor/ml/kb_graph.py`

### Thiết kế KB_Graph
Các node chính:
- `Document`
- `Product`
- `Brand`
- `Category`
- `Customer`
- `Tag`
- `Intent`

Các quan hệ chính:
- `(:Document)-[:ABOUT]->(:Product)`
- `(:Document)-[:BELONGS_TO]->(:Category)`
- `(:Document)-[:HAS_TAG]->(:Tag)`
- `(:Document)-[:HAS_INTENT]->(:Intent)`
- `(:Product)-[:BELONGS_TO]->(:Category)`
- `(:Product)-[:HAS_BRAND]->(:Brand)`
- `(:Product)-[:SIMILAR_TO]->(:Product)`
- `(:Customer)-[:VIEWS]->(:Product)`
- `(:Customer)-[:BUYS]->(:Product)`
- `(:Customer)-[:SEARCHES]->(:Category)`

### Luồng ingest dữ liệu
1. Thu thập dữ liệu tài liệu tri thức và dữ liệu sản phẩm/hành vi.
2. Chuẩn hóa thực thể và quan hệ.
3. Ghi vào Neo4j bằng các hàm build graph:
	 - `build_kb_graph_documents(...)`
	 - `build_kb_graph_entities(...)`
4. Duy trì chỉ mục để truy vấn nhanh cho tầng RAG.

### Giá trị đạt được
- Dữ liệu có cấu trúc ngữ nghĩa rõ ràng hơn so với bảng thuần.
- Truy vấn theo quan hệ (sản phẩm tương tự, danh mục liên quan, ý định người dùng) hiệu quả.
- Làm nền vững chắc cho chatbot tư vấn theo ngữ cảnh mua sắm thực tế.

---

## 2c) Xây dựng RAG và Chat dựa trên KB_Graph

### Mục tiêu
- Tạo chatbot tư vấn mua sắm dựa trên tri thức nội bộ, không trả lời chung chung.
- Kết hợp truy hồi từ KB Graph và vector/doc retrieval để sinh phản hồi sát ngữ cảnh user.

### Kiến trúc RAG
Pipeline tổng quát:
1. User gửi câu hỏi.
2. Hệ thống phân tích intent + ngữ cảnh phiên.
3. Truy hồi tài liệu/tri thức liên quan từ:
	 - Graph retrieval (Neo4j)
	 - Vector/document retrieval
4. Hợp nhất ngữ cảnh truy hồi.
5. Sinh phản hồi chat.
6. Trả kết quả + gợi ý sản phẩm liên quan.

### Thành phần đã triển khai
- API chat:
	- `services/advisor-service/advisor/views.py` (endpoint `chat`)
- KB retrieval:
	- `services/advisor-service/advisor/ml/kb.py`
	- `services/advisor-service/advisor/ml/kb_graph.py`
	- `services/advisor-service/advisor/ml/kb_vector.py`
- Các endpoint hỗ trợ ngữ nghĩa:
	- keyword suggest
	- semantic search

### Kết quả
- Chatbot phản hồi dựa trên dữ liệu tri thức nội bộ.
- Tăng khả năng giải thích gợi ý: có lý do gợi ý theo lịch sử hành vi và quan hệ tri thức.
- Hỗ trợ tốt cho nghiệp vụ tư vấn sản phẩm laptop/điện thoại.

---

## 2d) Tích hợp vào hệ e-commerce

### Yêu cầu tích hợp
- Hiển thị danh sách hàng gợi ý khi khách hàng:
	- click/search
	- thao tác giỏ hàng
- Có giao diện chat riêng cho user (không dùng giao diện chat mặc định kiểu ChatGPT).

### Triển khai giao diện và luồng nghiệp vụ
Các trang đã tích hợp advisor:
- `frontend/store/templates/store/home.html`
- `frontend/store/templates/store/products.html`
- `frontend/store/templates/store/cart.html`
- `frontend/store/templates/store/product_detail.html`

Các điểm tích hợp chính:
1. **Danh sách gợi ý sản phẩm theo hành vi**
	 - Hiển thị khối `advisor_recommendations` trên trang sản phẩm, trang chủ, trang giỏ hàng, trang chi tiết.
	 - Gợi ý thay đổi theo ngữ cảnh thao tác hiện tại của user.

2. **Theo dõi hành vi người dùng (behavior tracking)**
	 - Gửi event về advisor service qua endpoint event tracking.
	 - Dùng làm dữ liệu đầu vào cho mô hình và cho phần tóm tắt hành vi.

3. **Chat widget tùy biến cho e-commerce**
	 - Sử dụng widget riêng (`advisor-widget.js`), có thiết kế phù hợp website bán hàng.
	 - Giao tiếp với backend qua `/advisor/chat`.
	 - Không dùng giao diện chat tổng quát, đảm bảo đúng yêu cầu đề bài.

### Kết quả tích hợp
- Người dùng nhìn thấy sản phẩm gợi ý theo ngữ cảnh search/cart.
- Có thể chat trực tiếp với trợ lý AI để nhận tư vấn mua sắm.
- Hệ thống tạo trải nghiệm mua sắm cá nhân hóa, liền mạch từ hành vi -> gợi ý -> chat.

---

## Tổng kết phần 2 (2a-2d)
- Đã triển khai đủ 3 mô hình RNN, LSTM, biLSTM; đã đánh giá và chọn `model_best = biLSTM` dựa trên Accuracy + Macro F1.
- Đã xây dựng KB_Graph bằng Neo4j từ dữ liệu hệ thống.
- Đã triển khai RAG + Chat dựa trên KB_Graph.
- Đã tích hợp hoàn chỉnh vào hệ e-commerce với cả danh sách gợi ý và giao diện chat riêng cho user.

---

# 4) Lời giải thích + Copy code Câu 2a + ảnh minh họa

## 4.1 Lời giải thích ngắn gọn cho Câu 2a
Nhóm sử dụng dữ liệu hành vi để huấn luyện 3 mô hình học chuỗi gồm RNN, LSTM và biLSTM. Sau khi chuẩn hóa chuỗi sự kiện theo từng user và gán nhãn hành vi, nhóm huấn luyện các mô hình với cùng nguyên tắc đánh giá bằng Accuracy và Macro F1. Kết quả cho thấy biLSTM cho hiệu năng tốt nhất (cao nhất ở cả Accuracy và Macro F1), vì mô hình tận dụng được ngữ cảnh hai chiều của chuỗi sự kiện. Do đó nhóm chọn biLSTM làm `model_best` cho phần suy luận hành vi trong AISERVICE.

## 4.2 Code tiêu biểu Câu 2a (copy từ source)

### Đoạn code 1: Kiến trúc Vanilla RNN
Nguồn: `services/advisor-service/advisor/ml/behavior_rnn.py`

```python
class BehaviorRNNNet(nn.Module):
	"""Vanilla (Elman) RNN classifier for behavior profiles."""

	def __init__(
		self,
		input_size: int = INPUT_SIZE,
		hidden_size: int = HIDDEN_SIZE,
		num_layers: int = NUM_LAYERS,
		num_classes: int = NUM_CLASSES,
		dropout: float = 0.3,
	):
		super().__init__()
		self.rnn = nn.RNN(
			input_size,
			hidden_size,
			num_layers=num_layers,
			batch_first=True,
			dropout=dropout if num_layers > 1 else 0.0,
			nonlinearity="tanh",
		)
		self.classifier = nn.Sequential(
			nn.Dropout(dropout),
			nn.Linear(hidden_size, num_classes),
		)

	def forward(self, x):
		_, hidden = self.rnn(x)
		return self.classifier(hidden[-1])
```

### Đoạn code 2: Kiến trúc biLSTM và ghép ngữ cảnh 2 chiều
Nguồn: `services/advisor-service/advisor/ml/behavior_bilstm.py`

```python
class BehaviorBiLSTMNet(nn.Module):
	def __init__(
		self,
		input_size: int = INPUT_SIZE,
		hidden_size: int = HIDDEN_SIZE,
		num_layers: int = NUM_LAYERS,
		num_classes: int = NUM_CLASSES,
		dropout: float = 0.3,
	):
		super().__init__()
		self.bilstm = nn.LSTM(
			input_size,
			hidden_size,
			num_layers=num_layers,
			batch_first=True,
			dropout=dropout if num_layers > 1 else 0.0,
			bidirectional=True,
		)
		self.classifier = nn.Sequential(
			nn.Dropout(dropout),
			nn.Linear(2 * hidden_size, num_classes),
		)

	def forward(self, x):
		_, (hidden, _) = self.bilstm(x)
		forward_hidden = hidden[-2]
		backward_hidden = hidden[-1]
		combined = torch.cat((forward_hidden, backward_hidden), dim=1)
		return self.classifier(combined)
```

### Đoạn code 3: Chọn mô hình tốt nhất và xuất plot
Nguồn: `services/advisor-service/advisor/ml/model_selection_report.py`

```python
def write_model_selection_artifacts(artifact_dir: Path) -> dict:
	artifact_dir.mkdir(parents=True, exist_ok=True)
	models = collect_model_metrics(artifact_dir)
	manifest = build_production_manifest(models)

	(artifact_dir / PRODUCTION_MODEL_MANIFEST).write_text(
		json.dumps(manifest, indent=2)
	)
	(artifact_dir / MODEL_COMPARISON_MD).write_text(
		generate_markdown_report(models, manifest)
	)
	(artifact_dir / MODEL_COMPARISON_HTML).write_text(
		generate_html_report(models, manifest)
	)
	generate_model_comparison_plot(models, artifact_dir)

	return {
		"best_model": manifest["selected_model"],
		"manifest": manifest,
		"models": models,
		"report_files": {
			"markdown": str(artifact_dir / MODEL_COMPARISON_MD),
			"html": str(artifact_dir / MODEL_COMPARISON_HTML),
			"manifest": str(artifact_dir / PRODUCTION_MODEL_MANIFEST),
			"plot": str(artifact_dir / MODEL_COMPARISON_PLOT),
		},
	}
```

## 4.3 Danh sách ảnh cần chèn cho Câu 2a
1. Ảnh tập dữ liệu đầu vào `data_user500.csv` (20 dòng đầu).
2. Ảnh kết quả metrics của 3 mô hình (RNN, LSTM, biLSTM).
3. Ảnh biểu đồ so sánh mô hình:
   - `services/advisor-service/artifacts/model_comparison_plot.png`
4. Ảnh line graph Accuracy theo epoch:
	- `services/advisor-service/artifacts/model_validation_accuracy_curve.png`
5. Ảnh file manifest thể hiện `model_best = biLSTM`:
   - `services/advisor-service/artifacts/behavior_model_manifest.json`

---

# 5) KB_Graph: code 20 dòng + ảnh graph

## 5.1 Code 20 dòng tiêu biểu của KB_Graph
Nguồn: `services/advisor-service/advisor/ml/kb_graph.py`

```python
def build_kb_graph_documents(driver=None):
	"""Ingest KBDocument rows from SQLite into Neo4j as Document nodes."""
	from advisor.models import KBDocument  # noqa: PLC0415

	driver = driver or get_neo4j_driver()
	if driver is None:
		return {"status": "skipped", "reason": "neo4j_unavailable"}

	documents = list(KBDocument.objects.all().order_by("id"))
	ingested = 0

	with driver.session() as session:
		_create_constraints_and_indexes(session)

		# Category hierarchy
		for cat, parent in CATEGORY_HIERARCHY.items():
			session.run("MERGE (:Category {name: $name})", name=cat)
			if parent:
				session.run(
					"MATCH (child:Category {name: $child}), (parent:Category {name: $parent}) "
					"MERGE (child)-[:IS_SUBCATEGORY_OF]->(parent)",
					child=cat,
					parent=parent,
				)
```

## 5.2 Giải thích ngắn
Đoạn code trên thể hiện bước ingest tài liệu tri thức vào Neo4j và dựng quan hệ phân cấp danh mục. Đây là phần lõi để KB_Graph có cấu trúc chuẩn, từ đó phục vụ truy vấn ngữ nghĩa cho RAG và chat.

## 5.3 Ảnh graph cần chèn
1. Ảnh schema graph (Document, Product, Category, Customer, Intent, Tag).
2. Ảnh kết quả query graph trong Neo4j Browser, ví dụ:
   - `MATCH (n) RETURN n LIMIT 50`
   - `MATCH p=(:Customer)-[:VIEWS|BUYS|SEARCHES*1..2]->(:Product) RETURN p LIMIT 25`
3. Ảnh graph phức tạp có nhiều node/edge để tăng giá trị phần trình bày.

---

# 6) Câu 2c, 2d: tài liệu + ảnh

## 6.1 Câu 2c - RAG và Chat dựa trên KB_Graph

### Tài liệu mô tả
- API chat nhận câu hỏi user, phân tích ngữ cảnh, truy hồi tri thức từ graph + vector, sau đó tạo câu trả lời và gợi ý sản phẩm.
- Thành phần chính:
  - API chat tại `services/advisor-service/advisor/views.py`.
  - Graph retrieval tại `services/advisor-service/advisor/ml/kb_graph.py`.
  - Vector/doc retrieval tại `services/advisor-service/advisor/ml/kb_vector.py` và `services/advisor-service/advisor/ml/kb.py`.

### Code tiêu biểu (chat endpoint)
Nguồn: `services/advisor-service/advisor/views.py`

```python
@api_view(["POST"])
def chat(request):
	request_id = get_request_id()
	log_ctx = LogContext(logger, request_id=request_id, operation="chat")
	start_total = time.perf_counter()

	serializer = ChatRequestSerializer(data=request.data)
	if not serializer.is_valid():
		log_ctx.warning("Chat validation failed", result_code=400)
		metrics.record_error("chat", "validation_error")
		return Response(
			{"error": "Validation failed", "detail": serializer.errors},
			status=status.HTTP_400_BAD_REQUEST,
		)

	payload = serializer.validated_data
	user_id = payload.get("user_id") or request.META.get("HTTP_X_USER_ID", "")
	session_id = payload.get("session_id", "")
	language = payload.get("language", "vi")
```

### Ảnh cần chèn cho 2c
1. Ảnh giao diện chat widget trên trang web.
2. Ảnh response JSON của API `/advisor/chat`.
3. Ảnh semantic search/keyword suggest hoạt động.

## 6.2 Câu 2d - Tích hợp trong hệ e-commerce

### Tài liệu mô tả
- Hệ thống hiển thị danh sách hàng gợi ý khi user search hoặc thao tác giỏ hàng.
- Chat widget tùy biến xuất hiện trên các trang chính của cửa hàng.

### Code tiêu biểu (tích hợp chat widget ở trang cart)
Nguồn: `frontend/store/templates/store/cart.html`

```html
<script src="{% static 'store/js/advisor-widget.js' %}"></script>
<script>
  lucide.createIcons();
  initAdvisorWidget({
	pageName: "cart",
	chatUrl: "/advisor/chat",
	eventUrl: "/advisor/event",
	storageKey: "advisor-chat-history-cart",
	suggestionChips: ["Goi y san pham di kem", "Combo tiet kiem", "Nen mua them gi?"],
  });
</script>
```

### Ảnh cần chèn cho 2d
1. Ảnh khối gợi ý sản phẩm trên trang `home`.
2. Ảnh khối gợi ý sản phẩm trên trang `products`.
3. Ảnh khối gợi ý sản phẩm trên trang `cart`.
4. Ảnh popup/chat panel AI advisor đang hoạt động.

## 6.3 Kết luận mục 6
Phần 2c và 2d đã được triển khai hoàn chỉnh: RAG/Chat sử dụng tri thức từ KB_Graph và đã tích hợp vào luồng mua sắm thực tế, đáp ứng yêu cầu hiển thị gợi ý theo hành vi và cung cấp giao diện chat riêng cho người dùng cuối.
