import json
import re
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


# ---------- JSON 解析工具 ----------

def _safe_parse_json(content: str):
    """从模型返回的文本中稳健地提取 JSON 对象或数组。"""
    if not content:
        return None

    content = content.strip()

    # 去掉 markdown 代码块标记 ```json ... ``` 或 ``` ... ```
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    content = content.strip()

    # 直接尝试解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 兜底：提取第一个 {...} 或 [...]
    match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _extract_questions(data) -> list[str]:
    """从各种可能的返回结构中提取问题列表。"""
    if data is None:
        return []

    # 情况1：直接是列表
    if isinstance(data, list):
        result = []
        for item in data:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                for key in ("question", "content", "text", "q", "title"):
                    if key in item:
                        result.append(str(item[key]))
                        break
        return result

    # 情况2：是字典，尝试多个可能的字段名
    if isinstance(data, dict):
        for key in ("questions", "items", "data", "result", "list", "question_list"):
            if key in data:
                extracted = _extract_questions(data[key])
                if extracted:
                    return extracted
        # 如果字典里只有一个值且是列表/字典，递归处理
        for v in data.values():
            if isinstance(v, (list, dict)):
                extracted = _extract_questions(v)
                if extracted:
                    return extracted

    return []


# ---------- 核心业务函数 ----------

def generate_questions(resume_text: str, num_questions: int = 5) -> list[str]:
    """根据简历内容生成针对性面试题。"""
    prompt = f"""你是一位金融行业软件外包公司的技术面试官。请根据以下简历，生成 {num_questions} 道面试题。
要求：
1. 结合候选人实际项目经历，考察技术深度和项目理解
2. 覆盖技术能力、项目经验、问题解决能力
3. 问题应具体、有针对性，避免泛泛而谈

简历：
{resume_text}

请严格只返回一个 JSON 数组，不要包含任何解释文字或 markdown 标记。格式示例：
["问题1", "问题2", "问题3"]"""

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    content = resp.choices[0].message.content
    data = _safe_parse_json(content)
    questions = _extract_questions(data)

    # 最终兜底：如果解析失败，按行拆分纯文本
    if not questions and content:
        lines = [l.strip(" -•*\t0123456789.") for l in content.split("\n") if l.strip()]
        questions = [l for l in lines if len(l) > 5][:num_questions]

    return questions


def score_answer(question: str, answer: str) -> dict:
    """对候选人的回答进行多维度评分。"""
    prompt = f"""你是面试评分专家。请对以下面试回答进行客观评分。

面试题：{question}
候选人回答：{answer}

请从以下维度评分（总分100）：
- content_quality（内容质量，40分）：技术点准确性、逻辑性、是否答到要点
- depth（深度，30分）：是否有具体案例、数据、深入分析
- clarity（表达清晰度，30分）：条理是否清晰、表达是否流畅

评分要求：
1. 客观公正，不因表达风格扣分，重点关注内容实质
2. 如果回答明显偏题或空白，得分应低于30分
3. 判断是否需要追问（need_followup）：如果回答过于笼统、缺乏细节，或涉及简历中的关键项目但未展开，应追问

请严格只返回一个 JSON 对象，不要包含任何解释文字或 markdown 标记。格式：
{{
  "score": 85,
  "dimensions": {{"content_quality": 34, "depth": 25, "clarity": 26}},
  "feedback": "简短评语，指出优点和不足",
  "need_followup": false,
  "followup_question": ""
}}"""

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    data = _safe_parse_json(resp.choices[0].message.content)

    # 兜底：如果解析失败，返回默认结构
    if not isinstance(data, dict):
        return {
            "score": 0,
            "dimensions": {"content_quality": 0, "depth": 0, "clarity": 0},
            "feedback": "评分解析失败，请人工复核",
            "need_followup": False,
            "followup_question": "",
        }

    # 规范化字段，防止前端 KeyError
    data.setdefault("score", 0)
    data.setdefault("dimensions", {})
    data.setdefault("feedback", "")
    data.setdefault("need_followup", False)
    data.setdefault("followup_question", "")

    return data


def generate_final_report(scores: list[dict], questions: list[str]) -> dict:
    """根据所有评分生成最终面评报告。"""
    detail = "\n".join([
        f"Q{i+1}: {q}\n得分: {s.get('score', 'N/A')}\n评语: {s.get('feedback', '')}"
        for i, (q, s) in enumerate(zip(questions, scores))
    ])

    prompt = f"""根据以下面试记录，生成一份简洁的面试评估报告。

要求：
1. 总体评价控制在100字以内
2. 技术亮点列出2-3条，基于具体回答内容
3. 待改进点列出2-3条，客观指出不足
4. 不做录用建议，只做能力评估

面试记录：
{detail}

请严格只返回一个 JSON 对象，不要包含任何解释文字或 markdown 标记。格式：
{{"overall": "总体评价", "strengths": ["亮点1", "亮点2"], "improvements": ["改进1", "改进2"]}}"""

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    data = _safe_parse_json(resp.choices[0].message.content)

    # 兜底
    if not isinstance(data, dict):
        return {
            "overall": "报告生成失败，请人工复核面试记录",
            "strengths": [],
            "improvements": [],
        }

    data.setdefault("overall", "")
    data.setdefault("strengths", [])
    data.setdefault("improvements", [])

    return data


def check_followup_needed(question: str, answer: str) -> tuple[bool, str]:
    """独立判断是否需要追问（可选，用于更精细的控制）。"""
    result = score_answer(question, answer)
    return result.get("need_followup", False), result.get("followup_question", "")
