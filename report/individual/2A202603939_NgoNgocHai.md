# Báo cáo Day 7

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: 2 survey arXiv về Legal NLP — `nlp-legal-survey-2410.21306` (arXiv:2410.21306v3, 29 trang) và `legal-nlp-india-survey-2107.06056` (arXiv:2107.06056v1, 16 trang), giấy phép CC BY 4.0; tổng **45 trang nội dung** (≥30). Dùng lại **386 chunk** Strategy A (fixed-size 500, overlap 50) từ Day 6, ID duy nhất, đủ `id/text/source_id/source/page/metadata`; file `data/day6_chunks.json`.
- Vector store, embedding model, phiên bản và số chiều: PostgreSQL 16 + pgvector **0.8.7** (Docker `127.0.0.1:55433/day6_lab`, metric cosine `<=>`); embedding `qwen/qwen3-embedding-8b` qua OpenRouter, **4096 chiều**; query embedding cùng model/chiều với index; tái sử dụng index Day 6 nên chi phí tạo index mới = **$0**.
- Agent model, cách chạy và phân chia dev/test: agent `openai/gpt-4o-mini` qua OpenRouter (temperature 0, JSON) điều phối tool retrieval thật. Benchmark **31 câu**: dev 21 (19 có đáp án + 2 thiếu bằng chứng `u01`,`u02`), test 10 (8 có đáp án + 2 thiếu bằng chứng `u03`,`u04`); dev/test tách biệt, không trùng. Lệnh: `python starter/run_agent_benchmark.py --split <dev|test> --retriever <dense|hybrid> --max-searches N --top-k K --budget B`.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: câu có đáp án gồm `gold = {source_id, page, evidence}` với evidence nằm trọn trong một chunk đúng nguồn/trang (đã kiểm 27/27 câu bằng `baseline.validate`); câu thiếu evidence có `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Chấm retrieval bằng Hit@1, Evidence Hit@3 (cutoff 3), Context Evidence Rate; chấm agent bằng grounded 0/1/2, citation hợp lệ, abstention. Không đưa gold vào agent/retrieval/query; filter lấy từ câu hỏi, không suy từ gold.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | TF-IDF lexical, top_k=3, filter theo metadata, budget 2500 | Lexical baseline (NFC tokenization) | dev | 13/19 (68.4%) | 17/19 (89.5%) | 17/19 (89.5%) | 1.264 ms/query, $0 |
| Phương pháp 2 | Dense qwen3-embedding-8b + pgvector/cosine, top_k=3, filter, budget 2500 | Nearest-neighbor ngữ nghĩa trên index Day 6 | dev | 14/19 (73.7%) | 16/19 (84.2%) | 16/19 (84.2%) | 2606 ms/query, 19 embedding call; USD không xác thực |
| Phương pháp 3 | Hybrid RRF (dense + TF-IDF, k=60), candidate 10, top_k=3, budget 2500 | Hợp nhất thứ hạng, không cộng score khác thang đo | dev | 13/19 (68.4%) | 17/19 (89.5%) | 17/19 (89.5%) | 3141 ms/query, 19 embedding call |
| Cải thiện 1 | Hybrid RRF, candidate 20, top_k=8, budget 4500 | Lấy sâu hơn để evidence hạng 4–8 vào context, tăng CER; đánh đổi context lớn hơn | dev | 14/19 (73.7%) | 17/19 (89.5%) | **18/19 (94.7%)** | 19 embedding call; mean 4138.5 ký tự (~1035 token ước lượng) |
| Cải thiện 2 | LLM query rewriting + Hybrid RRF, candidate 10, top_k=5, budget 3500 | Viết lại câu hỏi thành từ khóa; **không tăng mà giảm** | dev | 11/19 (57.9%) | 13/19 (68.4%) | 17/19 (89.5%) | +19 LLM call (1241 token); mean 2870 ký tự |
| Cấu hình đã chọn | Hybrid RRF, candidate 20, top_k=8, budget 4500 (chốt trước khi test) | Đánh giá độc lập | test | 7/8 (87.5%) | 7/8 (87.5%) | **8/8 (100%)** | mean 4150 ký tự; 8 embedding call |
| Baseline | TF-IDF lexical, top_k=3, budget 2500 | Mốc so sánh trên cùng test | test | 6/8 (75.0%) | 6/8 (75.0%) | 6/8 (75.0%) | mean 1775 ký tự; $0 |

Toàn bộ báo cáo dùng `n/N` = số câu đạt / số câu có đáp án; thời gian là ms/query; chi phí embedding không ghi USD vì endpoint không trả usage/pricing (TF-IDF $0). Hai cấu hình cải thiện: **I1** (hybrid sâu hơn) tăng CER 17→18 trên dev và giữ Hit@3 17/19, đánh đổi context lớn hơn; **I2** (viết lại câu hỏi) giảm Hit@3 còn 13/19 dù tốn thêm 19 LLM call nên bị loại. Hai lỗi dev: (1) **q19** evidence hạng 4–8 nên top-3 hụt (grade 0), I1 đưa vào context → grade 2, đo lại CER 17→18; (2) **q02** ("16 challenges") câu ngắn khiến từ "challenges" khớp bảng tóm tắt trang 29 thay vì câu trang 1, I1 vẫn hụt, chỉ I2 cứu riêng câu này nhưng làm hỏng câu khác. Chốt **I1** trước khi xem test theo tiêu chí CER → Hit@3 → chi phí; trên test I1 đạt 7/8 · 7/8 · 8/8 so với baseline TF-IDF 6/8 · 6/8 · 6/8.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: một tool `Retriever.search` (dense hoặc hybrid RRF trên pgvector Day 6, hỗ trợ filter). `run_agent` tối đa `max_searches=2` trên test; dừng khi có answer kèm citation hợp lệ, hoặc hết lượt / context rỗng / citation sai → abstain. Context chọn bằng `pack_context` (khử trùng lặp theo id, ưu tiên chunk xuất hiện trước, giới hạn budget). Lỗi provider/retriever ghi `status="error"` riêng, không thay bằng kết quả giả.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| Baseline dense / test | 10/10 | 8×1, 2×2 | 3/1/4 — TB 1.125 | 5/6 | 5/5 | 2/2 | 3/8 |
| Cấu hình chọn hybrid / test | 10/10 | 8×1, 2×2 | 2/1/5 — TB 1.375 | 7/7 | 6/6 | 2/2 | 2/8 |

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q05 | Có đáp án | 1 search → `p13-c0` | "Federal Supreme Court of Switzerland (FSCS)" `[A:nlp-legal-survey-2410.21306-p13-c0-422e6e8f]` | 2 — citation chứa đúng evidence |
| q25 | Có đáp án | 1 search → `p13-c1`,`p13-c2` | Mô tả case-similarity (keyword/text search) `[p13-c1][p13-c2]` | 1 — thiếu ý "manual/act-based", dù citation hợp lệ |
| q27 | Có đáp án | 1 search, không đủ evidence | "Không đủ bằng chứng để trả lời." | 0 — từ chối nhầm (LEXTREME) |
| u03 | Thiếu evidence | 2 search, không có evidence | "Không đủ bằng chứng để trả lời." | abstain đúng |

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí: trace và nhãn ở `starter/results/agent-test/` (agent_traces.json, reviews.json, summary.json) và `starter/results/agent-test-baseline/`; chạy `python starter/agent_metrics.py --cases data/cases.json --traces <traces.json> --reviews <reviews.json> --split test --output <summary.json>`; thời gian ~4–8 s/câu; chi phí LLM/embedding thấp, không ghi USD vì thiếu pricing từ endpoint.
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn: chuyển baseline dense sang hybrid giúp grounded TB 1.125→1.375, citation 5/6→7/7, từ chối nhầm 3/8→2/8. Ví dụ lỗi: q25 (baseline) citation đầu là bảng relations nên không hỗ trợ (support `[false, true]`); q02 dev trả "five" thay vì "16" do chunk bảng bị cắt ở biên 500 ký tự. Giới hạn: test nhỏ (8 câu có đáp án), nhãn do tác giả chấm nên có thiên lệch, chunk fixed-size có thể cắt bảng.

## Thử thách nâng cao (nếu thực hiện)

Không thực hiện.