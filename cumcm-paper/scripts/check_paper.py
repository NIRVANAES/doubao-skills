#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cumcm-paper 机械初筛脚本：扫描数模论文源文件(.tex/.md/.txt)中的可机械判定问题。
只做格式/合规层面的确定性检查，语义质量仍需按 review-checklist.md 人工红队复核。

用法:
    python check_paper.py <文件或目录> [文件或目录 ...] [--ext tex,md,txt]
退出码: 发现 ERROR 返回 1, 否则 0 (WARN 不影响退出码)
"""
import sys, re, argparse
from pathlib import Path

# ---- 规则库（可按需增删）----
# 匿名/身份泄漏风险词（命中给 WARN，需人工确认是否真泄漏）
IDENTITY = [
    "致谢", "指导教师", "指导老师", "作者简介", "笔者", "我校", "我院", "本学院",
    "学号", "班级", "姓名", "大学", "学院", "赛区",
]
# LaTeX 里出现这些命令且非空，基本可判匿名/结构问题
IDENTITY_CMD = [r"\\author\s*\{[^}]+\}", r"\\thanks\{[^}]+\}", r"\\title\s*\{[^}]*?(大学|学院)[^}]*?\}"]
# 教学占位 / 未完成残留（ERROR：成稿不允许）
PLACEHOLDER = [r"\\fillin", r"\bTODO\b", r"\bFIXME\b", r"placeholder",
               "待补", "待填", "此处省略", "（……）", r"\bXXX\b", "此处插入"]
# 成稿中少见、需人工确认的符号（WARN）
SOFT_PLACEHOLDER = ["【", "】", "略）"]
# 不应出现的结构：英文摘要、目录
FORBIDDEN_STRUCT = [r"\\tableofcontents", r"\\listoffigures", r"\\listoftables"]
EN_ABSTRACT = [r"\bAbstract\b", r"\bKeywords?\b", r"Key\s*words?"]
# 空话套话（WARN：无证据表述，应改为带数值/证据）
EMPTY_CLAIM = ["效果良好", "结果合理", "合理结果", "精度高", "实用性强", "具有较强的",
               "鲁棒性强", "泛化能力强", "符合实际情况", "令人满意"]
# 代码/推导省略（WARN）
OMIT = ["其余同理", "以此类推", "代码省略", "此处省略", "由于篇幅"]

LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|autoref|eqref|pageref|cref|Cref)\{([^}]+)\}")
FIGTAB_LABEL = re.compile(r"\\label\{((?:fig|tab)[^}:]*)\}")


def scan_file(p: Path):
    issues = []  # (level, code, lineno, msg)
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = p.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    for i, line in enumerate(lines, 1):
        hits = []
        for w in IDENTITY:
            if w in line:
                issues.append(("WARN", "IDENTITY", i, f"疑似身份/校名词「{w}」: {line.strip()[:80]}"))
        for pat in IDENTITY_CMD:
            if re.search(pat, line):
                issues.append(("ERROR", "IDENTITY-CMD", i, f"疑似非空作者/标题身份命令: {line.strip()[:80]}"))
        ph = [pat for pat in PLACEHOLDER if re.search(pat, line)]
        if ph:
            issues.append(("ERROR", "PLACEHOLDER", i, f"占位/未完成残留 {len(ph)} 处: {line.strip()[:80]}"))
        for w in SOFT_PLACEHOLDER:
            if w in line:
                issues.append(("WARN", "SOFT-MARK", i, f"待确认符号「{w}」(正文一般不用): {line.strip()[:60]}"))
        for pat in FORBIDDEN_STRUCT:
            if re.search(pat, line):
                issues.append(("ERROR", "STRUCT", i, f"不应出现目录/图表目录: {line.strip()[:80]}"))
        # 跳过 LaTeX 的 abstract 环境命令本身，只抓真正的英文摘要/英文关键词
        is_tex_env = ("\\begin{abstract}" in line) or ("\\end{abstract}" in line)
        if not is_tex_env:
            for pat in EN_ABSTRACT:
                if re.search(pat, line, re.I):
                    issues.append(("WARN", "EN-ABSTRACT", i, f"疑似英文摘要/英文关键词(国赛不附英文摘要): {line.strip()[:80]}"))
                    break
        for w in EMPTY_CLAIM:
            if w in line:
                issues.append(("WARN", "EMPTY-CLAIM", i, f"空话套话「{w}」需改为带数值/证据的表述"))
        for w in OMIT:
            if w in line:
                issues.append(("WARN", "OMIT", i, f"疑似省略代码/推导「{w}」，附录代码须完整"))

    # 图表 label 是否都被引用（仅对 tex 有意义）
    if p.suffix == ".tex":
        labels = {m.group(1): ln for ln, line in enumerate(lines, 1)
                  for m in FIGTAB_LABEL.finditer(line)}
        refs = set()
        for line in lines:
            for m in REF_RE.finditer(line):
                refs.update(x.strip() for x in m.group(1).split(","))
        for lab, ln in labels.items():
            if lab not in refs:
                issues.append(("WARN", "UNREF-LABEL", ln, f"图表标签 {lab} 定义后未被 \\ref 引用"))
        # 引用了但没定义
        all_labels = set(m.group(1) for m in LABEL_RE.finditer(text))
        for r in refs:
            if r not in all_labels:
                issues.append(("ERROR", "DANGLING-REF", 0, f"引用了不存在的标签 {r}"))

        # 摘要长度粗判：abstract 环境内中文字符数（国赛摘要与标题关键词同页，一般 600–1100 字）
        m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
        if m:
            zh = re.findall(r"[\u4e00-\u9fff]", m.group(1))
            n = len(zh)
            if n < 400:
                issues.append(("WARN", "ABSTRACT-LEN", 0, f"摘要正文仅约 {n} 个汉字，可能过短、结果未给全"))
            elif n > 1300:
                issues.append(("WARN", "ABSTRACT-LEN", 0, f"摘要正文约 {n} 个汉字，可能超出一页"))
    return issues


def collect(paths, exts):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for e in exts:
                files.extend(sorted(p.rglob(f"*.{e}")))
        elif p.exists():
            files.append(p)
        else:
            print(f"[SKIP] 路径不存在: {raw}")
    # 去重并跳过编译产物目录
    out = []
    for f in files:
        if any(part in ("build", "out", ".git", "node_modules") for part in f.parts):
            continue
        out.append(f)
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--ext", default="tex,md,txt")
    args = ap.parse_args()
    exts = [e.strip().lstrip(".") for e in args.ext.split(",")]
    files = collect(args.paths, exts)
    if not files:
        print("未找到可检查文件。")
        return 0

    n_err = n_warn = 0
    for f in files:
        issues = scan_file(f)
        if not issues:
            print(f"[OK] {f}")
            continue
        print(f"\n=== {f} ===")
        for level, code, ln, msg in sorted(issues, key=lambda x: (0 if x[0] == "ERROR" else 1, x[2])):
            pos = f"L{ln}" if ln else "全局"
            print(f"  [{level}] {code} @{pos}  {msg}")
            if level == "ERROR":
                n_err += 1
            else:
                n_warn += 1
    print("\n" + "=" * 48)
    print(f"扫描 {len(files)} 个文件：ERROR {n_err} 项，WARN {n_warn} 项")
    print("ERROR 为成稿必须消除项；WARN 需人工确认。语义质量请再按 review-checklist.md 红队复核。")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
