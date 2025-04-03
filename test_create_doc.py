import asyncio
import os
import json
from dotenv import load_dotenv
from mcp_lark_doc_manage.server import create_doc, larkClient, USER_ACCESS_TOKEN, TOKEN_EXPIRES_AT, token_lock

async def test_create_doc():
    """测试创建文档功能"""
    # 加载环境变量
    load_dotenv()
    
    # 测试数据
    title = "测试文档 - 2024-03-21"
    content = """# 测试文档

这是一个测试文档，用于验证文档创建功能。

## 功能列表

1. 创建文档
2. 添加内容
3. 设置标题

## 代码示例

```python
def hello_world():
    print("Hello, World!")
```

## 表格示例

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 内容1 | 内容2 | 内容3 |
| 数据1 | 数据2 | 数据3 |

## 总结

这是一个完整的测试文档，包含了各种 Markdown 格式。
"""
    
    try:
        # 确保环境变量已设置
        if not os.getenv("LARK_APP_ID") or not os.getenv("LARK_APP_SECRET"):
            print("错误：请在 .env 文件中设置 LARK_APP_ID 和 LARK_APP_SECRET")
            return
            
        if not os.getenv("FOLDER_TOKEN"):
            print("错误：请在 .env 文件中设置 FOLDER_TOKEN")
            return
            
        print("开始创建文档...")
        print(f"标题: {title}")
        print("内容长度:", len(content))
        
        # 直接调用创建文档函数
        result = await create_doc(title=title, content=content)
        
        # 解析结果
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                pass
                
        # 打印结果
        print("\n创建结果:")
        if isinstance(result, dict):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    # 运行测试函数
    asyncio.run(test_create_doc()) 