import re
import uuid
import urllib.parse
import os
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict
import base64
import mistune

def generate_unique_id() -> str:
    """Generate a unique ID for nested structure children."""
    # 生成一个 UUID 并将其转换为 base64 格式
    # 使用 uuid4 生成随机 UUID
    id_bytes = uuid.uuid4().bytes
    # 转换为 base64 并去除 padding
    id_str = base64.urlsafe_b64encode(id_bytes).decode('ascii').rstrip('=')
    # 截取前 24 个字符
    return id_str[:24]

def convert_list_item_to_block(line: str, current_level: int, list_type: str) -> OrderedDict:
    """Convert a list item to a block.

    Args:
        line (str): The line containing the list item.
        current_level (int): The current indentation level.
        list_type (str): The type of list ('bullet' or 'ordered').

    Returns:
        OrderedDict: The block representation of the list item.
    """
    # Remove list marker and get content
    if list_type == 'bullet':
        content = re.sub(r'^(\s*)[*+-]\s+', '', line)
        block_type = 12
    else:  # ordered
        content = re.sub(r'^(\s*)\d+\.\s+', '', line)
        block_type = 13

    # Create text run for the content
    text_run = OrderedDict([
        ('content', content.strip()),
        ('text_element_style', create_text_element_style())
    ])

    # Create elements list with the text run
    elements = [OrderedDict([('text_run', text_run)])]

    # Create style object
    style = OrderedDict([
        ('align', 1),
        ('folded', False)
    ])

    # Add sequence for ordered lists
    if list_type == 'ordered':
        if current_level == 0:
            style['sequence'] = '1'
        else:
            style['sequence'] = 'auto'

    # Create the block
    block = OrderedDict([
        ('block_type', block_type),
        (list_type, OrderedDict([
            ('elements', elements),
            ('style', style)
        ]))
    ])

    return block

def convert_todo_to_block(content: str, done: bool = False) -> OrderedDict:
    """Convert a todo item to a block.

    Args:
        content (str): The content of the todo item.
        done (bool): Whether the todo item is done.

    Returns:
        OrderedDict: The block representation of the todo item.
    """
    # Create text run for the content
    text_run = OrderedDict([
        ('content', content.strip()),
        ('text_element_style', create_text_element_style())
    ])

    # Create elements list with the text run
    elements = [OrderedDict([('text_run', text_run)])]

    # Create style object
    style = OrderedDict([
        ('align', 1),
        ('folded', False),
        ('done', done)
    ])

    # Create the block
    block = OrderedDict([
        ('block_type', 17),
        ('todo', OrderedDict([
            ('elements', elements),
            ('style', style)
        ]))
    ])

    return block

def parse_table_row(row: str) -> List[str]:
    """Parse a table row into cells.

    Args:
        row (str): The table row to parse.

    Returns:
        List[str]: The list of cells in the row.
    """
    # Remove leading and trailing pipes
    row = row.strip('|')
    
    # Split by pipes and strip whitespace
    cells = [cell.strip() for cell in row.split('|')]
    
    return cells

def convert_table_to_block(table_rows: List[str]) -> Tuple[OrderedDict, int]:
    """Convert a table to a block.

    Args:
        table_rows (List[str]): The rows of the table.

    Returns:
        Tuple[OrderedDict, int]: The block representation of the table and the number of rows consumed.
    """
    if not table_rows or len(table_rows) < 3:
        return None, 0
    
    # Parse header row
    header_cells = parse_table_row(table_rows[0])
    
    # Skip separator row
    separator_row = table_rows[1]
    
    # Parse data rows
    data_rows = []
    rows_consumed = 2  # Header and separator
    
    for row in table_rows[2:]:
        if not re.match(r'\|.*\|', row):
            break
        
        cells = parse_table_row(row)
        if len(cells) != len(header_cells):
            break
        
        data_rows.append(cells)
        rows_consumed += 1
    
    # Create table cells
    table_cells = []
    
    # Add header row
    header_row = []
    for cell in header_cells:
        header_row.append(OrderedDict([
            ('text', cell)
        ]))
    table_cells.append(header_row)
    
    # Add data rows
    for row in data_rows:
        data_row = []
        for cell in row:
            data_row.append(OrderedDict([
                ('text', cell)
            ]))
        table_cells.append(data_row)
    
    # Create the block
    block = OrderedDict([
        ('block_type', 31),
        ('table', OrderedDict([
            ('cells', table_cells)
        ]))
    ])
    
    return block, rows_consumed

def process_list_items(items, depth=0, ordered=False, parent_id=None):
    block_ids = []
    for item in items:
        block_id = get_next_block_id()
        if parent_id is None:
            result['children_id'].append(block_id)

        # Get content from block_text
        content = ''
        children_ids = []
        for child in item['children']:
            if child['type'] == 'block_text':
                content = child['children'][0]['raw']
            elif child['type'] == 'list':
                child_ids = process_list_items(
                    child['children'], 
                    depth + 1, 
                    child.get('attrs', {}).get('ordered', False),
                    block_id
                )
                children_ids.extend(child_ids)  # 收集子项的 ID

        # Create block
        block_type = 13 if ordered else 12  # 13 for ordered, 12 for bullet
        list_type = 'ordered' if ordered else 'bullet'
        sequence = '1' if ordered and depth == 0 else 'auto' if ordered else None

        block = OrderedDict([
            ('block_type', block_type),
            ('block_id', block_id),
            (list_type, OrderedDict([
                ('elements', [OrderedDict([('text_run', create_text_run(content))])]),
                ('style', create_block_style(sequence))
            ]))
        ])

        if children_ids:
            block['children'] = [str(child_id) for child_id in children_ids]

        result['descendants'].append(block)
        block_ids.append(block_id)

    return block_ids

def create_text_style(bold: bool = False, italic: bool = False, inline_code: bool = False,
                   strikethrough: bool = False, underline: bool = False, link: str = None) -> OrderedDict:
    """Create text style object with all properties."""
    style = OrderedDict([
        ("bold", bold),
        ("italic", italic),
        ("inline_code", inline_code),
        ("strikethrough", strikethrough),
        ("underline", underline)
    ])
    if link:
        style["link"] = OrderedDict([("url", link)])
    return style

def process_escape_characters(text: str) -> str:
    """Process escape characters in text."""
    result = ""
    i = 0
    while i < len(text):
        if text[i] == '\\' and i + 1 < len(text):
            next_char = text[i + 1]
            if next_char in ['\\', '*', '_', '`', '#']:
                result += text[i:i+2]
                i += 2
                continue
        result += text[i]
        i += 1
    return result

def convert_text_to_block(text: str, block_id: int) -> OrderedDict:
    """Convert text to block with proper styles."""
    block = OrderedDict([
        ("block_type", 2),
        ("block_id", str(block_id)),
        ("text", OrderedDict([
            ("elements", []),
            ("style", OrderedDict([
                ("align", 1),
                ("folded", False)
            ]))
        ]))
    ])
    
    # 处理转义字符
    text = process_escape_characters(text)
    
    # 解析文本样式
    i = 0
    current_text = ""
    while i < len(text):
        if text[i:i+2] == '**':  # 粗体
            if current_text:
                block["text"]["elements"].append(OrderedDict([
                    ("text_run", OrderedDict([
                        ("content", current_text),
                        ("text_element_style", create_text_element_style())
                    ]))
                ]))
                current_text = ""
            i += 2
            bold_text = ""
            while i < len(text) and text[i:i+2] != '**':
                bold_text += text[i]
                i += 1
            i += 2
            block["text"]["elements"].append(OrderedDict([
                ("text_run", OrderedDict([
                    ("content", bold_text),
                    ("text_element_style", create_text_element_style(bold=True))
                ]))
            ]))
        elif text[i:i+1] == '*':  # 斜体
            if current_text:
                block["text"]["elements"].append(OrderedDict([
                    ("text_run", OrderedDict([
                        ("content", current_text),
                        ("text_element_style", create_text_element_style())
                    ]))
                ]))
                current_text = ""
            i += 1
            italic_text = ""
            while i < len(text) and text[i:i+1] != '*':
                italic_text += text[i]
                i += 1
            i += 1
            block["text"]["elements"].append(OrderedDict([
                ("text_run", OrderedDict([
                    ("content", italic_text),
                    ("text_element_style", create_text_element_style(italic=True))
                ]))
            ]))
        elif text[i:i+2] == '~~':  # 删除线
            if current_text:
                block["text"]["elements"].append(OrderedDict([
                    ("text_run", OrderedDict([
                        ("content", current_text),
                        ("text_element_style", create_text_element_style())
                    ]))
                ]))
                current_text = ""
            i += 2
            strike_text = ""
            while i < len(text) and text[i:i+2] != '~~':
                strike_text += text[i]
                i += 1
            i += 2
            block["text"]["elements"].append(OrderedDict([
                ("text_run", OrderedDict([
                    ("content", strike_text),
                    ("text_element_style", create_text_element_style(strikethrough=True))
                ]))
            ]))
        elif text[i:i+1] == '`':  # 行内代码
            if current_text:
                block["text"]["elements"].append(OrderedDict([
                    ("text_run", OrderedDict([
                        ("content", current_text),
                        ("text_element_style", create_text_element_style())
                    ]))
                ]))
                current_text = ""
            i += 1
            code_text = ""
            while i < len(text) and text[i:i+1] != '`':
                code_text += text[i]
                i += 1
            i += 1
            block["text"]["elements"].append(OrderedDict([
                ("text_run", OrderedDict([
                    ("content", code_text),
                    ("text_element_style", create_text_element_style(inline_code=True))
                ]))
            ]))
        elif text[i:i+1] == '[':  # 链接
            link_start = i
            while i < len(text) and text[i] != ']':
                i += 1
            if i < len(text) and text[i+1:i+2] == '(':
                link_text = text[link_start+1:i]
                i += 2
                url_start = i
                while i < len(text) and text[i] != ')':
                    i += 1
                url = text[url_start:i]
                i += 1
                if current_text:
                    block["text"]["elements"].append(OrderedDict([
                        ("text_run", OrderedDict([
                            ("content", current_text),
                            ("text_element_style", create_text_element_style())
                        ]))
                    ]))
                    current_text = ""
                block["text"]["elements"].append(OrderedDict([
                    ("text_run", OrderedDict([
                        ("content", link_text),
                        ("text_element_style", create_text_element_style(link=url, underline=False))
                    ]))
                ]))
            else:
                current_text += text[link_start]
                i = link_start + 1
        else:
            current_text += text[i]
            i += 1
    
    if current_text:
        block["text"]["elements"].append(OrderedDict([
            ("text_run", OrderedDict([
                ("content", current_text),
                ("text_element_style", create_text_element_style())
            ]))
        ]))
    
    return block

def convert_heading_to_block(node: Dict[str, Any], block_id: str) -> OrderedDict:
    """Convert heading AST node to block."""
    # In mistune 3.x, heading depth is stored in 'attrs'
    level = node['attrs']['level']
    # Text content is stored in 'raw' field of text nodes
    content = ''.join(child['raw'] for child in node['children'])
    block_type = 3 if level == 1 else 4
    heading_type = 'heading1' if level == 1 else 'heading2'
    
    return OrderedDict([
        ('block_type', block_type),
        ('block_id', block_id),
        (heading_type, OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', content),
                        ('text_element_style', create_text_element_style())
                    ]))
                ])
            ]),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False)
            ]))
        ]))
    ])

def convert_paragraph_to_block(node: Dict[str, Any], block_id: str) -> OrderedDict:
    """Convert paragraph AST node to block."""
    # Text content is stored in 'raw' field of text nodes
    content = ''.join(child['raw'] for child in node['children'])
    return OrderedDict([
        ('block_type', 2),
        ('block_id', block_id),
        ('text', OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', content),
                        ('text_element_style', create_text_element_style())
                    ]))
                ])
            ]),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False)
            ]))
        ]))
    ])

def convert_code_to_block(code: str, language: str = None) -> Tuple[OrderedDict, int]:
    """Convert code to a Lark Doc block.

    Args:
        code: The code content.
        language: The programming language.

    Returns:
        Tuple containing the code block and the number of lines consumed.
    """
    # Map programming languages to their IDs
    language_map = {
        'python': 49,
        'javascript': 30,
        None: 1
    }
    language_id = language_map.get(language, 1)

    elements = []
    lines = code.splitlines()
    lines_consumed = len(lines) + 2  # Code lines plus the ``` markers

    for line in lines:
        elements.append(OrderedDict([
            ('text_run', OrderedDict([
                ('content', line),
                ('text_element_style', create_text_element_style())
            ]))
        ]))
    return OrderedDict([
        ('block_type', 14),
        ('code', OrderedDict([
            ('elements', elements),
            ('style', OrderedDict([
                ('language', language_id),
                ('wrap', False)
            ]))
        ]))
    ]), lines_consumed

def convert_quote_to_block(text: str) -> OrderedDict:
    """Convert quote text to block with proper nesting."""
    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        line = re.sub(r'^>\s*', '', line)
        processed_lines.append(line)
    
    block = OrderedDict([
        ("block_type", 34),
        ("quote_container", OrderedDict()),
        ("children", [])
    ])
    
    text_block = OrderedDict([
        ("block_type", 2),
        ("text", OrderedDict([
            ("elements", []),
            ("style", OrderedDict([
                ("align", 1),
                ("folded", False)
            ]))
        ]))
    ])
    
    for line in processed_lines:
        line_block = convert_text_to_block(line, 0)
        text_block["text"]["elements"].extend(line_block["text"]["elements"])
    
    block["children"].append(text_block)
    
    return block

def merge_text_blocks(blocks: List[OrderedDict]) -> List[OrderedDict]:
    """Merge consecutive text blocks while preserving empty lines."""
    if not blocks:
        return blocks
    
    result = []
    i = 0
    while i < len(blocks):
        if blocks[i]["block_type"] != 2:
            result.append(blocks[i])
            i += 1
            continue
        
        current_block = blocks[i]
        if not current_block.get("text", {}).get("elements"):
            result.append(current_block)
            i += 1
            continue
            
        current_is_empty = not current_block["text"]["elements"][0]["text_run"]["content"]
        
        if current_is_empty and i + 1 < len(blocks) and blocks[i + 1]["block_type"] == 2:
            next_block = blocks[i + 1]
            if not next_block.get("text", {}).get("elements"):
                result.append(current_block)
                i += 1
                continue
                
            next_is_empty = not next_block["text"]["elements"][0]["text_run"]["content"]
            
            if next_is_empty:
                i += 1
                continue
        
        while i + 1 < len(blocks) and blocks[i + 1]["block_type"] == 2:
            next_block = blocks[i + 1]
            if not next_block.get("text", {}).get("elements"):
                break
                
            next_is_empty = not next_block["text"]["elements"][0]["text_run"]["content"]
            
            if next_is_empty or current_is_empty:
                break
            
            current_block["text"]["elements"].extend(next_block["text"]["elements"])
            i += 1
        
        result.append(current_block)
        i += 1
    
    return result

def is_child_block(child_block, parent_block):
    # Get indentation levels
    child_indent = get_block_indent(child_block)
    parent_indent = get_block_indent(parent_block)
    
    # Child must have greater indentation
    if child_indent <= parent_indent:
        return False
        
    # Check for no intermediate blocks with same or lower indentation
    for block in blocks[blocks.index(parent_block)+1:blocks.index(child_block)]:
        block_indent = get_block_indent(block)
        if block_indent <= parent_indent:
            return False
            
    return True

def get_block_indent(block):
    # Get content based on block type
    content = ""
    if block["block_type"] == 12:  # Bullet list
        content = block["bullet"]["elements"][0]["text_run"]["content"]
    elif block["block_type"] == 13:  # Ordered list
        content = block["ordered"]["elements"][0]["text_run"]["content"]
    else:
        return 0
        
    # Count leading spaces
    match = re.match(r'^\s*', content)
    return len(match.group(0)) if match else 0

def is_top_level_block(block, blocks):
    # Check if any previous block could be this block's parent
    for prev_block in blocks[:blocks.index(block)]:
        if is_child_block(block, prev_block):
            return False
    return True

def convert_markdown_to_blocks(markdown_text):
    """Convert markdown text to blocks.

    Args:
        markdown_text (str): The markdown text to convert.

    Returns:
        OrderedDict: The block representation of the markdown.
    """
    # Parse markdown using mistune
    tokens = mistune.markdown(markdown_text, True, 'ast')
    print("Parsed tokens:", tokens)  # Debug print
    
    # Initialize the result structure
    result = OrderedDict([
        ('children_id', []),
        ('descendants', [])
    ])
    
    # 用于生成唯一的 block_id
    block_id_counter = 1
    
    def get_next_block_id():
        nonlocal block_id_counter
        block_id = str(block_id_counter)
        block_id_counter += 1
        return block_id
    
    # 按顺序处理每个顶级节点
    for i, node in enumerate(tokens):
        # 处理标题
        if node['type'] == 'heading':
            block_id = get_next_block_id()
            result['children_id'].append(block_id)
            
            level = node['attrs']['level']
            content = ''.join([child['raw'] for child in node['children']])
            
            if level == 1:
                block_type = 3
                heading_type = 'heading1'
            elif level == 2:
                block_type = 4
                heading_type = 'heading2'
            elif level == 3:
                block_type = 5
                heading_type = 'heading3'
            else:
                # 默认为段落
                block_type = 2
                heading_type = 'text'
            
            # 创建标题块
            block = OrderedDict([
                ('block_type', block_type),
                ('block_id', block_id),
                (heading_type, OrderedDict([
                    ('elements', [
                        OrderedDict([
                            ('text_run', OrderedDict([
                                ('content', content),
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
            ])
            
            result['descendants'].append(block)
            
            # 只在非最后一个标题后添加空行
            # 检查是否是最后一个节点
            is_last_node = i == len(tokens) - 1
            # 检查是否是 H3 标题
            is_h3_heading = level == 3
            
            # 如果不是最后一个节点或者不是 H3 标题，则添加空行
            if not (is_last_node and is_h3_heading):
                block_id = get_next_block_id()
                result['children_id'].append(block_id)
                
                empty_block = OrderedDict([
                    ('block_type', 2),
                    ('block_id', block_id),
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
                ])
                
                result['descendants'].append(empty_block)
        
        # 处理段落
        elif node['type'] == 'paragraph':
            block_id = get_next_block_id()
            result['children_id'].append(block_id)
            
            content = ''.join([child['raw'] for child in node['children']])
            
            block = OrderedDict([
                ('block_type', 2),
                ('block_id', block_id),
                ('text', OrderedDict([
                    ('elements', [
                        OrderedDict([
                            ('text_run', OrderedDict([
                                ('content', content),
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
            ])
            
            result['descendants'].append(block)
            
        # TODO: 处理其他类型的块，如列表、代码块等
    
    return result

def create_text_block(content: str) -> OrderedDict:
    """Create a text block with the given content.

    Args:
        content: The text content.

    Returns:
        An OrderedDict containing the text block structure.
    """
    return OrderedDict([
        ('block_type', 2),
        ('text', OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', content),
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
    ])

def create_text_run(content: str, style: OrderedDict = None) -> OrderedDict:
    """Create text run with proper order."""
    if style is None:
        style = create_text_element_style()
    return OrderedDict([
        ("text_run", OrderedDict([
            ("content", content),
            ("text_element_style", style),
        ])),
    ])

def create_text_element_style(
    bold: bool = False,
    italic: bool = False,
    inline_code: bool = False,
    strikethrough: bool = False,
    underline: bool = False,
    link: str = None,
) -> OrderedDict:
    """Create text element style with proper order."""
    style = OrderedDict([
        ("bold", bold),
        ("inline_code", inline_code),
        ("italic", italic),
    ])
    if link:
        style["link"] = OrderedDict([("url", urllib.parse.quote(link, safe=''))])
    style.update([
        ("strikethrough", strikethrough),
        ("underline", underline),
    ])
    return style

def create_block_style(align: int = 1, folded: bool = False) -> OrderedDict:
    """Create block style with proper order."""
    return OrderedDict([
        ("align", align),
        ("folded", folded)
    ])

def create_heading_block(content: str, level: int = 1) -> OrderedDict:
    """Create a heading block with the given content and level.

    Args:
        content: The heading text content.
        level: The heading level (1 or 2).

    Returns:
        An OrderedDict containing the heading block structure.
    """
    block_type = 3 if level == 1 else 4
    heading_type = 'heading1' if level == 1 else 'heading2'
    
    return OrderedDict([
        ('block_type', block_type),
        (heading_type, OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', content),
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
    ])

def convert_bullet_list_to_block(text: str, block_id: int) -> OrderedDict:
    """Convert bullet list item to block."""
    # Remove bullet marker and get content
    content = re.sub(r'^(\s*)[*+-]\s+', '', text)
    
    block = OrderedDict([
        ("block_type", 12),
        ("block_id", str(block_id)),
        ("bullet", OrderedDict([
            ("elements", [OrderedDict([
                ("text_run", OrderedDict([
                    ("content", content),
                    ("text_element_style", create_text_style())
                ]))
            ])]),
            ("style", OrderedDict([
                ("align", 1),
                ("folded", False)
            ]))
        ]))
    ])
    
    return block

def convert_ordered_list_to_block(text: str, block_id: int) -> OrderedDict:
    """Convert ordered list item to block."""
    # Remove number marker
    content = re.sub(r'^\d+\.\s+', '', text)
    
    return OrderedDict([
        ('block_type', 13),
        ('block_id', str(block_id)),
        ('ordered', OrderedDict([
            ('elements', [
                OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', content),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('italic', False),
                            ('inline_code', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ])
            ]),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False),
                ('sequence', 'auto')
            ]))
        ]))
    ])

def convert_list_to_blocks(node: Dict[str, Any], start_block_id: int, block_parents: Dict[str, str], block_children: Dict[str, List[str]]) -> List[OrderedDict]:
    """Convert list AST node to blocks."""
    blocks = []
    current_block_id = start_block_id
    list_type = 'bullet' if not node['attrs'].get('ordered', False) else 'ordered'
    
    def process_list_item(item: Dict[str, Any], parent_id: Optional[str] = None) -> str:
        nonlocal current_block_id
        block_id = str(current_block_id)
        current_block_id += 1
        
        # Get text content from the block_text node
        content = ''.join(child['raw'] for child in item['children'][0]['children'])
        
        block = OrderedDict([
            ('block_type', 12 if list_type == 'bullet' else 13),
            ('block_id', block_id),
            (list_type, OrderedDict([
                ('elements', [
                    OrderedDict([
                        ('text_run', OrderedDict([
                            ('content', content),
                            ('text_element_style', create_text_element_style())
                        ]))
                    ])
                ]),
                ('style', OrderedDict([
                    ('align', 1),
                    ('folded', False)
                ]))
            ]))
        ])
        
        # Add sequence for ordered lists
        if list_type == 'ordered':
            block[list_type]['style']['sequence'] = '1'
        
        blocks.append(block)
        
        # Process child list if any
        for child in item['children']:
            if child['type'] == 'list':
                child_list = child
                child_ids = []
                for child_item in child_list['children']:
                    child_id = process_list_item(child_item, block_id)
                    child_ids.append(child_id)
                if child_ids:
                    block_children[block_id] = child_ids
                    for child_id in child_ids:
                        block_parents[child_id] = block_id
        
        # Set parent relationship
        if parent_id:
            block_parents[block_id] = parent_id
        
        return block_id
    
    # Process all items in the list
    for item in node['children']:
        process_list_item(item)
    
    return blocks