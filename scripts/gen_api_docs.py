"""导出静态 API 文档（OpenAPI 规范 + Swagger UI 页面）。

用法（在项目根目录执行）：

    python -m scripts.gen_api_docs                 # 输出到 docs/
    python -m scripts.gen_api_docs -o build/api    # 指定输出目录

产物：
    <out>/openapi.json   OpenAPI 3.0 规范
    <out>/index.html     Swagger UI 页面（引用同目录的 openapi.json）

适合随仓库提交或在 CI 中生成后托管到静态站点；
也可直接在运行时访问 /api/docs 查看最新文档。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zfjw.app import create_app  # noqa: E402
from zfjw.docs import build_openapi_spec, render_swagger_ui  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="导出静态 API 文档")
    parser.add_argument("-o", "--output", default="docs", help="输出目录（默认 docs/）")
    args = parser.parse_args()

    app = create_app()
    spec = build_openapi_spec(app, spec_url="openapi.json")
    html = render_swagger_ui(spec_url="openapi.json")

    os.makedirs(args.output, exist_ok=True)
    spec_path = os.path.join(args.output, "openapi.json")
    html_path = os.path.join(args.output, "index.html")

    with open(spec_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(html_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    operations = sum(len(v) for v in spec["paths"].values())
    print(f"已生成 {spec_path}（{len(spec['paths'])} 条路径 / {operations} 个操作）")
    print(f"已生成 {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
