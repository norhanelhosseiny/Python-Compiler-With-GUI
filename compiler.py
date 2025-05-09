import copy
import re
import tkinter as tk
from tkinter import messagebox
from binarytree import Node


setOfTokens = {
    'Reserved_Words': r'\b(if|then|else|end|repeat|until|read|write)\b',
    'Special_Symbol': r'[\+\-\*/=<>();]',
    'Assignment_Opr': r':=',
    'Comment': r'%%[a-zA-Z]+',
    'Number': r'\b\d+(\.\d+)?\b',
    'Identifier': r'\b[a-zA-Z][a-zA-Z0-9_]*\b'
}

Operator_Mapping = {
    '=': '=',
    '*': '*',
    'pi': '3.14'
}



def preprocess_expression(expression, is_source_code):
    expression = expression.replace('pi', '3.14')
    if is_source_code:
        if re.search(r'\d+[a-zA-Z]', expression):
            raise ValueError("Lexical Error! Use '*' directly in Source Code.")
    else:
        expression = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expression)
        expression = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', expression)
    return expression



def check_input(expression, is_source_code):
    if re.search(r'\+\s*$', expression) or re.search(r'\+\+', expression):
        raise ValueError("Syntax Error!")
    if re.search(r'([a-zA-Z][a-zA0-9_]*)\s*=\s*\1', expression):
        raise ValueError("Syntax Error! Self-assignment detected.")

    expression = preprocess_expression(expression, is_source_code)
    return expression


# Lexical Analysis

def tokenize_expression(expression):
    tokens = []
    position = 0
    while position < len(expression):
        match = None
        for token_type, token_pattern in setOfTokens.items():
            regex = re.compile(token_pattern)
            match = regex.match(expression, position)
            if match:
                tokens.append((token_type, match.group(0)))
                position = match.end()
                break
        if not match:
            position += 1
    return tokens


def enumerate_tokens(tokens):
    token_dict = {}
    enumerated_tokens = []
    id_counter = 1
    for token_type, token_value in tokens:
        if token_type == 'Identifier':
            if token_value not in token_dict:
                token_dict[token_value] = f'id{id_counter}'
                id_counter += 1
            enumerated_tokens.append((token_type, token_dict[token_value]))
        else:
            enumerated_tokens.append((token_type, token_value))
    return enumerated_tokens


#Syntax Analysis

def build_parse_tree(tokens):
    if len(tokens) < 3 or tokens[1][1] != '=':
        raise ValueError("Invalid syntax!")

    root = Node('=')

    left_child = Node(tokens[0][1])

    right_child = build_expression_tree(tokens[2:])
    root.left = left_child
    root.right = right_child

    return root


def build_expression_tree(tokens):
    if len(tokens) == 1:
        return Node(tokens[0][1])

    operator = tokens[1][1]
    root = Node(operator)


    left_child = build_expression_tree(tokens[:1])
    right_child = build_expression_tree(tokens[2:])

    root.left = left_child
    root.right = right_child

    return root


#Semantic Analysis

def semantic_analyzer(node, is_float):
    if node.left is None and node.right is None:
        try:
            value = int(node.value)
            if is_float:
                node.value = f"inttofloat({value})"
        except ValueError:
            pass
    else:
        if node.left:
            semantic_analyzer(node.left, is_float)
        if node.right:
            semantic_analyzer(node.right, is_float)


def format_enumerated_tokens(enumerated_tokens):
    formatted_expression = ""
    for token_type, token_value in enumerated_tokens:
        formatted_expression += token_value + " "
    return formatted_expression.strip()



#ICG

def generate_intermediate_code(parse_tree, is_float):
    temp_counter = 1
    intermediate_code = []

    def traverse(node):
        nonlocal temp_counter
        if node.left is None and node.right is None:  # Leaf node
            return node.value

        left = traverse(node.left)
        right = traverse(node.right)

        if node.value == '*':
            temp_var = f'temp{temp_counter}'
            temp_counter += 1
            if is_float:
                intermediate_code.append(f'{temp_var}=inttofloat({right})')
            else:
                intermediate_code.append(f'{temp_var}={right}')
            result_var = f'temp{temp_counter}'
            temp_counter += 1
            intermediate_code.append(f'{result_var}={left}*{temp_var}')
            return result_var

        if node.value == '+':
            result_var = f'temp{temp_counter}'
            temp_counter += 1
            intermediate_code.append(f'{result_var}={left}+{right}')
            return result_var

    result = traverse(parse_tree.right)
    intermediate_code.append(f'{parse_tree.left.value}={result}')

    return '\n'.join(intermediate_code)



#Code Optimizer

def optimize_code(enumerated_expression, is_float):
    tokens = enumerated_expression.split()
    optimized_code = []
    temp_counter = 1


    if len(tokens) < 3 or tokens[1] != '=':
        raise ValueError("Invalid expression!")

    result_variable = tokens[0]
    expression_tokens = tokens[2:]

    def process_expression(expr_tokens):
        nonlocal temp_counter
        if len(expr_tokens) == 1:

            if is_float and re.match(r'^\d+(\.\d+)?$', expr_tokens[0]):
                token = expr_tokens[0]
                return f"{token}.0" if '.' not in token else token
            return expr_tokens[0]


        operator_index = None
        for i, token in enumerate(expr_tokens):
            if token in ('+', '-', '*', '/'):
                operator_index = i
                break

        if operator_index is None:
            raise ValueError("Invalid expression structure!")

        left_operand = process_expression(expr_tokens[:operator_index])
        right_operand = process_expression(expr_tokens[operator_index + 1:])
        operator = expr_tokens[operator_index]

        temp_var = f"temp{temp_counter}"
        temp_counter += 1

        optimized_code.append(f"{temp_var}={left_operand}{operator}{right_operand}")
        return temp_var


    final_temp = process_expression(expression_tokens)
    optimized_code.append(f"{result_variable}={final_temp}")

    return '\n'.join(optimized_code)



#Code Generator

def code_generator(enumerated_expression, is_float):
    instructions = []
    tokens = enumerated_expression.split()


    if len(tokens) < 3 or tokens[1] != '=':
        raise ValueError("Invalid expression! Expected format: id = expression")

    result_variable = tokens[0]
    expression_tokens = tokens[2:]

    def load_operand(operand, register):
        if operand.startswith('id'):  #Variable
            if is_float:
                instructions.append(f"LDF {register}, {operand}")
            else:
                instructions.append(f"LD {register}, {operand}")
        elif operand.isdigit():  #Constant
            if is_float:
                instructions.append(f"LDF {register}, #{operand}")
            else:
                instructions.append(f"LD {register}, #{operand}")

    def process_expression(expr_tokens):

        if len(expr_tokens) == 3:
            left_operand, operator, right_operand = expr_tokens
            load_operand(right_operand, 'R2')
            load_operand(left_operand, 'R1')
            if operator == '+':
                instructions.append(f"{'ADDF' if is_float else 'ADD'} R1, R1, R2")
            elif operator == '*':
                instructions.append(f"{'MULF' if is_float else 'MUL'} R1, R1, R2")
            return 'R1'

        if len(expr_tokens) == 5:
            left_operand, operator1, mid_operand, operator2, right_operand = expr_tokens
            load_operand(mid_operand, 'R2')
            if operator2 == '*':
                instructions.append(f"{'MULF' if is_float else 'MUL'} R2, R2, #{right_operand}")
            load_operand(left_operand, 'R1')
            if operator1 == '+':
                instructions.append(f"{'ADDF' if is_float else 'ADD'} R1, R1, R2")
            elif operator1 == '-':
                instructions.append(f"{'SUBF' if is_float else 'SUB'} R1, R1, R2")
            return 'R1'

        raise ValueError("Unsupported expression structure!")


    process_expression(expression_tokens)


    instructions.append(f"STR{'F' if is_float else ''} {result_variable}, R1")

    return '\n'.join(instructions)




#Output

def handle_submit():
    try:
        expr = entry_expr.get()
        is_source_code = var_code_or_math.get() == "source_code"
        is_float = var_type.get() == "float"

        checked_expr = check_input(expr, is_source_code)
        tokens = tokenize_expression(checked_expr)

        enumerated_tokens = enumerate_tokens(tokens)

        parse_tree = build_parse_tree(enumerated_tokens)

        parse_tree_semantic = copy.deepcopy(parse_tree)

        semantic_analyzer(parse_tree_semantic, is_float)

        intermediate_code = generate_intermediate_code(parse_tree, is_float)

        enumerated_expression = format_enumerated_tokens(enumerated_tokens)

        optimized_code = optimize_code(enumerated_expression, is_float)

        assembly_code = code_generator(enumerated_expression, is_float)


        parse_tree_str = str(parse_tree)
        parse_tree_semantic_str = str(parse_tree_semantic)


        result.set(
            f"Source Code:\n{checked_expr}\n\nLexical Analyzer:\n{enumerated_expression}\n\n"
            f"Parse Tree (Syntax Analyzer):\n{parse_tree_str}\n\n"
            f"Parse Tree (Semantic Analyzer):\n{parse_tree_semantic_str}\n\n"
            f"Intermediate Code Generator:\n{intermediate_code}\n\n"
            f"Code Optimizer:\n{optimized_code}\n\n"
            f"Code Generation:\n{assembly_code}"
        )

    except ValueError as e:
        messagebox.showerror("Error", str(e))




#Create the main application window
root = tk.Tk()
root.title("Compiler Program")

#Create the GUI elements
label_expr = tk.Label(root, text="Enter Expression:")
label_expr.pack()

entry_expr = tk.Entry(root, width=50)
entry_expr.pack()

var_code_or_math = tk.StringVar(value="source_code")
radio_source_code = tk.Radiobutton(root, text="Source Code", variable=var_code_or_math, value="source_code")
radio_math_form = tk.Radiobutton(root, text="Math Form", variable=var_code_or_math, value="math_form")
radio_source_code.pack()
radio_math_form.pack()

var_type = tk.StringVar(value="int")
radio_int = tk.Radiobutton(root, text="Integer", variable=var_type, value="int")
radio_float = tk.Radiobutton(root, text="Float", variable=var_type, value="float")
radio_int.pack()
radio_float.pack()

button_submit = tk.Button(root, text="Submit", command=handle_submit)
button_submit.pack()

result = tk.StringVar()
label_result = tk.Label(root, textvariable=result, justify=tk.LEFT)
label_result.pack()


root.mainloop()
