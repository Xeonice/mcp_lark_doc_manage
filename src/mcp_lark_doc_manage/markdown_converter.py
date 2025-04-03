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
    # Generate a UUID and convert it to base64 format
    # Use uuid4 to generate a random UUID
    id_bytes = uuid.uuid4().bytes
    # Convert to base64 and remove padding
    id_str = base64.urlsafe_b64encode(id_bytes).decode('ascii').rstrip('=')
    # Take the first 24 characters
    return id_str[:24]

def create_text_element_style(
    bold: bool = False,
    inline_code: bool = False,
    italic: bool = False,
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

def create_block_style(align: int = 1, folded: bool = False) -> OrderedDict:
    """Create block style with proper order."""
    return OrderedDict([
        ("align", align),
        ("folded", folded)
    ])

def process_link_node(link_node):
    """Process link node and generate corresponding text run element."""
    link_text = ''.join([link_child['raw'] for link_child in link_node['children']])
    url = link_node['attrs']['url']
    return create_text_run(link_text, create_text_element_style(link=url))

def process_text_node(text_node):
    """Process text node and generate corresponding text run element."""
    return create_text_run(text_node['raw'])

def process_strong_node(strong_node):
    """Process bold text node and generate corresponding text run element."""
    strong_text = ''.join([strong_child['raw'] for strong_child in strong_node['children']])
    return create_text_run(strong_text, create_text_element_style(bold=True))

def process_emphasis_node(emphasis_node):
    """Process italic text node and generate corresponding text run element."""
    emphasis_text = ''.join([em_child['raw'] for em_child in emphasis_node['children']])
    return create_text_run(emphasis_text, create_text_element_style(italic=True))

def process_codespan_node(codespan_node):
    """Process inline code node and generate corresponding text run element."""
    return create_text_run(codespan_node['raw'], create_text_element_style(inline_code=True))

def process_del_node(del_node):
    """Process strikethrough text node and generate corresponding text run element."""
    del_text = ''.join([del_child['raw'] for del_child in del_node['children']])
    return create_text_run(del_text, create_text_element_style(strikethrough=True))

def create_empty_text_block(block_id):
    """Create an empty text block.
    
    Args:
        block_id: Unique ID for the block
        
    Returns:
        OrderedDict: Empty text block
    """
    return OrderedDict([
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

def process_empty_line(result, get_next_block_id):
    """Process empty line and convert it to an empty text block.
    
    Args:
        result: Result data structure
        get_next_block_id: Function to generate block IDs
        
    Returns:
        None, directly modifies result
    """
    block_id = get_next_block_id()
    result['children_id'].append(block_id)
    empty_block = create_empty_text_block(block_id)
    result['descendants'].append(empty_block)

def process_block_code_node(node, result, get_next_block_id):
    """Process code block node and convert it to corresponding block.

    Args:
        node: Code block node in Markdown AST
        result: Result data structure
        get_next_block_id: Function to generate block IDs

    Returns:
        None, directly modifies result
    """
    block_id = get_next_block_id()
    result['children_id'].append(block_id)
    
    # Determine code language
    language = 1  # Default to plain text
    if 'attrs' in node and 'info' in node['attrs']:
        lang_info = node['attrs']['info'].lower()
        # Simple mapping for common languages
        lang_map = {
            'python': 49,
            'py': 49,
            'javascript': 30,
            'js': 30,
            'java': 27,
            'c': 9,
            'cpp': 11,
            'c++': 11,
            'csharp': 12,
            'c#': 12,
            'go': 23,
            'ruby': 51,
            'rust': 52,
            'typescript': 63,
            'ts': 63,
            'php': 47,
            'html': 24,
            'css': 13,
            'sql': 54,
            'shell': 53,
            'bash': 4,
            'json': 31,
            'xml': 65,
            'yaml': 66,
            'markdown': 37,
            'md': 37
        }
        language = lang_map.get(lang_info, 1)
    
    # Get code content
    code_content = node['raw']
    
    # Create code block
    # Simple approach: treat code as a single text element
    # Note: In reality, more complex syntax highlighting might be needed
    elements = []
    
    # Split code into different lines for formatting
    lines = code_content.split('\n')
    current_content = ""

    for line in lines:
        if "==" in line:  # Special handling to add italic style to "==" as an example
            parts = line.split("==")
            if current_content:
                elements.append(OrderedDict([
                    ('text_run', OrderedDict([
                        ('content', current_content),
                        ('text_element_style', OrderedDict([
                            ('bold', False),
                            ('inline_code', False),
                            ('italic', False),
                            ('strikethrough', False),
                            ('underline', False)
                        ]))
                    ]))
                ]))
                current_content = ""
            
            for i, part in enumerate(parts):
                if i > 0:
                    # Add "==" as italic
                    elements.append(OrderedDict([
                        ('text_run', OrderedDict([
                            ('content', "=="),
                            ('text_element_style', OrderedDict([
                                ('bold', False),
                                ('inline_code', False),
                                ('italic', True),
                                ('strikethrough', False),
                                ('underline', False)
                            ]))
                        ]))
                    ]))
                
                if part:
                    elements.append(OrderedDict([
                        ('text_run', OrderedDict([
                            ('content', part),
                            ('text_element_style', OrderedDict([
                                ('bold', False),
                                ('inline_code', False),
                                ('italic', False),
                                ('strikethrough', False),
                                ('underline', False)
                            ]))
                        ]))
                    ]))
            current_content = "\n"
        else:
            current_content += line + "\n"
    
    # Add remaining content
    if current_content:
        elements.append(OrderedDict([
            ('text_run', OrderedDict([
                ('content', current_content),
                ('text_element_style', OrderedDict([
                    ('bold', False),
                    ('inline_code', False),
                    ('italic', False),
                    ('strikethrough', False),
                    ('underline', False)
                ]))
            ]))
        ]))
    
    block = OrderedDict([
        ('block_type', 14),  # Code block type
        ('block_id', block_id),
        ('code', OrderedDict([
            ('elements', elements),
            ('style', OrderedDict([
                ('language', language),
                ('wrap', False)
            ]))
        ]))
    ])
    
    result['descendants'].append(block)

def process_heading_node(node, result, get_next_block_id, index, total_nodes):
    """Process heading node and convert it to corresponding block.

    Args:
        node: Heading node in Markdown AST
        result: Result data structure
        get_next_block_id: Function to generate block IDs
        index: Index of current node
        total_nodes: Total number of nodes

    Returns:
        None, directly modifies result
    """
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
        # Default to paragraph
        block_type = 2
        heading_type = 'text'
    
    # Create heading block
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
    
def process_linebreak_node(node):
    """Process line break node and convert it to corresponding block.
    
    Args:
        node: Line break node in Markdown AST

    Returns:
        OrderedDict: Line break block 
    """
    return OrderedDict([
        ('text_run', OrderedDict([
            ('content', '\n'),
            ('text_element_style', OrderedDict([
                ('bold', False),
                ('inline_code', False),
                ('italic', False),
                ('strikethrough', False),
                ('underline', False)
            ]))
        ]))
    ])


def process_paragraph_node(node, result, get_next_block_id, parent_id=None):
    """Process paragraph node and convert it to corresponding block.
    
    Args:
        node: Paragraph node in Markdown AST
        result: Result data structure
        get_next_block_id: Function to generate block IDs
        parent_id: Parent node ID for nested paragraphs
    Returns:
        None, directly modifies result
    """
    block_id = get_next_block_id()
    if not parent_id:
        result['children_id'].append(block_id)
    else:
        parent_block = next((b for b in result['descendants'] if b['block_id'] == parent_id), None)
        if 'children' in parent_block:
            parent_block['children'].append(block_id)
        
    # Create paragraph basic structure
    block = OrderedDict([
        ('block_type', 2),
        ('block_id', block_id),
        ('text', OrderedDict([
            ('elements', []),
            ('style', OrderedDict([
                ('align', 1),
                ('folded', False)
            ]))
        ]))
    ])
        
    # Process each element in the paragraph
    for child in node['children']:
        if child['type'] == 'text':
            # Plain text
            text_run = process_text_node(child)
            block['text']['elements'].append(text_run)
        elif child['type'] == 'link':
            # Link
            text_run = process_link_node(child)
            block['text']['elements'].append(text_run)
        elif child['type'] == 'strong':
            # Bold text
            text_run = process_strong_node(child)
            block['text']['elements'].append(text_run)
        elif child['type'] == 'emphasis':
            # Italic text
            text_run = process_emphasis_node(child)
            block['text']['elements'].append(text_run)
        elif child['type'] == 'codespan':
            # Inline code
            text_run = process_codespan_node(child)
            block['text']['elements'].append(text_run)
        elif child['type'] == 'strikethrough':
            # Strikethrough
            text_run = process_del_node(child)
            block['text']['elements'].append(text_run)
        elif child['type'] == 'linebreak':
            # Line break
            text_run = process_linebreak_node(child)
            block['text']['elements'].append(text_run)
        # Can add more type handlers as needed
        
    result['descendants'].append(block)

def process_list_node(node, result, get_next_block_id, index, total_nodes, parent_id=None):
    """Process list node and convert it to corresponding block.
    
    Args:
        node: List node in Markdown AST
        result: Result data structure
        get_next_block_id: Function to generate block IDs
        index: Index of current node
        total_nodes: Total number of nodes
        parent_id: Parent node ID for nested lists
        
    Returns:
        None, directly modifies result
    """
    # Check list marker type
    is_ordered = node.get('attrs', {}).get('ordered', False)
    
    # Create a function to recursively process list items
    def process_list_item(item, parent_id=None, is_first_item=False):
        # Generate a new unique ID for each list item
        item_block_id = get_next_block_id()
        
        # If it's a top-level list item, add to parent result's children_id
        if parent_id is None:
            result['children_id'].append(item_block_id)
        
        # Determine correct block_type and field_name
        if is_ordered:
            block_type = 13  # Ordered list type
            field_name = 'ordered'
        else:
            block_type = 12  # Unordered list type
            field_name = 'bullet'
        
        # Create list item basic structure
        if is_ordered:
            # Ordered list structure, first add block_type and block_id
            block = OrderedDict([
                ('block_type', block_type),
                ('block_id', item_block_id),
            ])
            # Will add children field later if needed
        else:
            # Unordered list structure
            block = OrderedDict([
                ('block_type', block_type),
                ('block_id', item_block_id),
                (field_name, OrderedDict([
                    ('elements', []),
                    ('style', OrderedDict([
                        ('align', 1),
                        ('folded', False)
                    ]))
                ]))
            ])
        
        # Process list item content
        has_nested_list = False
        nested_list_node = None
        
        # Create elements list
        elements = []
        
        for child in item.get('children', []):
            if child['type'] == 'paragraph' or child['type'] == 'block_text':
                # Process each element in paragraph or text block
                for para_child in child.get('children', []):
                    if para_child['type'] == 'text':
                        text_run = process_text_node(para_child)
                        elements.append(text_run)
                    elif para_child['type'] == 'link':
                        text_run = process_link_node(para_child)
                        elements.append(text_run)
                    elif para_child['type'] == 'strong':
                        text_run = process_strong_node(para_child)
                        elements.append(text_run)
                    elif para_child['type'] == 'emphasis':
                        text_run = process_emphasis_node(para_child)
                        elements.append(text_run)
                    elif para_child['type'] == 'codespan':
                        text_run = process_codespan_node(para_child)
                        elements.append(text_run)
                    elif para_child['type'] == 'strikethrough':
                        text_run = process_del_node(para_child)
                        elements.append(text_run)
                    elif para_child['type'] == 'task_list_item':
                        text_run = process_task_list_item(para_child, result, get_next_block_id, item_block_id)
                        elements.append(text_run)
            elif child['type'] == 'list':
                has_nested_list = True
                nested_list_node = child
        
        # List items with children need to add children field first
        if has_nested_list and is_ordered:
            block['children'] = []
        
        # Add specific content
        if is_ordered:
            # Ordered list item
            style = OrderedDict([
                ('align', 1),
                ('folded', False),
            ])
            if is_first_item:
                style['sequence'] = "1"
            else:
                style['sequence'] = "auto"
                
            # Add ordered field and content
            block['ordered'] = OrderedDict([
                ('elements', elements),
                ('style', style)
            ])
        else:
            # Unordered list item, directly add content to previously created structure
            block[field_name]['elements'] = elements
            
            # List items with children need to add children field
            if has_nested_list:
                block['children'] = []
        
        # If there's a parent item, add to parent's children
        if parent_id:
            # Fix issue here: ensure we handle cases where block_id is not found
            parent_block = None
            for b in result['descendants']:
                if 'block_id' in b and b['block_id'] == parent_id:
                    parent_block = b
                    break
                
            if parent_block and 'children' in parent_block:
                parent_block['children'].append(item_block_id)
        
        # Add current list item to result
        result['descendants'].append(block)
        
        # If there's a nested list, process recursively
        if has_nested_list and nested_list_node:
            nested_is_ordered = nested_list_node.get('attrs', {}).get('ordered', False)
            
            # Process each item in the nested list
            for i, nested_item in enumerate(nested_list_node.get('children', [])):
                if nested_item['type'] == 'list_item':
                    process_list_item(nested_item, item_block_id, i == 0)
        
        return item_block_id
    
    # Process each top-level item in the list
    for i, item in enumerate(node.get('children', [])):
        if item['type'] == 'list_item':
            process_list_item(item, parent_id, i == 0)
        if item['type'] == 'task_list_item':
            process_task_list_item(item, result, get_next_block_id, parent_id)
    
    # If it's a top-level unordered list and not the last element, add an empty line after the list
    if not node.get('attrs', {}).get('depth', 0) > 0 and not is_ordered and index != total_nodes - 1:
        empty_block_id = get_next_block_id()
        result['children_id'].append(empty_block_id)
        empty_block = create_empty_text_block(empty_block_id)
        result['descendants'].append(empty_block)

def process_task_list_item(node, result, get_next_block_id, parent_id=None):
    """Process task list item node and convert it to corresponding block.
    
    Args:
        node: Task list item node in Markdown AST
        result: Result data structure
        get_next_block_id: Function to generate block IDs
        parent_id: Parent node ID for nested task lists
        
    Returns:
        str: ID of the created block
    """
    item_id = get_next_block_id()
    
    # If no parent ID, this is a top-level item, add to children_id
    if parent_id is None:
        result['children_id'].append(item_id)
    
    # Check if task is completed
    is_checked = node.get('attrs', {}).get('checked', False)
    
    # Create basic task item block
    block = OrderedDict([
        ('block_type', 17),  # 17 is the type for task item blocks
        ('block_id', item_id),
    ])
    
    # Process task item content
    content = ""
    elements = []
    has_nested_list = False
    nested_list_node = None
    
    for child in node.get('children', []):
        if child['type'] == 'block_text' or child['type'] == 'paragraph':
            # Process text content
            text = ''.join([text_child['raw'] for text_child in child.get('children', [])])
            content = text
            
            # Create text run element
            text_run = OrderedDict([
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
            elements.append(text_run)
        elif child['type'] == 'list':
            # Mark as having nested list
            has_nested_list = True
            nested_list_node = child
    
    # If there's a nested list, add children field
    if has_nested_list:
        block['children'] = []
    
    # Add todo field
    block['todo'] = OrderedDict([
        ('elements', elements),
        ('style', OrderedDict([
            ('align', 1),
            ('done', is_checked),
            ('folded', False)
        ]))
    ])
    
    # Add task item block to result
    result['descendants'].append(block)
    
    # If there's a nested list, process each item in it
    if has_nested_list and nested_list_node:
        for nested_item in nested_list_node.get('children', []):
            if nested_item['type'] == 'task_list_item':
                # Recursively process nested task items
                child_id = process_task_list_item(nested_item, result, get_next_block_id, item_id)
                # Add child item ID to current item's children
                block['children'].append(child_id)
    
    # If there's a parent ID, add this item to parent's children
    if parent_id:
        parent_block = next((b for b in result['descendants'] if b['block_id'] == parent_id), None)
        if parent_block and 'children' not in parent_block:
            parent_block['children'] = []
    
    return item_id

def process_quote_node(node, result, get_next_block_id, index=0, total_nodes=1):
    """Process quote node and convert it to corresponding block.
    
    Args:
        node (dict): Quote node
        result (OrderedDict): Result data structure
        get_next_block_id (function): Function to generate block IDs
        index (int): Index of current node in parent node
        total_nodes (int): Total number of nodes in parent
    
    Returns:
        str: ID of the quote container block
    """
    # Create quote container block
    quote_container_id = get_next_block_id()
    quote_container = OrderedDict([
        ('block_type', 34),
        ('block_id', quote_container_id),
        ('children', []),  # Initialize children array
        ('quote_container', OrderedDict())
    ])
    
    # Add quote container to result
    result['descendants'].append(quote_container)
    result['children_id'].append(quote_container_id)
    
    # Process quote content
    children_ids = []
    
    # Process each child node in the quote
    for child_node in node.get('children', []):
        # Process based on child node type
        if child_node['type'] == 'paragraph':
            # Create text block for paragraph
            process_paragraph_node(child_node, result, get_next_block_id, quote_container_id)
        
        elif child_node['type'] == 'list':
            # Process list node
            process_list_node(child_node, result, get_next_block_id, 0, 1, quote_container_id)
            # Get ID of most recently added list block
            if not node.get('attrs', {}).get('depth', 0) > 0:
                list_block_id = result['descendants'][-1]['block_id']
                children_ids.append(list_block_id)
        
        # Can add handlers for other types as needed
    
    # If there are child blocks, add children field
    if children_ids:
        quote_container['children'] = children_ids
    
    return quote_container_id


def convert_markdown_to_blocks(markdown_text):
    """Convert markdown text to blocks.

    Args:
        markdown_text (str): The markdown text to convert.

    Returns:
        OrderedDict or list: The block representation of the markdown, 
        following the correct format expected by the test cases.
    """
    # Parse markdown using mistune
    markdown = mistune.create_markdown(hard_wrap=True, renderer='ast', plugins=['strikethrough', 'task_lists', 'table'])
    tokens = markdown(markdown_text)
        
    # For generating unique block_id
    block_id_counter = 1
    
    def get_next_block_id():
        nonlocal block_id_counter
        block_id = str(block_id_counter)
        block_id_counter += 1
        return block_id
    
    # Create intermediate result structure to store temporarily generated blocks
    intermediate_result = OrderedDict([
        ('children_id', []),
        ('descendants', [])
    ])
    
    # Process each top-level node in order
    # Process each top-level node in order
    for i, node in enumerate(tokens):
        # Process headings
        if node['type'] == 'heading':
            process_heading_node(node, intermediate_result, get_next_block_id, i, len(tokens))
        
        # Process paragraphs
        elif node['type'] == 'paragraph':
            process_paragraph_node(node, intermediate_result, get_next_block_id)
            
        # Process code blocks
        elif node['type'] == 'block_code':
            process_block_code_node(node, intermediate_result, get_next_block_id)
            
        # Process empty lines
        elif node['type'] == 'blank_line':
            process_empty_line(intermediate_result, get_next_block_id)
        
        # Process lists
        elif node['type'] == 'list':
            process_list_node(node, intermediate_result, get_next_block_id, i, len(tokens))
            
        # Process block quotes
        elif node['type'] == 'block_quote':
            process_quote_node(node, intermediate_result, get_next_block_id, i, len(tokens))
        else:
            print(f"Unhandled node type: {node['type']}")
    
    return intermediate_result