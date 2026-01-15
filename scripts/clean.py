#!/usr/bin/env python3
"""
书源清洗脚本
- 去除表情符号
- 去除括号及内容
- 转换特殊字符（圆圈数字、全角字符等）
- 规范名称和分组
- 清理多余空格
- 可选：按评分自动分组（精选/标准/备用）+ 排序
"""

import json
import re
import time
import argparse
from pathlib import Path

# 表情符号正则（覆盖常见 emoji 范围）
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # 常见 emoji
    "\U00002600-\U000027BF"  # 杂项符号
    "\U0001FA00-\U0001FAFF"  # 扩展符号
    "\U00002300-\U000023FF"  # 技术符号
    "\U00002B50-\U00002B55"  # 星星等
    "\U0000FE00-\U0000FE0F"  # 变体选择器
    "\U0000200D"             # 零宽连接符
    "\U0001F1E0-\U0001F1FF"  # 国旗
    "]+",
    flags=re.UNICODE
)

# 特殊符号（需要移除）
SPECIAL_SYMBOLS = re.compile(
    r'[★☆✦✧⭐🌟💫🔥💥✨🎉🎊📚📖📕📗📘📙👍👎👏🙏💪'
    r'❤️💕💖💗💙💚💛✅❌⭕❗❓'
    r'①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    r'㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟'
    r'⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻'
    r'Ⅰ-Ⅻ～~丨|｜👁🔰🎨📻📥💠'
    r'◎▪™〽㊣●○◆◇■□▲△▼▽'
    r'Ａ-Ｚａ-ｚ０-９'
    r']+'
)

# 括号及内容（中文括号、英文括号、方括号、尖括号）
BRACKET_PATTERN = re.compile(r'[（(【\[<][^）)】\]>]*[）)】\]>]')

# 名称后缀清洗模式（按顺序应用）
NAME_SUFFIX_PATTERNS = [
    (r'^源社区出品-', ''),                     # 来源前缀（优先处理）
    (r'^[+\-#.·]\s*', ''),                    # 开头特殊符号
    (r'#\d+$', ''),                           # #数字 版本号
    (r'\s*#[^\s]+$', ''),                     # #作者名 署名
    (r'\s+[^\s]+$', ''),                      # 空格+内容（如 "爱书包 破冰"）
    (r'_[a-zA-Z0-9.-]+\.[a-z]{2,}$', ''),    # _域名 后缀
    (r'-[\u4e00-\u9fa5]{2,4}$', ''),          # -作者名 后缀
    (r'[a-z]\d{1,3}$', ''),                   # 英文+数字后缀（如 b13）
    (r'(?<=[^\d])\d{1,3}$', ''),              # 纯数字后缀
]

# 分组排序顺序
GROUP_ORDER = {"精选": 0, "标准": 1, "备用": 2}

# 分组名称映射（原始 -> 标准）
GROUP_MAPPING = {
    "🌟 抓包": "抓包",
    "🎉 精选": "精选",
    "🔰 正版": "正版",
    "💠 综合": "综合",
    "📥 下载": "下载",
    "📚 出版": "出版",
    "🎨 漫画": "漫画",
    "📻 有声": "有声",
    "抓包": "抓包",
    "精选": "精选",
    "正版": "正版",
    "综合": "综合",
    "下载": "下载",
    "出版": "出版",
    "漫画": "漫画",
    "有声": "有声",
}


def calculate_quality_score(source: dict) -> int:
    """计算书源质量评分（满分约 60）"""
    score = 0

    # 基础状态 (0-7)
    if source.get('enabled', True):
        score += 5
    if source.get('enabledExplore'):
        score += 2

    # 响应时间 (0-15)
    rt = source.get('respondTime', 99999)
    if rt < 1000:
        score += 15
    elif rt < 3000:
        score += 12
    elif rt < 5000:
        score += 8
    elif rt < 10000:
        score += 4

    # 规则完整性 (0-20)
    if source.get('searchUrl'):
        score += 4
    if source.get('ruleSearch') or source.get('searchRule'):
        score += 4
    if source.get('ruleToc') or source.get('tocRule'):
        score += 4
    if source.get('ruleContent') or source.get('contentRule'):
        score += 6
    if source.get('exploreUrl'):
        score += 2

    # 更新时间 (0-10)
    last = source.get('lastUpdateTime', 0)
    if last:
        days = max(0, (time.time() * 1000 - last) / 86400000)
        if days < 30:
            score += 10
        elif days < 90:
            score += 7
        elif days < 180:
            score += 4
        elif days < 365:
            score += 2

    # 权重 (0-5)
    score += min(source.get('weight', 0) // 100, 5)

    return score


def get_grade_group(score: int) -> str:
    """根据评分返回分组名称"""
    if score >= 45:
        return "精选"
    elif score >= 40:
        return "标准"
    else:
        return "备用"


def strip_decorations(text: str) -> str:
    """移除装饰性内容（表情、特殊符号、括号、后缀等）"""
    if not text:
        return ""
    text = EMOJI_PATTERN.sub("", text)
    text = SPECIAL_SYMBOLS.sub("", text)
    text = BRACKET_PATTERN.sub("", text)
    # 名称后缀清洗
    for pattern, replacement in NAME_SUFFIX_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def clean_spaces(text: str) -> str:
    """清理空格"""
    if not text:
        return ""
    # 去除首尾空格
    text = text.strip()
    # 多个空格合并为一个
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_group(group: str) -> str:
    """规范化分组名称"""
    if not group:
        return ""

    # 先尝试直接映射
    if group in GROUP_MAPPING:
        return GROUP_MAPPING[group]

    # 清洗后再映射
    cleaned = clean_spaces(strip_decorations(group))
    if cleaned in GROUP_MAPPING:
        return GROUP_MAPPING[cleaned]

    return cleaned


def clean_source(source: dict, grade: bool = False) -> dict:
    """清洗单个书源"""
    # 清洗名称
    if "bookSourceName" in source:
        source["bookSourceName"] = clean_spaces(strip_decorations(source["bookSourceName"]))

    # 按评分分组（覆盖原有分组）
    if grade:
        score = calculate_quality_score(source)
        source["bookSourceGroup"] = get_grade_group(score)
    # 仅清洗分组
    elif "bookSourceGroup" in source:
        source["bookSourceGroup"] = normalize_group(source["bookSourceGroup"])

    # 清洗备注（保留内容，只去表情）
    if "bookSourceComment" in source and source["bookSourceComment"]:
        # 备注可能包含使用说明，只去除开头的表情
        comment = source["bookSourceComment"]
        # 只清理开头的表情符号
        comment = re.sub(r'^[\s]*' + EMOJI_PATTERN.pattern, '', comment)
        source["bookSourceComment"] = comment.strip()

    return source


def clean_sources(sources: list, grade: bool = False) -> list:
    """批量清洗书源"""
    return [clean_source(s, grade) for s in sources]


def sort_sources(sources: list) -> list:
    """按分组和名称排序"""
    return sorted(sources, key=lambda s: (
        GROUP_ORDER.get(s.get("bookSourceGroup", ""), 99),
        s.get("bookSourceName", "")
    ))


def main():
    parser = argparse.ArgumentParser(description="书源清洗脚本")
    parser.add_argument("--input", "-i", required=True, help="输入文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    parser.add_argument("--grade", "-g", action="store_true", help="按评分自动分组（精选/标准/备用）+ 排序")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"错误：输入文件不存在 {input_path}")
        return 1

    # 读取书源
    with open(input_path, "r", encoding="utf-8") as f:
        sources = json.load(f)

    print(f"读取书源：{len(sources)} 个")
    if args.grade:
        print("启用评分分组 + 排序模式")

    # 清洗
    cleaned = clean_sources(sources, grade=args.grade)

    # 排序（仅在 grade 模式下）
    if args.grade:
        cleaned = sort_sources(cleaned)

    # 输出
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"清洗完成，输出到：{output_path}")

    # 统计
    groups = {}
    for s in cleaned:
        g = s.get("bookSourceGroup", "未分组")
        groups[g] = groups.get(g, 0) + 1

    print("\n分组统计：")
    for g, count in sorted(groups.items(), key=lambda x: GROUP_ORDER.get(x[0], 99)):
        print(f"  {g or '未分组'}: {count}")

    return 0


if __name__ == "__main__":
    exit(main())
