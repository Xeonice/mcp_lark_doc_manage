#!/usr/bin/env python3
import os
import sys
import coverage
import pytest

# 设置环境变量
os.environ["TESTING"] = "true"
os.environ["OAUTH_PORT"] = "9997"
os.environ["LARK_APP_ID"] = "test_app_id"
os.environ["LARK_APP_SECRET"] = "test_app_secret"
os.environ["FOLDER_TOKEN"] = "test_folder_token"

def main():
    """运行测试并收集覆盖率"""
    # 从命令行获取传递给 pytest 的参数
    args = sys.argv[1:] if len(sys.argv) > 1 else ["-xvs", "tests"]
    
    # 添加 --no-cov 参数以避免与 pytest-cov 插件冲突
    if "--no-cov" not in args:
        args.append("--no-cov")
    
    # 初始化覆盖率收集
    cov = coverage.Coverage(
        source=["src/mcp_lark_doc_manage"],
        omit=["*/tests/*", "*/conftest.py", "*/__pycache__/*"]
    )
    cov.start()
    
    try:
        # 运行测试
        exit_code = pytest.main(args)
    except KeyboardInterrupt:
        print("\n测试被中断")
        exit_code = 130
    finally:
        # 停止覆盖率收集，即使测试中断也要生成报告
        cov.stop()
        cov.save()
        
        # 生成覆盖率报告，显示未覆盖的行
        print("\n覆盖率报告:")
        cov.report(show_missing=True)
        
        # 生成 HTML 格式的详细报告
        cov.html_report(directory="coverage_html")
        print(f"\n详细的 HTML 覆盖率报告已生成在: {os.path.abspath('coverage_html')}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 