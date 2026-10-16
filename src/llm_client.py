import json
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

def generate_questions(resume_text: str, num_questions: int = 5) -> list[str]:
    """根据简历内容生成针对性面试题。"""
    prompt = f"""你是一位金融行业软件外包公司的技术面试官。请根据以下简历，生成 {num_questions} 道面试题。
要求：结合候选人实际项目经历，考察技术深度和项目理解。只返回 JSON 数组，每项是一个问题字符串。

简历：
{resume_text}

输出格式：[{{"question": "..."}}, ...]"""
    
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    data = json.loads(resp.choices[0].message.content)
    questions = data.get("questions", data.get("items", []))
    if isinstance(questions, list) and questions and isinstance(questions[0], dict):
        return [q.get("question", str(q)) for q in questions]
    return questions if isinstance(questions, list) else []

def score_answer(question: str, answer: str) -> dict:
    """对候选人的回答进行多维度评分。"""
    prompt = f"""你是面试评分专家。请对以下面试回答进行评分。

面试题：{question}
候选人回答：{answer}

请从以下维度评分（总分100）：
- content_quality（内容质量，40分）：技术点准确性、逻辑性
- depth（深度，30分）：是否有具体案例、数据、深入分析
- clarity（表达清晰度，30分）：条理是否清晰

同时判断是否需要追问（need_followup），如果需要追问，给出 followup_question。
返回严格 JSON：
{{
  "score": 整数,
  "dimensions": {{"content_quality": 整数, "depth": 整数, "clarity": 整数}},
  "feedback": "简短评语",
  "need_followup": true/false,
  "followup_question": "追问问题或空字符串"
}}"""
    
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(resp.choices[0].message.content)

def generate_final_report(scores: list[dict], questions: list[str]) -> str:
    """根据所有评分生成最终面评报告。"""
    detail = "\n".join([
        f"Q{i+1}: {q}\n得分: {s.get('score', 'N/A')}\n评语: {s.get('feedback', '')}"
        for i, (q, s) in enumerate(zip(questions, scores))
    ])
    prompt = f"""根据以下面试记录，生成一份简洁的面试评估报告，包含总体评价、技术亮点、待改进点。
只返回 JSON: {{"overall": "总体评价", "strengths": ["亮点1"], "improvements": ["改进1"]}}

记录：
{detail}"""
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(resp.choices[0].message.content)
