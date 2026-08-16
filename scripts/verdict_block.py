"""verdict_block — v8 契约层: 节点 md 顶部 fenced YAML verdict 块的抽取与 schema 校验。

单一数据源纪律: 装配(决断卡/面板/Top3/变化区块)与增量对比只读节点 md **顶部**的
fenced YAML 块——正文中部出现的块不算数, 防止第二数据源。

schema 文件在 scripts/schemas/ (节点×4 + decision + assembly + manifest + common 共享定义),
跨文件 $ref 按文件名解析(如 common.schema.json#/$defs/red_flag_item)。

CLI(供写手 agent / lint / 调度自检):
  python -m scripts.verdict_block --schema node-quality --file output/.../nodes/node-quality.md
  退出码 0=合法, 1=有错(逐条打印), 2=文件/块缺失。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

# 顶部块: 允许前导空白, 之后必须直接是 ```yaml fence
_TOP_BLOCK_RE = re.compile(r"\A\s*```yaml[ \t]*\n(.*?)\n[ \t]*```", re.DOTALL)


class BlockNotFound(ValueError):
    """md 文件顶部没有 fenced YAML 块, 或块不是 YAML 映射。"""


def extract_yaml_block(md_text: str) -> dict:
    """抽取 md 顶部的 fenced YAML 块, 返回 dict; 找不到抛 BlockNotFound。"""
    m = _TOP_BLOCK_RE.match(md_text)
    if not m:
        raise BlockNotFound("md 顶部无 ```yaml 块(装配只读顶部块, 正文中部的块不算)")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        raise BlockNotFound("顶部 YAML 块不是映射(期望 key: value 结构)")
    return data


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        contents = json.loads(p.read_text(encoding="utf-8"))
        resources.append((p.name, Resource.from_contents(contents)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    path = SCHEMA_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"未知 schema: {schema_name}(找不到 {path.name})")
    schema = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_registry())


def validate(data: dict, schema_name: str) -> list[str]:
    """按 schema 校验, 返回错误列表(空列表=合法), 每条含字段路径。"""
    errors = sorted(
        _validator(schema_name).iter_errors(data),
        key=lambda e: [str(x) for x in e.absolute_path],
    )
    out = []
    for e in errors:
        path = "/".join(str(x) for x in e.absolute_path) or "<root>"
        out.append(f"{path}: {e.message}")
    return out


def load_and_validate(md_path: Path, schema_name: str) -> tuple[dict, list[str]]:
    """读节点 md → 抽顶部块 → 校验。返回 (块数据, 错误列表)。"""
    data = extract_yaml_block(Path(md_path).read_text(encoding="utf-8"))
    return data, validate(data, schema_name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schema", required=True, help="schema 名(不带 .schema.json), 如 node-quality")
    ap.add_argument("--file", required=True, help="节点 md 或 JSON 文件路径")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"文件不存在: {path}")
        return 2
    try:
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = extract_yaml_block(path.read_text(encoding="utf-8"))
    except (BlockNotFound, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"解析失败: {exc}")
        return 2

    errs = validate(data, args.schema)
    if errs:
        for e in errs:
            print(f"✗ {e}")
        return 1
    print(f"✓ {path.name} 通过 {args.schema} 校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
