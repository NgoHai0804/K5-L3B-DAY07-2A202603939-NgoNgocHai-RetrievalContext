"""Generate complete Day 7 benchmark questions (27 answerable + 4 unanswerable)."""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DAY6_Q_FILE = Path("D:/AI20K/Day06/lab/K5-L3B-DAY06-NgoNgocHai-2A202603939-DataIngestion/benchmark/questions.json")

day6_data = json.loads(DAY6_Q_FILE.read_text(encoding="utf-8"))
raw_questions = day6_data["questions"]

# 27 answerable questions
answerable_questions = []
for q in raw_questions:
    gold_evidence = q["evidence_quote"]
    # Fix q08 to fit inside chunk boundary on page 18
    if q["id"] == "q08":
        gold_evidence = "drawn from federal court decisions, comprising about 67,000"

    item = {
        "id": q["id"],
        "split": q["split"],
        "question": q["question"],
        "expected_answer": q["expected_answer"],
        "gold": [
            {
                "source_id": q["gold_source_id"],
                "page": q["gold_page"],
                "evidence": gold_evidence
            }
        ]
    }
    if q.get("filter"):
        item["filter"] = q["filter"]
    answerable_questions.append(item)

# 4 unanswerable questions (2 dev, 2 test)
unanswerable_questions = [
    {
        "id": "u01",
        "split": "dev",
        "question": "Which deep reinforcement learning framework does the survey recommend for drafting Vietnamese commercial contracts?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Bộ tài liệu chỉ khảo sát các tập dữ liệu và mô hình cho tiếng Anh, tiếng Trung, tiếng Đức và tiếng Ấn Độ; không có nội dung về soạn thảo hợp đồng thương mại Việt Nam."
    },
    {
        "id": "u02",
        "split": "dev",
        "question": "What is the fine amount in Euros for violating GDPR Article 83 according to the legal NLP survey?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Bài survey tập trung vào các bài toán NLP, dataset và mô hình xử lý ngôn ngữ trong luật, không trích dẫn mức phạt chi tiết bằng Euro theo Điều 83 GDPR."
    },
    {
        "id": "u03",
        "split": "test",
        "question": "What is the token limit of the Japanese Supreme Court judgment prediction model introduced in 2025?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Hai tài liệu survey được công bố vào năm 2024 và 2021; không chứa mô hình dự đoán bản án Tòa án Tối cao Nhật Bản năm 2025."
    },
    {
        "id": "u04",
        "split": "test",
        "question": "How many French penal code articles were annotated for the LeXmart reasoning benchmark?",
        "answerable": False,
        "expected_behavior": "search_and_abstain",
        "absence_reason": "Khảo sát chỉ đánh giá các benchmark như JEC-QA (Trung Quốc), CaseHOLD, LegalBench (Mỹ), và các benchmark luật Ấn Độ; không có benchmark LeXmart hay bộ luật hình sự Pháp."
    }
]

# Write data/questions.json (answerable questions for baseline & retrieval benchmark)
(DATA_DIR / "questions.json").write_text(
    json.dumps(answerable_questions, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)
print(f"Wrote {len(answerable_questions)} answerable questions to data/questions.json")

# Write data/unanswerable_questions.json
(DATA_DIR / "unanswerable_questions.json").write_text(
    json.dumps(unanswerable_questions, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)
print(f"Wrote {len(unanswerable_questions)} unanswerable questions to data/unanswerable_questions.json")

# Write cases.json for agent_metrics.py (all 31 questions)
cases = []
for q in answerable_questions:
    cases.append({
        "id": q["id"],
        "split": q["split"],
        "question": q["question"],
        "answerable": True,
        "expected_behavior": "search_and_answer"
    })
for u in unanswerable_questions:
    cases.append({
        "id": u["id"],
        "split": u["split"],
        "question": u["question"],
        "answerable": False,
        "expected_behavior": u["expected_behavior"],
        "absence_reason": u["absence_reason"]
    })

(DATA_DIR / "cases.json").write_text(
    json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)
print(f"Wrote {len(cases)} cases to data/cases.json")

# Prepare converted raw input for starter/convert_day6.py
raw_input_q = []
for q in raw_questions:
    gold_ev = q["evidence_quote"]
    if q["id"] == "q08":
        gold_ev = "drawn from federal court decisions, comprising about 67,000"
    raw_input_q.append({
        "id": q["id"],
        "split": q["split"],
        "question": q["question"],
        "expected_answer": q["expected_answer"],
        "gold_source_id": q["gold_source_id"],
        "gold_page": q["gold_page"],
        "evidence_quote": gold_ev,
        **({"filter": q["filter"]} if q.get("filter") else {})
    })

(DATA_DIR / "day6_questions_raw.json").write_text(
    json.dumps(raw_input_q, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)
print(f"Wrote raw questions array to data/day6_questions_raw.json for convert_day6.py")
