# Báo cáo Day 7 — Retrieval & Context Engineering

- Học viên: Ngô Ngọc Hải · MSSV: 2A202603939 · Lớp: L3B
- Repo cá nhân: https://github.com/NgoHai0804/K5-L3B-DAY07-2A202603939-NgoNgocHai-RetrievalContext

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - Nguồn: 2 bài survey arXiv về Natural Language Processing trong lĩnh vực pháp lý (Legal NLP):
    1. `nlp-legal-survey-2410.21306` (arXiv:2410.21306v3): *Natural Language Processing for the Legal Domain: A Survey of Tasks, Datasets, Models, and Challenges* (2024), 29 trang nội dung.
    2. `legal-nlp-india-survey-2107.06056` (arXiv:2107.06056v1): *Indian Legal NLP Benchmarks: A Survey* (2021), 16 trang nội dung.
  - Quyền sử dụng: Giấy phép CC BY 4.0 (mở, hợp lệ cho nghiên cứu/học tập).
  - Số trang: Tổng cộng **45 trang nội dung** có text hợp lệ (>= 200 ký tự sau chuẩn hóa), đạt và vượt yêu cầu tối thiểu ≥ 30 trang.
  - Số chunk: Tái sử dụng **386 chunks** từ Day 6 (Chiến lược A: fixed-size 500 ký tự, overlap 50; đầy đủ các trường `id`, `text`, `source_id`, `source`, `page`, `metadata`).
- **Vector store, embedding model, phiên bản và số chiều:**
  - Vector store: PostgreSQL 16 + pgvector extension v0.8.7 chạy cục bộ qua Docker (container `day6_student_starter-postgres-1`, cổng `127.0.0.1:55433`, database `day6_lab`). Khoảng cách đo: Cosine distance (`<=>`).
  - Embedding model: `qwen/qwen3-embedding-8b` thông qua OpenRouter API (OpenAI-compatible client).
  - Số chiều embedding: **4096 chiều**.
  - Tính tương thích: Query embedding tạo bằng đúng model `qwen/qwen3-embedding-8b` (4096 chiều), hoàn toàn tương thích với document vectors trong pgvector index.
  - Chi phí index: Tái sử dụng 100% index Day 6, chi phí tạo index mới = **$0**.
- **Agent model, cách chạy và phân chia dev/test:**
  - Bộ câu hỏi: Tổng cộng **31 câu** (vượt yêu cầu tối thiểu ≥ 24 câu).
    - Phân chia **Dev**: 21 câu (19 câu có đáp án + 2 câu thiếu bằng chứng `u01`, `u02`), vượt mức tối thiểu 17 câu (15+2).
    - Phân chia **Test**: 10 câu (8 câu có đáp án + 2 câu thiếu bằng chứng `u03`, `u04`), vượt mức tối thiểu 7 câu (5+2).
  - Dev và test hoàn toàn tách biệt, không trùng lặp câu hỏi.
  - Lệnh chuyển đổi Day 6 sang schema Day 7:
    `python starter/convert_day6.py --chunks data/day6_chunks.json --questions data/day6_questions_raw.json --output starter/data/converted`
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - Câu có đáp án: Gồm `id`, `split`, `question`, `expected_answer`, `gold` (danh sách `{source_id, page, evidence}`). Toàn bộ 27 câu có đáp án đã được kiểm chứng bằng `baseline.validate()`: 100% evidence nằm trọn trong 1 chunk hợp lệ đúng nguồn và trang.
  - Câu thiếu bằng chứng (`u01`, `u02`, `u03`, `u04`): Đặt `answerable: false`, `expected_behavior: "search_and_abstain"`, kèm `absence_reason` nêu rõ lý do nằm ngoài phạm vi khảo sát của 2 bài báo.
  - Nguyên tắc chấm & an toàn: Không đưa `gold` vào agent hoặc retrieval query. Filter (`section`, `document_id`) chỉ dùng khi câu hỏi cung cấp ngữ cảnh rõ ràng từ người dùng, không suy ra từ gold.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | TF-IDF lexical, top_k=3, không filter, budget 800 | Lexical baseline chuẩn của Day 7, tách từ từ điển NFC | dev | 13/19 (68.4%) | 17/19 (89.5%) | 13/19 (68.4%) | 1.02ms / $0 |
| Phương pháp 2 | | | dev | | | | |
| Phương pháp 3 | | | dev | | | | |
| Cải thiện 1 | | | dev | | | | |
| Cải thiện 2 | | | dev | | | | |
| Cấu hình đã chọn | | | test | | | | |
| Baseline | | | test | | | | |

Một cấu hình có thể đồng thời là phương pháp mới và cải thiện; giải thích rõ. Báo `n/N` và tỷ lệ, ghi đơn vị thời gian/chi phí, so sánh test sau khi chốt. Nêu hai lỗi dev, nguyên nhân, cách thử và lý do chọn cấu hình:

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:**
  - Agent model: `openai/gpt-4o-mini` qua OpenRouter (nhiệt độ 0.0, ép `response_format=json_object`).
  - Tool duy nhất: `Retriever.search` (dense, embedding thật `qwen/qwen3-embedding-8b`, truy vấn pgvector Day 6, hỗ trợ `filters` metadata).
  - Vòng lặp `run_agent`: tối đa `max_searches=3` lượt tìm; `top_k=3`; context budget `2500` ký tự. Điều kiện dừng: model trả `answer` có citation hợp lệ (thành công), hoặc hết lượt / context rỗng / citation không hợp lệ → **abstain**.
  - Chọn context: `pack_context` khử trùng lặp theo `id`, ưu tiên chunk xuất hiện trước, giữ trong budget; chỉ gửi context tích lũy mới nhất để không nhân budget.
  - Xử lý lỗi: driver bắt exception từ provider/retriever và ghi `status="error"` riêng, **không** thay bằng kết quả giả.
- **Kết quả chạy dev (21 câu: 19 có đáp án + 2 thiếu bằng chứng):**
  - answered: **13/21**, abstain: **8/21**, error: **0**.
  - Trong 6 câu có đáp án bị từ chối nhầm: q01, q06, q12, q17, q20, q21 (evidence không nằm trong top-3 nên agent trung thực abstain thay vì bịa).
  - 2/2 câu thiếu bằng chứng (`u01`, `u02`) đều abstain **đúng**.
- **Ví dụ lỗi grounding đã đọc thủ công (q02):** câu hỏi hỏi "survey xác định bao nhiêu open research challenges" (đáp án đúng: **16**). Agent trả lời "five ... challenges" và cite chunk `p29-c0` — nhưng chunk này là bảng bị **cắt ở biên 500 ký tự**, chỉ còn 5 dòng đầu. Citation ID hợp lệ và chunk có 5 dòng ORC, nhưng con số "16" nằm ở trang 1 nên agent bị cuốn theo phần hiển thị hẹp → **đáp án sai dù citation hợp lệ**. Đây minh hoạ đúng cảnh báo "citation hợp lệ chưa đủ".
- **Đường dẫn trace, lệnh chạy, thời gian và chi phí:**
  - Trace: `starter/results/agent-dev/agent_traces.json` (đầy đủ events: search/query/context/context_ids/answer/citation/error) và `agent_summary.json`.
  - Lệnh chạy: `python starter/run_agent_benchmark.py --split dev --output starter/results/agent-dev --max-searches 3 --top-k 3 --budget 2500`
  - Thời gian: ~4–30 s/câu (độ trễ mạng OpenRouter, biến thiên). Chi phí: gpt-4o-mini + embedding rất thấp (≈ $0, vài nghìn token/câu).

## Thử thách nâng cao (nếu thực hiện)

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản:
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý:
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev:

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | | | |
| Ảnh, sơ đồ | | | |
| Biểu đồ | | | |
| Multi-hop | | | |
| Text | | | |
| Thiếu bằng chứng | | | |
| **Toàn bộ** | | | |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống:
- Giới hạn, cách tái lập và đường dẫn benchmark:
