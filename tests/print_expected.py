import json
from collections import OrderedDict
import os

def load_expected_result(filename):
    with open(os.path.join('tests', 'test_data', 'json', filename), 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data

def convert_to_ordered_dict(obj):
    if isinstance(obj, dict):
        result = OrderedDict()
        for k, v in obj.items():
            result[k] = convert_to_ordered_dict(v)
        return result
    elif isinstance(obj, list):
        return [convert_to_ordered_dict(item) for item in obj]
    return obj

expected = load_expected_result('text_styles_result.json')

# 打印行内代码和最后一个文本元素的内容
block = expected['descendants'][0]
elements = block['text']['elements']
for i, element in enumerate(elements):
    content = element.get('text_run', {}).get('content', '')
    print(f'Element {i}: "{content}"')
    
    if element.get('text_run', {}).get('text_element_style', {}).get('inline_code', False):
        print(f'  这是行内代码，长度: {len(content)}')
        print(f'  ASCII codes: {[ord(c) for c in content]}')
    
    if element.get('text_run', {}).get('text_element_style', {}).get('strikethrough', False):
        print(f'  这是删除线，长度: {len(content)}')
        print(f'  ASCII codes: {[ord(c) for c in content]}')
    
    if i == len(elements) - 1:
        print(f'  这是最后一个元素，长度: {len(content)}')
        print(f'  ASCII codes: {[ord(c) for c in content]}') 