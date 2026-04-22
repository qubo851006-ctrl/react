import base64
import os
import warnings
import httpx
from dotenv import load_dotenv
from openai import OpenAI

warnings.filterwarnings("ignore")  # 屏蔽内网 SSL 警告
load_dotenv(override=True)

MODEL_VISION = os.getenv("MODEL_VISION", "qwen2.5-vl-72b")


def encode_image(image_path: str) -> str:
    """将图片转为 base64 字符串"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("AIRCHINA_API_KEY"),
        base_url=os.getenv("AIRCHINA_BASE_URL"),
        http_client=httpx.Client(verify=False),
    )


def count_attendees(image_path: str) -> dict:
    """
    分析签到表图片，统计参与人数及提取抬头信息
    返回: {count, topic, location, date}
    """
    client = get_client()

    image_data = encode_image(image_path)
    ext = image_path.split(".")[-1].lower()
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = """这是一张培训签到表图片。

第一步：提取抬头信息
- 培训主题、培训地点、培训时间

第二步：逐行列出所有有内容的姓名格
签到表分左右两栏，请从第1行开始，逐行检查左栏姓名格和右栏姓名格：
- 有手写内容的格子：写"有"
- 空白的格子：写"空"
格式示例：
行1：左=有，右=有
行2：左=有，右=空
行3：左=空，右=空（遇到连续空行可停止）

第三步：统计
把所有标记为"有"的格子数量加总，就是总人数。
注意：忽略表格底部任何手写的合计/估计数字。

请按以下格式输出，不要有多余内容：
主题：xxx
地点：xxx
时间：xxx
明细：（粘贴第二步的逐行结果）
人数：数字
"""

    response = client.chat.completions.create(
        model=MODEL_VISION,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    result_text = response.choices[0].message.content.strip()
    return parse_sign_in_result(result_text)


def parse_sign_in_result(text: str) -> dict:
    """解析 AI 返回的签到表信息"""
    result = {"topic": "", "location": "", "date": "", "count": 0}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("主题："):
            result["topic"] = line.replace("主题：", "").strip()
        elif line.startswith("地点："):
            result["location"] = line.replace("地点：", "").strip()
        elif line.startswith("时间："):
            result["date"] = line.replace("时间：", "").strip()
        elif line.startswith("人数："):
            count_str = line.replace("人数：", "").strip()
            try:
                result["count"] = int("".join(filter(str.isdigit, count_str)))
            except ValueError:
                result["count"] = 0
    return result
