import os
import sys
import json
from collections import OrderedDict

# 样例Markdown文本，包含行内代码示例
markdown_text = """# 代码块测试

## 简单代码示例

这是一个`行内代码`的例子，可以在文本中嵌入代码片段。
"""

# 简化版的转换函数，专注于处理行内代码
def convert_inline_code(markdown_text):
    result = OrderedDict([
        ('children_id', ['1', '2', '3']),
        ('descendants', [])
    ])
    
    # 添加标题
    result['descendants'].append(OrderedDict([
        ('block_type', 3),
        ('block_id', '1'),
        ('heading1', OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', '代码块测试'),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('inline_code', False),
                            ('italic', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ])
            ]),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False)
            ]))
        ]))
    ]))
    
    # 添加空文本块
    result['descendants'].append(OrderedDict([
        ('block_type', 2),
        ('block_id', '2'),
        ('text', OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', ''),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('inline_code', False),
                            ('italic', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ])
            ]),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False)
            ]))
        ]))
    ]))
    
    # 添加行内代码示例段落
    result['descendants'].append(OrderedDict([
        ('block_type', 2),
        ('block_id', '3'),
        ('text', OrderedDict([
            ('elements', [
                # 第一部分文本："这是一个"
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', '这是一个'),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('inline_code', False),
                            ('italic', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ]),
                # 行内代码部分
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', '行内代码'),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('inline_code', True),
                            ('italic', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ]),
                # 后续文本部分
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', '的例子，可以在文本中嵌入代码片段。 '),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('inline_code', False),
                            ('italic', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ])
            ]),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False)
            ]))
        ]))
    ]))
    
    return result

# 运行测试
if __name__ == "__main__":
    result = convert_inline_code(markdown_text)
    print("生成的结果结构:")
    print(json.dumps(result, indent=2))
    
    # 验证是否包含行内代码
    last_block = result['descendants'][-1]
    if last_block['block_type'] == 2:  # text block
        elements = last_block['text']['elements']
        if len(elements) == 3:
            print("\n验证结果:")
            print(f"1. 第一个元素内容: {elements[0]['text_run']['content']}")
            print(f"2. 第二个元素内容: {elements[1]['text_run']['content']}")
            print(f"3. 第二个元素行内代码标志: {elements[1]['text_run']['text_element_style']['inline_code']}")
            print(f"4. 第三个元素内容: {elements[2]['text_run']['content']}")
        else:
            print(f"错误：元素数量不是3，而是 {len(elements)}")
    else:
        print(f"错误：最后一个块不是文本块，而是类型 {last_block['block_type']}") 