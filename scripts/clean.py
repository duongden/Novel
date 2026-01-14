#!/usr/bin/env python3
"""
书源清洗脚本
- 去除表情符号
- 规范名称和分组
- 清理多余空格
"""

import json
import re
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
    "]+",
    flags=re.UNICODE
)

# 特殊符号（需要移除）
SPECIAL_SYMBOLS = re.compile(r'[★☆✦✧⭐🌟💫🔥💥✨🎉🎊📚📖📕📗📘📙👍👎👏🙏💪❤️💕💖💗💙💚💛✅❌⭕❗❓①②③④⑤⑥⑦⑧⑨⑩Ⅰ-Ⅻ～~丨|｜👁🔰🎨📻📥💠🎉]+')

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


def remove_emoji(text: str) -> str:
    """移除表情符号"""
    if not text:
        return ""
    text = EMOJI_PATTERN.sub("", text)
    text = SPECIAL_SYMBOLS.sub("", text)
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
    cleaned = clean_spaces(remove_emoji(group))
    if cleaned in GROUP_MAPPING:
        return GROUP_MAPPING[cleaned]

    return cleaned


def clean_source(source: dict) -> dict:
    """清洗单个书源"""
    # 清洗名称
    if "bookSourceName" in source:
        source["bookSourceName"] = clean_spaces(remove_emoji(source["bookSourceName"]))

    # 清洗分组
    if "bookSourceGroup" in source:
        source["bookSourceGroup"] = normalize_group(source["bookSourceGroup"])

    # 清洗备注（保留内容，只去表情）
    if "bookSourceComment" in source and source["bookSourceComment"]:
        # 备注可能包含使用说明，只去除开头的表情
        comment = source["bookSourceComment"]
        # 只清理开头的表情符号
        comment = re.sub(r'^[\s]*' + EMOJI_PATTERN.pattern, '', comment)
        source["bookSourceComment"] = comment.strip()

    return source


def clean_sources(sources: list) -> list:
    """批量清洗书源"""
    return [clean_source(s) for s in sources]


def main():
    parser = argparse.ArgumentParser(description="书源清洗脚本")
    parser.add_argument("--input", "-i", required=True, help="输入文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出文件路径")
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

    # 清洗
    cleaned = clean_sources(sources)

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
    for g, count in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  {g or '未分组'}: {count}")

    return 0


if __name__ == "__main__":
    exit(main())
