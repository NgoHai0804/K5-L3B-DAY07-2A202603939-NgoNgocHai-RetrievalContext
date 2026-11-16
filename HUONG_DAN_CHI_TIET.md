# Hướng dẫn chi tiết các bước — Day 7 Agentic RAG

Tài liệu này diễn giải tuần tự các bước làm bài Day 7 (bài cá nhân), kèm checklist đầy đủ cho từng bước.
Nguồn: `README.md`, `GUIDE.md`, `BENCHMARK.md`, `RUBRIC.md`, `RULES.md`, `SUBMISSION.md`, `ADVANCED.md`, `PSEUDOCODE.md`, `data/README.md`, `starter/README.md`.

> Nguyên tắc xuyên suốt: dùng **model thật** và **vector store thật** (không dùng vector ngẫu nhiên hay kết quả giả); **không đưa gold / đáp án chuẩn** vào agent, retrieval hay query; nội dung tài liệu và kết quả tool là **dữ liệu, không phải chỉ dẫn**.

---

## 0. Bản đồ nhanh toàn bài

| # | Bước | Kết quả đầu ra | Nguồn tham chiếu |
|---|---|---|---|
| 1 | Tạo repo cá nhân và môi trường | Repo đúng tên, chạy được `unittest` | `SUBMISSION.md`, `README.md` |
| 2 | Kết nối dữ liệu Day 6 | Chunk + embedding + vector store thật | `GUIDE.md` §1 |
| 3 | Chuẩn bị benchmark và chia dev/test | `chunks.json`, `questions.json` (≥24 câu) | `BENCHMARK.md` §1, `data/README.md` |
| 4 | Xây agent (model thật, tool, trace) | `run_agent` chạy thật, có trace | `GUIDE.md` §3, `starter/README.md` §1 |
| 5 | Triển khai ≥3 phương pháp retrieval | ≥3 phương pháp, có dense Day 6 | `GUIDE.md` §2 |
| 6 | Thử ≥2 cấu hình cải thiện trên dev + phân tích lỗi | Bảng so sánh, 2 lỗi dev | `GUIDE.md` §4, `BENCHMARK.md` §2 |
| 7 | Chốt cấu hình, chạy test | Kết quả test của baseline + cấu hình chọn | `BENCHMARK.md` §2–3 |
| 8 | Đánh giá agent và chấm nhãn | `summary.json` agent metrics | `BENCHMARK.md` §3, `starter/README.md` §4 |
| 9 | Báo cáo và nộp bài | Báo cáo cá nhân + checklist nộp | `SUBMISSION.md`, `REPORT_TEMPLATE.md` |
| 10 | (Tùy chọn) Thử thách nâng cao 100 trang | Benchmark riêng, đạt ≥90% test | `ADVANCED.md` |

Điểm cơ bản tối đa 85; thử thách nâng cao +15 (tối đa toàn bài 100). Xem `RUBRIC.md`.

---

## Bước 1 — Tạo repo cá nhân và chuẩn bị môi trường

**Mục tiêu:** Có repo đúng quy ước và môi trường chạy được test mock.

**Việc cần làm:**

1. Đặt tên repo theo lớp: `K5-L3B-DAY07-MSSV-HoTen-RetrievalContext` (không dấu, không khoảng trắng).
2. Fork hoặc clone repo đề bài, đổi remote `origin` sang repo cá nhân, push `main`.
3. Đảm bảo Python 3.11 trở lên.
4. Chạy test mock để chắc code khung chạy được.

**Lệnh chạy:**

```bash
git clone https://github.com/VinUni-AI20k/K5-L3-Day07-Retrieval-Context-Engineering.git <TEN_REPO>
cd <TEN_REPO>
git remote rename origin upstream
git remote add origin <URL_REPO_CA_NHAN>
git push -u origin main

python3 -m unittest discover -s tests -v
```

**Checklist:**

- [x] Repo đúng tên quy ước, không chứa secret/`.env`/API key.
- [x] Đã đổi remote: `upstream` = repo đề bài, `origin` = repo cá nhân.
- [x] Python ≥ 3.11; đã cài các thư viện cần (embedding, vector store, model client).
- [x] `python3 -m unittest discover -s tests -v` chạy qua (test mock chỉ kiểm tra code).
- [x] Đã đọc `GUIDE.md`, `RUBRIC.md`, `RULES.md`, `BENCHMARK.md`.

---

## Bước 2 — Kết nối dữ liệu, embedding và vector store Day 6

**Mục tiêu:** Dùng lại chunk/ID/nguồn/embedding/vector store Day 6, ghi rõ cấu hình.

**Việc cần làm:**

1. Tái sử dụng chunk, ID, nguồn, vector store và embedding model của Day 6.
2. Ghi phiên bản model, số chiều embedding (chiều), cách kết nối.
3. Đảm bảo **query embedding tương thích** với index. Nếu đổi embedding model, tạo index mới và ghi chi phí.
4. Nếu chưa xong Day 6: chuẩn bị dữ liệu, embedding thật và vector store trước (không dùng vector ngẫu nhiên để đánh giá).
5. Chọn tập tài liệu đa dạng; nếu tự chuẩn bị, dùng ≥30 trang nội dung hợp lệ.

**Checklist:**

- [x] Có chunk Day 6 với đủ trường: `id`, `text`, `source_id`, `source`, `page`, `metadata` (ID duy nhất).
- [x] Có vector store truy vấn được bằng embedding thật.
- [x] Đã ghi: embedding model, phiên bản, số chiều, cách kết nối.
- [x] Query embedding và index dùng **cùng** model/chiều.
- [x] Đã ghi chi phí nếu phải tạo index mới.
- [x] Có ≥30 trang nội dung hợp lệ (nếu tự chuẩn bị từ đầu).

---

## Bước 3 — Chuẩn bị benchmark và chia dev/test

**Mục tiêu:** Bộ câu hỏi tối thiểu 24 câu, có nhãn evidence, chia rõ dev/test.

**Yêu cầu số lượng (phần cơ bản):**

| Loại câu | Dev | Test |
|---|---:|---:|
| Có đáp án trong tài liệu | Ít nhất 15 | Ít nhất 5 |
| Không đủ bằng chứng | Ít nhất 2 | Ít nhất 2 |
| **Tối thiểu** | **17** | **7** |

> Tổng tối thiểu **24 câu** (20 câu có evidence + 4 câu thiếu evidence).

**Việc cần làm:**

1. Xuất chunk và câu hỏi thành hai JSON array theo `data/README.md`.
2. Với câu có đáp án, ghi `id`, `split`, `question`, `expected_answer`, `gold` = danh sách `{source_id, page, evidence}`; evidence phải **nằm trọn trong một chunk** đúng nguồn và trang.
3. Với câu multi-hop, mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm.
4. Với câu thiếu evidence: `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`; ưu tiên câu gần chủ đề và ghi cách kiểm tra trong bộ tài liệu.
5. Chuyển định dạng Day 6 nếu cần bằng `starter/convert_day6.py`, rồi đối chiếu lại nguồn/trang/evidence.

**Lệnh chạy (khi chuyển từ Day 6):**

```bash
python3 starter/convert_day6.py --chunks <day6_chunks.json> --questions <day6_questions.json> --output starter/data/converted
python3 starter/baseline.py --chunks starter/data/converted/chunks.json --questions starter/data/converted/questions.json --split dev --output starter/results/dev-tfidf
```

**Checklist:**

- [x] Benchmark ≥24 câu: ≥20 câu có evidence, ≥4 câu thiếu evidence.
- [x] Dev: ≥15 câu có đáp án, ≥2 câu thiếu evidence. Test: ≥5 câu có đáp án, ≥2 câu thiếu evidence.
- [x] Mỗi câu có đáp án ghi đủ ID, câu hỏi, đáp án, `source_id`, `page`, `evidence`.
- [x] Câu thiếu evidence có `answerable: false` và lý do thiếu.
- [x] Câu dev và test **không trùng** hoặc chỉ đổi cách diễn đạt.
- [x] Đã kiểm tra evidence nằm trọn trong chunk đúng nguồn/trang.
- [x] **Không** đưa `gold`/đáp án vào agent, retrieval hay query.
- [x] Đã ghi rõ cách chọn filter (từ người dùng hoặc suy luận từ query), không suy từ gold.

---

## Bước 4 — Xây agent (model thật, tool, trace)

**Mục tiêu:** Agent dùng model thật, gọi được ≥1 tool truy xuất, có trace đầy đủ.

**Việc cần làm:**

1. Trong `starter/agentic.py`, hiện thực:
   - `Controller.decide`: gọi **model thật**, trả `{action: "search", query: "..."}` hoặc `{action: "answer", answer: "... [chunk-id]", citations: ["chunk-id"]}`.
   - `Retriever.search`: tạo query embedding tương thích Day 6, truy vấn vector store thật, trả chunk kèm `score`.
2. Viết chương trình nối hai phần bằng `run_agent`, hoặc thay bằng kiến trúc nhiều tool.
3. Tự chọn số lượt gọi (`max_searches`), `top_k`, `budget`, điều kiện dừng; ghi lý do và đo tác động (chất lượng, thời gian, chi phí).
4. Cách chọn context: deduplication, chọn theo độ liên quan, giữ đoạn lân cận, nén/trích đoạn. Giữ đủ nguồn để kiểm chứng.
5. Lưu **từng tool call**: tham số, query, kết quả, context cuối, câu trả lời, citation, lỗi.
6. Agent phải trả lời có citation hoặc nói **không đủ bằng chứng** (abstain). Báo lỗi kết nối thật, không thay bằng kết quả giả.

> Lưu ý kỹ thuật: khung agent ưu tiên giữ chunk từ lần search trước; nếu chunk đầu chiếm gần hết budget, lần search sau có thể không thêm được evidence — kiểm tra trace và thử cách chọn context phù hợp trên dev.

**Checklist:**

- [x] `Controller.decide` gọi model thật (không mock khi chạy benchmark).
- [x] `Retriever.search` truy vấn vector store Day 6 thật, trả tối đa `top_k` chunk ID **duy nhất**.
- [x] Agent dùng ≥1 tool truy xuất; hỗ trợ nhiều tool/nhiều lượt nếu cần.
- [x] Có điều kiện dừng và giới hạn vòng lặp (ghi rõ lý do).
- [x] Đã bàn giao được chương trình nối `run_agent` (hoặc kiến trúc nhiều tool tương đương).
- [x] Trace lưu đủ: tool call, tham số, query, kết quả, context cuối, câu trả lời, citation, lỗi.
- [x] Agent trả lời có `[chunk-id]` hoặc abstain khi thiếu bằng chứng.
- [x] Đã đọc thủ công xác nhận citation **thực sự hỗ trợ** câu trả lời (không chỉ kiểm tra ID hợp lệ).
- [x] Lỗi kết nối được báo riêng, không bị thay bằng kết quả giả.

---

## Bước 5 — Triển khai và benchmark ≥3 phương pháp retrieval

**Mục tiêu:** ≥3 phương pháp khác nhau, **bắt buộc có dense retrieval** trên vector store Day 6.

**Việc cần làm:** Chọn tối thiểu 3 phương pháp (đổi top-k đơn thuần **không** tính là phương pháp mới):

| Phương pháp | Ý tưởng |
|---|---|
| Dense retrieval (**bắt buộc**) | Embedding query, tìm vector gần nhất; thử top-k và metadata filter |
| Lexical retrieval | BM25, full-text hoặc TF-IDF; chú ý tách từ tiếng Việt |
| Hybrid retrieval | Dense + lexical bằng RRF hoặc score fusion có chuẩn hóa |
| Retrieval + rerank | Lấy nhiều candidate rồi rerank; so sánh trước/sau |
| Query transformation | Viết lại, mở rộng, tách câu hỏi; so sánh với query gốc |
| Multi-stage / multi-hop | Tìm theo nhiều bước, dùng kết quả trước để tìm tiếp |

> Một pipeline hybrid hoặc có rerank được tính là một phương pháp nếu khác rõ về cách tìm/xếp hạng. Chỉ cộng score khi đã chuẩn hóa/hợp nhất hợp lý.

**Việc cần làm chung:**

1. Chạy mỗi phương pháp trên **cùng corpus, phiên bản index, câu hỏi và nhãn dev**.
2. Kết quả mỗi query có: ID, nội dung, score hoặc rank, nguồn, trang, metadata.
3. Báo **query gốc**; với query viết lại/multi-hop, báo thêm kết quả pipeline và trace từng bước.
4. Báo **Hit@1** và **Evidence Hit@3** cùng định nghĩa hit và cutoff; nếu top-k khác 3 vẫn xuất top-3 để so sánh.

**Checklist:**

- [x] Có **≥3 phương pháp** thực sự khác nhau về cách tìm/xếp hạng.
- [x] Trong đó có **dense retrieval** dùng vector store Day 6.
- [x] Mỗi phương pháp chạy trên cùng corpus / index / câu hỏi / nhãn dev.
- [x] Kết quả có ID, nội dung, score/rank, nguồn, trang, metadata.
- [x] Đã báo Hit@1 và Evidence Hit@3 cùng định nghĩa, cùng cutoff.
- [x] Đã ghi filter, cách tạo query cho từng phương pháp.
- [x] Nếu dùng query viết lại / multi-hop: có trace từng bước.
- [x] Đã ghi thời gian và chi phí theo từng cấu hình.

---

## Bước 6 — Thử ≥2 cấu hình cải thiện trên dev + phân tích lỗi

**Mục tiêu:** Ít nhất 2 cấu hình nhằm cải thiện baseline, có giả thuyết và kết quả riêng.

**Việc cần làm:**

1. Đặt **ít nhất 2 giả thuyết cải thiện** (ví dụ: thay top-k, thêm rerank, đổi context budget, thử nhiều lượt tìm).
2. Với mỗi cấu hình, ghi giả thuyết, kết quả riêng, và chấp nhận cả trường hợp **không tăng điểm** (không bịa).
3. Đọc **ít nhất 2 lỗi dev**, tìm nguyên nhân, đo lại sau thay đổi.
4. Báo **Context Evidence Rate**: số câu có đủ evidence trong context cuối / số câu có đáp án. Ghi context budget, đơn vị, cách chọn context, số candidate và token/chi phí.
5. Chấm context dev theo thang: **0** = không có evidence; **1** = có nhưng thiếu điều kiện/nguồn; **2** = đủ evidence và nguồn.

**Checklist:**

- [x] Có ≥2 cấu hình cải thiện, mỗi cấu hình có giả thuyết riêng.
- [x] Đã đo và ghi kết quả của **tất cả** thử nghiệm, kể cả không cải thiện.
- [x] Đã đọc và phân tích ≥2 lỗi dev (nguyên nhân + đo lại sau thay đổi).
- [x] Báo Context Evidence Rate (`n/N` và tỷ lệ) cho các cấu hình.
- [x] Ghi context budget, đơn vị đo, cách chọn context, số candidate, token/chi phí.
- [x] Đã chấm context 0/1/2 và ghi lý do, trace, số câu mỗi mức.
- [x] Tiêu chí chọn cấu hình đã được **công bố trước** khi chạy test.

---

## Bước 7 — Chốt cấu hình và chạy test

**Mục tiêu:** Đánh giá độc lập trên test sau khi đã chốt cấu hình.

**Việc cần làm:**

1. Chốt cấu hình dựa trên tiêu chí công bố trước: chất lượng retrieval, context, câu trả lời, chi phí/thời gian.
2. Chạy **baseline và cấu hình đã chọn** trên cùng test.
3. Nếu test đã dùng để chỉnh, phải tạo test mới mới đủ điều kiện đánh giá độc lập (ghi rõ).

**Lệnh chạy (ví dụ):**

```bash
python3 starter/baseline.py --chunks data/example_chunks.json --questions data/example_questions.json --split test --output starter/results/example-test
```

**Checklist:**

- [ ] Đã chốt cấu hình **trước** khi xem test.
- [ ] Đã chạy baseline và cấu hình chọn trên cùng test.
- [ ] Đã báo `n/N` và tỷ lệ, thời gian, chi phí theo từng cấu hình.
- [ ] Nếu test từng bị dùng để chỉnh: đã tạo test mới (ghi rõ).
- [ ] Không dùng kết quả mock để báo chất lượng.

---

## Bước 8 — Đánh giá agent và chấm nhãn

**Mục tiêu:** Đánh giá tool use, grounded answer, citation, abstention; tổng hợp bằng script.

**Việc cần làm:**

1. Chạy agent thật trên dev cho các cấu hình cần so sánh; sau khi chốt, chạy baseline và cấu hình chọn trên cùng test.
2. Đọc **ít nhất 5 câu test có đáp án và 2 câu thiếu evidence**.
3. Chuẩn bị 3 JSON array cho `starter/agent_metrics.py`:
   - `cases.json`: mỗi câu có `id`, `split`, `answerable`.
   - `traces.json`: mỗi câu có `query_id`, `status` (`answered`/`abstain`/`error`), `events`, `citations`.
   - `reviews.json`: mỗi nhãn có `query_id`, `citation_support` (list đúng/sai theo từng citation); câu có đáp án cần `answer_grade` 0–2; câu thiếu evidence cần `abstention_correct`.
4. Chấm theo bảng của `BENCHMARK.md` §3: Tool use, Grounded answer 0/1/2, Citation hợp lệ, Abstention.

**Lệnh chạy:**

```bash
python3 starter/agent_metrics.py --cases <cases.json> --traces <traces.json> --reviews <reviews.json> --split test --output starter/results/agent-test/summary.json
```

**Định nghĩa chấm:**

| Nội dung | Cách chấm |
|---|---|
| Tool use | Số câu gọi retrieval tool / số câu chạy thành công; báo phân bố số lượt gọi và xử lý lỗi |
| Grounded answer | Câu có đáp án: 0 = sai/thiếu evidence; 1 = đúng một phần; 2 = đúng và đủ. Từ chối câu có đáp án chấm **0** |
| Citation hợp lệ | Citation có trong context **và** hỗ trợ câu trả lời / tổng citation; nếu không có báo `0/0 (không áp dụng)` |
| Abstention | Số câu thiếu evidence được từ chối / tổng câu thiếu evidence; báo thêm từ chối nhầm |

**Checklist:**

- [ ] Đã chạy agent thật, lưu model, tool call, tham số, kết quả, context, câu trả lời, citation, số lượt gọi, thời gian, chi phí, lỗi.
- [ ] Đã đọc ≥5 câu test có đáp án và ≥2 câu thiếu evidence.
- [ ] `cases.json`, `traces.json`, `reviews.json` đúng schema (ID duy nhất, không trùng).
- [ ] Đã đọc **từng citation** xác nhận nguồn hỗ trợ (không chỉ ID hợp lệ).
- [ ] Câu có đáp án bị từ chối đã chấm 0.
- [ ] Đã báo qua `agent_metrics.py` và lưu `summary.json`.
- [ ] Lỗi kết nối được báo riêng, không tính vào chất lượng.

---

## Bước 9 — Báo cáo và nộp bài

**Mục tiêu:** Sao chép mẫu báo cáo, điền đầy đủ, đảm bảo checklist nộp.

**Việc cần làm:**

1. Sao chép `report/individual/MSSV_HoTen.md`, đổi tên theo `MSSV_HoTen` (ví dụ `20241234_NguyenVanAn.md`).
2. Điền đầy đủ theo `REPORT_TEMPLATE.md`: dữ liệu/benchmark, retrieval và thử nghiệm, agent và đánh giá.
3. Trình bày ≥1 câu trả lời có bằng chứng, ≥1 câu thiếu bằng chứng, ≥1 lỗi; kèm bảng so sánh, trace, lý do chọn cấu hình.

**Checklist nộp bài (từ `SUBMISSION.md`):**

- [ ] Code agent, ≥3 phương pháp retrieval (gồm dense), test và hướng dẫn chạy.
- [ ] Embedding model, vector store, cách kết nối và dữ liệu được phép chia sẻ (hoặc cách cấp quyền/tái tạo).
- [ ] Benchmark ≥20 câu có evidence và ≥4 câu thiếu evidence, đã chia dev/test.
- [ ] Kết quả từng query và tool call; context, câu trả lời, citation, lỗi, thời gian, chi phí.
- [ ] ≥2 cấu hình cải thiện; bảng benchmark, nhãn, phân tích lỗi và lý do chọn.
- [ ] Báo cáo cá nhân đã điền (đúng tên `MSSV_HoTen.md`).
- [ ] Người chấm xem được repo; **không** nộp dữ liệu mật/`.env`/API key/token.

**Checklist báo cáo:**

- [ ] Mục "Dữ liệu và benchmark" đầy đủ: nguồn, quyền, số trang/chunk, vector store, embedding model/phiên bản/chiều, agent model, cách chạy, chia dev/test, tiêu chí chấm.
- [ ] Bảng "Retrieval và thử nghiệm" điền đủ cấu hình, phương pháp/top-k/filter/rerank/budget, giả thuyết, split, Hit@1, Evidence Hit@3, Context Evidence Rate, thời gian/chi phí.
- [ ] Nêu 2 lỗi dev, nguyên nhân, cách thử, lý do chọn cấu hình.
- [ ] Mục "Agent và đánh giá": tool, số lượt gọi, điều kiện dừng, chọn context, xử lý lỗi; bảng grounded answer, citation, abstention.
- [ ] Ghi đường dẫn trace/nhãn, lệnh chạy, thời gian, chi phí, giới hạn.

---

## Bước 10 (Tùy chọn) — Thử thách nâng cao +15 điểm

**Mục tiêu:** Index 1 tài liệu thực tế ≥100 trang (có bảng, ảnh, biểu đồ), đạt ≥90% benchmark test.

**Việc cần làm:**

1. Chọn 1 tài liệu ≥100 trang; ghi nguồn, phiên bản, số trang, quyền sử dụng.
2. Index **toàn bộ** nội dung hữu ích (không chỉ trang trong benchmark); giữ liên kết về trang gốc; với bảng/ảnh/biểu đồ lưu vùng trang/crop để kiểm chứng.
3. Thiết kế pipeline xử lý text + trực quan (OCR, phân tích layout, trích bảng, mô tả ảnh, vision/multimodal embedding...). Kiểm tra nội dung trích xuất với bản gốc.
4. Tạo benchmark riêng, chia dev/test trước khi thử: test ≥30 câu (≥24 có đáp án, ≥6 thiếu evidence); dev ≥15 câu có đáp án, ≥3 thiếu evidence.
5. Chạy pipeline đã chốt trên toàn bộ test, chấm đạt/không đạt từng câu; đạt **≥90%** (không làm tròn; ví dụ 30 câu cần ≥27/30).

**Phân bổ nhóm câu test có đáp án (tối thiểu):**

| Nhóm | Tối thiểu |
|---|---:|
| Bảng | 6 |
| Ảnh, sơ đồ | 5 |
| Biểu đồ | 5 |
| Multi-hop | 4 |
| Text | 4 |

**Checklist:**

- [ ] Tài liệu ≥100 trang, có quyền sử dụng, người chấm truy cập/tái tạo được.
- [ ] Đã index toàn bộ nội dung hữu ích; ghi rõ phần không xử lý được và ảnh hưởng.
- [ ] Bảng/ảnh/biểu đồ có vùng trang/crop đủ để kiểm chứng.
- [ ] Benchmark test ≥30 câu đúng phân bổ nhóm; dev ≥15 + ≥3.
- [ ] Đã chốt pipeline trên dev trước khi chạy test.
- [ ] Đạt ≥90% test; báo `n/N` toàn bộ và theo nhóm, kèm lỗi/thời gian/chi phí.
- [ ] Đã chấm và ghi nhãn từng câu test, đối chiếu evidence bản gốc.
- [ ] Nộp đủ bằng chứng tái lập.

---

## Phụ lục A — Định dạng dữ liệu (`data/README.md`)

**Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID duy nhất; giữ phiên bản/ngày nếu có.

**Câu có đáp án:** `id`, `split` (`dev`/`test`), `question`, `expected_answer`, `gold` = list `{source_id, page, evidence}`; mỗi evidence nằm trọn trong một chunk đúng nguồn/trang; các phần tử `gold` là evidence thay thế. Có thể thêm `filter` do người dùng cung cấp.

**Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`.

---

## Phụ lục B — Metric và ngưỡng tham chiếu

- **Hit@1** = số câu có evidence hợp lệ trong top-1 / số câu có đáp án.
- **Evidence Hit@3** = số câu có evidence hợp lệ trong top-3 / số câu có đáp án.
- **Context Evidence Rate** = số câu đủ evidence trong context cuối / số câu có đáp án (có thể ≥ Hit@3 nếu context từ nhiều lượt).
- **Grounded answer** = trung bình 0/1/2 trên câu có đáp án.
- Ngưỡng nâng cao: test **≥90%** câu đạt (không làm tròn).
- Mục tiêu compaction trong slide (nếu tham chiếu): token reduction ≥40%, pass-rate drop ≤2 pts — đây là bối cảnh buổi học, không phải yêu cầu chấm chính của lab.

---

## Phụ lục C — Lỗi thường gặp cần tránh

1. Dùng **query embedding** khác model/chiều với index → kết quả vô nghĩa.
2. Đổi **top-k** rồi coi là "phương pháp mới" → không được tính.
3. **Đưa `gold`** vào agent/retrieval/query → vi phạm quy tắc.
4. Chỉ kiểm tra **citation ID hợp lệ** mà không đọc xem nguồn có hỗ trợ → không hợp lệ.
5. Chỉnh trên **test** rồi báo điểm trên chính test đó → không đánh giá độc lập.
6. Bịa số liệu hoặc sao chép không ghi nguồn → vi phạm `RULES.md`.
7. Nộp **`.env`, API key, token, dữ liệu mật** → vi phạm.
8. Chunk thiếu **ngày/phiên bản** → LLM không xử lý được mâu thuẫn khi augment.

---

## Phụ lục D — Bản đồ file trong repo

| Đường dẫn | Vai trò |
|---|---|
| `README.md` | Tổng quan bài và yêu cầu |
| `GUIDE.md` | Hướng dẫn 5 phần chính |
| `BENCHMARK.md` | Bộ câu hỏi và cách báo metric |
| `RUBRIC.md` | Thang điểm 100 |
| `RULES.md` | Quy tắc làm bài |
| `SUBMISSION.md` | Checklist nộp bài |
| `ADVANCED.md` | Thử thách nâng cao +15 |
| `PSEUDOCODE.md` | Luồng triển khai gợi ý |
| `REPORT_TEMPLATE.md` | Mẫu báo cáo |
| `starter/agentic.py` | Khung agent (`Controller`, `Retriever`, `run_agent`) |
| `starter/baseline.py` | Baseline TF-IDF lexical, chạy offline |
| `starter/convert_day6.py` | Chuyển JSON Day 6 sang schema Day 7 |
| `starter/agent_metrics.py` | Tổng hợp nhãn đánh giá agent |
| `starter/README.md` | Cách kết nối, chạy baseline, tổng hợp metrics |
| `data/README.md` | Định dạng dữ liệu |
| `report/individual/MSSV_HoTen.md` | Báo cáo cá nhân (sao chép và điền) |
| `tests/` | Test mock kiểm tra code (không phải benchmark thật) |
