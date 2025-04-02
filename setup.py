from setuptools import setup, find_packages

setup(
    name="mcp_lark_doc_manage",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "lark-sdk",
        "aiohttp",
        "python-dotenv",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "mcp-lark-doc-manage=mcp_lark_doc_manage.server:main",
        ],
    },
) 