# RUNBOOK — Day 7 Retrieval & Context Engineering

Hướng dẫn tái lập toàn bộ kết quả trong báo cáo `report/individual/2A202603939_NgoNgocHai.md`.

## 1. Điều kiện tiên quyết
- Python 3.11+ (đã test 3.12).
- Docker + container Postgres/pgvector của Day 6 đang chạy: image `pgvector/pgvector:0.8.7-pg16`, cổng `127.0.0.1:55433`, DB `day6_lab`.
- OpenRouter API key.

## 2. Cài đặt (một lần)
```powershell
copy .env.example .env    # sau đó điền OPENROUTER_API_KEY
pip install -r requirements.txt
```
Windows PowerShell cần thêm cho repo này:
```powershell
$env:PYTHONUTF8="1"
$env:PSYCOPG_IMPL="python"   # nếu Smart App Control chặn DLL psycopg (xem mục 7)
```

## 3. Dữ liệu đã kèm sẵn (không cần tạo lại)
- `data/day6_chunks.json` — 386 chunk Strategy A.
- `data/questions.json` — 27 câu có đáp án (dev 19, test 8).
- `data/unanswerable_questions.json` — 4 câu thiếu bằng chứng (dev 2, test 2).
- `data/cases.json` — 31 case cho đánh giá agent.

## 4. Chạy test
```powershell
python -m unittest discover -s tests -v
```

## 5. Tái lập kết quả
```powershell
# Bước 5: 3 phương pháp retrieval trên dev
python starter/benchmark_retrieval.py --split dev --output starter/results/retrieval-step5 --top-k 3 --candidate-k 10 --context-budget 2500

# Bước 6: 2 cấu hình cải thiện + phân tích lỗi trên dev
python starter/benchmark_improvements.py

# Bước 7: đánh giá test độc lập (cấu hình đã chốt)
python starter/evaluate_test.py

# Bước 4: agent trên dev (dense)
python starter/run_agent_benchmark.py --split dev --output starter/results/agent-dev --retriever dense --top-k 3 --budget 2500 --max-searches 3

# Bước 8: agent trên test — baseline dense
python starter/run_agent_benchmark.py --split test --output starter/results/agent-test-baseline --retriever dense --top-k 3 --budget 2500 --max-searches 2

# Bước 8: agent trên test — cấu hình chọn hybrid
python starter/run_agent_benchmark.py --split test --output starter/results/agent-test --retriever hybrid --top-k 8 --budget 4500 --max-searches 2

# Bước 8: tổng hợp metric agent (nhãn đã chấm thủ công trong reviews.json)
python starter/agent_metrics.py --cases data/cases.json --traces starter/results/agent-test/agent_traces.json --reviews starter/results/agent-test/reviews.json --split test --output starter/results/agent-test/summary.json
```

## 6. Chia sẻ artifact
`starter/results/` và `starter/data/` bị `.gitignore`. Để người chấm xem kết quả, chọn một trong hai:
- `git add -f starter/results/agent-test starter/results/agent-test-baseline starter/results/retrieval-step5 starter/results/improvements-dev starter/results/step7-test starter/results/step7-lock`
- Hoặc chạy lại các lệnh ở mục 5 để tái tạo.

Nhãn chấm thủ công: `starter/results/agent-test/reviews.json`, `starter/results/agent-test-baseline/reviews.json`.

## 7. Ghi chú Windows
- `python3` không tồn tại trên Windows → dùng `python` hoặc `py`.
- `UnicodeDecodeError` → đặt `$env:PYTHONUTF8="1"`.
- `psycopg` báo "Application Control policy has blocked this file" → đặt `$env:PSYCOPG_IMPL="python"` và đặt `libpq.dll` trong thư mục Python (hoặc trên PATH), hoặc tắt Smart App Control.

## 8. Tái tạo benchmark từ Day 6 (tùy chọn)
```powershell
$env:DAY6_DIR="D:\AI20K\Day06\lab\K5-L3B-DAY06-NgoNgocHai-2A202603939-DataIngestion"
python starter/generate_benchmark.py
python starter/convert_day6.py --chunks data/day6_chunks.json --questions data/day6_questions_raw.json --output starter/data/converted
```