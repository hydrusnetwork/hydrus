#made by prkc for Hydrus Network
#Licensed under the same terms as Hydrus Network

"""
Accepted operators: not (!, -), and (&&), or (||), implies (=>), xnor (iff, <=>), nand, nor.
Parentheses work the usual way. \ can be used to escape characters (eg. to search for tags including parentheses)
The usual precedence rules apply.
ValueErrors are thrown with a message on syntax/parser errors.

Some test inputs:
a or b
a OR b
a and b
not a
a implies b
a xor b
a nor b
a nand b
a xnor b
(a && b) and not (a xor !b)
blah blah blah and another_long_tag_241245!
a_and_b
test!
!test
aaaaa_\(bbb ccc \(\)\) and not x
(a || b) and c and d and e or f and x or not (y or k or z and (h or i or j or t and f))
"""

import re

#Generates tokens for the parser. Consumes the input string.
#As opposed to most lexers it doesn't split on spaces.
#In fact, it tries to avoid splitting when possible by only splitting on logical operators or parentheses.
#Lowercase input is assumed.
#Contains some special handling for:
# * escapes with the \ character (escaping any character is valid). 'a \or b' is parsed as a single tag 'a or b'.
# * to allow tags ending with ! and other special chars without escaping. '!a' is negation of 'a' but 'a!' is just a tag.
#Returns a token and the remaining (unconsumed) input
def next_token(src):
    def check_tag_end(src):
        if re.match(r"\s(and|or|implies|xor|nor|nand|xnor|iff)", src): return True
        if re.match(r"&&|\|\||=>|<=>|\)|\(", src): return True
        return False

    src = src.strip()
    if len(src) == 0: return ("end", None), ""

    escape = False
    if src[0] == '\\' and len(src) > 1:
        escape = True
        src = src[1:]

    if not escape:
        if src.startswith(("!","-")):
            return ("not", None), src[1:]
        if src.startswith("&&"):
            return ("and", None), src[2:]
        if src.startswith("||"):
            return ("or", None), src[2:]
        if src.startswith("=>"):
            return ("implies", None), src[2:]
        if src.startswith("<=>"):
            return ("iff", None), src[3:]
        if src.startswith("("):
            return ("(", None), src[1:]
        if src.startswith(")"):
            return (")", None), src[1:]

        m = re.match(r"(not|and|or|implies|xor|nor|nand|xnor|iff)[\s(]", src)
        if m:
            kw = m.group(1)
            return (kw if kw != "xnor" else "iff", None), src[len(kw):]

    tag = ""
    if escape:
        tag += src[0]
        src = src[1:]
    while len(src) > 0 and not check_tag_end(src):
        if len(src) > 1 and src[0] == '\\':
            tag += src[1]
            src = src[2:]
        else:
            tag += src[0]
            src = src[1:]
    tag = tag.strip()
    if len(tag) == 0:
        raise ValueError("Syntax error: empty search term")
    return ("tag", tag), src

#Roughly following conventional preferences, or C/C++ for rarely used operators
precedence_table = { "not": 10, "and": 9, "or": 8, "nor": 7, "nand": 7, "xor": 6, "implies": 5, "iff": 4 }

def precedence(token):
    if token[0] in precedence_table: return precedence_table[token[0]]
    raise ValueError("Syntax error: '{}' is not an operator".format(token[0]))

#A simple class representing a node in a logical expression tree
class Node:
    def __init__(self, op, children = []):
        self.op = op
        self.children = children[:]
    def __str__(self): #pretty string form, for debug purposes
        if self.op == "not":
            return "not ({})".format(str(self.children[0]) if type(self.children[0]) != str else self.children[0])
        else:
            child_strs = ["("+(str(x) if type(x) != str else x)+")" for x in self.children]
            final_str = ""
            for child_s in child_strs[:-1]:
                final_str += child_s
                final_str += " "+self.op+" "
            final_str += child_strs[-1]
            return final_str

#Parse a string into a logical expression tree
#First uses the shunting-yard algorithm to parse into reverse polish notation (RPN),
#then builds the tree from that
def parse(src):
    src = src.lower()
    prev_tok_type = "start"
    tok_type = "start"
    rpn_result = []
    operator_stack = []
    #Parse into reverse polish notation using the shunting-yard algorithm
    #Basic algorithm:
    #https://en.wikipedia.org/wiki/Shunting-yard_algorithm
    #Handling of unary operators:
    #https://stackoverflow.com/questions/1593080/how-can-i-modify-my-shunting-yard-algorithm-so-it-accepts-unary-operators
    #tl;dr - make unary operators right associative and higher precedence than any infix operator
    #however it will also accept prefix operators as postfix - we check for that later
    while True:
        prev_tok_type = tok_type
        token, src = next_token(src)
        tok_type, tok_val = token
        if tok_type == "end":
            break
        if tok_type == "tag":
            rpn_result.append(token)
        elif tok_type == "(":
            operator_stack.append(token)
        elif tok_type == ")":
            while len(operator_stack) > 0 and operator_stack[-1][0] != "(":
                rpn_result.append(operator_stack[-1])
                del operator_stack[-1]
            if len(operator_stack) > 0:
                del operator_stack[-1]
            else:
                raise ValueError("Syntax error: mismatched parentheses")
        else:
            if tok_type == "not" and prev_tok_type in ["tag",")"]:
                raise ValueError("Syntax error: invalid negation")
            while len(operator_stack) > 0 and operator_stack[-1][0] != "(" and \
                    (precedence(operator_stack[-1]) > precedence(token) or (precedence(operator_stack[-1]) == precedence(token) and operator_stack[-1][0] != "not")):
                rpn_result.append(operator_stack[-1])
                del operator_stack[-1]
            operator_stack.append(token)

    while len(operator_stack) > 0:
        if operator_stack[-1][0] in ["(", ")"]:
            raise ValueError("Syntax error: mismatched parentheses")
        rpn_result.append(operator_stack[-1])
        del operator_stack[-1]

    if len(rpn_result) == 0:
        raise ValueError("Empty input!")

    #Convert RPN into a tree
    #The original shunting-yard algorithm doesn't check for wrong number of arguments so also check that here
    rpn_result = list(reversed(rpn_result))
    stack = []
    while len(rpn_result) > 0:
        if rpn_result[-1][0] == "tag":
            stack.append(rpn_result[-1][1])
            del rpn_result[-1]
        else:
            if rpn_result[-1][0] == "not":
                if len(stack) == 0:
                    raise ValueError("Syntax error: wrong number of arguments")
                op = Node("not", [stack[-1]])
                del stack[-1]
                stack.append(op)
            else:
                if len(stack) < 2:
                    raise ValueError("Syntax error: wrong number of arguments")
                op = Node(rpn_result[-1][0], [stack[-2], stack[-1]])
                del stack[-1]
                del stack[-1]
                stack.append(op)
            del rpn_result[-1]

    #The original shunting-yard algorithm also accepts prefix operators as postfix
    #Check for that here
    if len(stack) != 1:
        raise ValueError("Parser error: unused values left in stack")

    return stack[0]

#Input is an expression tree
#Convert all logical operators to 'and', 'or' and 'not'
def convert_to_and_or_not(node):
    def negate(node):
        return Node("not", [convert_to_and_or_not(node)])

    if not hasattr(node, 'op'): return node

    if node.op == "implies": #convert to !a || b
        return Node("or", [negate(node.children[0]), convert_to_and_or_not(node.children[1])])
    elif node.op == "xor": #convert to (a && !b) || (!a && b)
        return Node("or", [
            Node("and", [convert_to_and_or_not(node.children[0]), negate(node.children[1])]),
            Node("and", [negate(node.children[0]), convert_to_and_or_not(node.children[1])])
        ])
    elif node.op == "nor": #convert to !(a || b)
        return negate(Node("or", node.children))
    elif node.op == "nand": #convert to !(a && b)
        return negate(Node("and", node.children))
    elif node.op == "iff": #convert to (a && b) || (!a && !b)
        return Node("or", [
            convert_to_and_or_not(Node("and", node.children)),
            Node("and", [negate(node.children[0]), negate(node.children[1])])
        ])
    else:
        return Node(node.op, list(map(convert_to_and_or_not, node.children)))

#Move negation inwards (downwards in the expr. tree) by using De Morgan's law,
#until they are directly apply to a term
#Also eliminates double negations
def move_not_inwards(node):
    if hasattr(node, 'op'):
        if node.op == "not" and hasattr(node.children[0], 'op'):
            if node.children[0].op == "not": #eliminate double negation
                return move_not_inwards(node.children[0].children[0])
            elif node.children[0].op == "and": #apply De Morgan's law
                return Node("or", [move_not_inwards(Node("not", [node.children[0].children[0]])), move_not_inwards(Node("not", [node.children[0].children[1]]))])
            elif node.children[0].op == "or": #apply De Morgan's law
                return Node("and", [move_not_inwards(Node("not", [node.children[0].children[0]])), move_not_inwards(Node("not", [node.children[0].children[1]]))])
            else:
                return Node(node.op, list(map(move_not_inwards, node.children)))
        else:
            return Node(node.op, list(map(move_not_inwards, node.children)))
    return node

#Use the distribute law to swap 'and's and 'or's so we get CNF
#Basically pushes 'or's downwards in the expression tree
def distribute_and_over_or(node):
    if hasattr(node, 'op'):
        node.children = list(map(distribute_and_over_or, node.children))
        if node.op == 'or' and hasattr(node.children[0], 'op') and node.children[0].op == 'and': #apply (A && B) || C -> (A || C) && (B || C)
            a = node.children[0].children[0]
            b = node.children[0].children[1]
            c = node.children[1]
            return Node("and", [distribute_and_over_or(Node("or", [a, c])), distribute_and_over_or(Node("or", [b, c]))])
        elif node.op == 'or' and hasattr(node.children[1], 'op') and node.children[1].op == 'and': #apply C || (A && B) -> (A || C) && (B || C)
            a = node.children[1].children[0]
            b = node.children[1].children[1]
            c = node.children[0]
            return Node("and", [distribute_and_over_or(Node("or", [a, c])), distribute_and_over_or(Node("or", [b, c]))])
        else:
            return node
    return node

#Flatten the tree so that 'and'/'or's don't have 'and'/'or's as direct children
#or(or(a,b),c) -> or(a,b,c)
#After this step, nodes can have more than two child
def flatten_tree(node):
    if hasattr(node, 'op'):
        node.children = list(map(flatten_tree, node.children))
        if node.op == 'and':
            new_children = []
            for chld in node.children:
                if hasattr(chld, 'op') and chld.op == 'and':
                    new_children += chld.children
                else:
                    new_children.append(chld)
            node.children = new_children
        elif node.op == 'or':
            new_children = []
            for chld in node.children:
                if hasattr(chld, 'op') and chld.op == 'or':
                    new_children += chld.children
                else:
                    new_children.append(chld)
            node.children = new_children
    return node

#Convert the flattened tree to a list of sets of terms
#Do some basic simplification: removing tautological or repeating clauses
def convert_to_list_and_simplify(node):
    res = []
    if hasattr(node, 'op'):
        if node.op == 'and':
            for chld in node.children:
                if type(chld) == str:
                    res.append(set([chld]))
                elif chld.op == 'not':
                    res.append(set(["-"+chld.children[0]]))
                else:
                    res.append(set(map(lambda x: "-"+x.children[0] if hasattr(x, "op") else x, chld.children)))
        elif node.op == 'or':
            res.append(set(map(lambda x: "-"+x.children[0] if hasattr(x, "op") else x, node.children)))
        elif node.op == 'not':
            res.append(set(["-"+node.children[0]]))
    else:
        res.append(set([node]))
    filtered_res = []
    last_found_always_true_clause = None
    #Filter out tautologies
    for clause in res:
        always_true = False
        for term in clause:
            if "-"+term in clause:
                always_true = True
                last_found_always_true_clause = clause
                break
        if not always_true: filtered_res.append(clause)
    #Remove repeating clauses
    for i in range(len(filtered_res)):
        for j in range(len(filtered_res)):
            if i != j and filtered_res[i] == filtered_res[j]: filtered_res[i] = None
    filtered_res = [x for x in filtered_res if x is not None]
    #Do not return empty if all clauses are tautologies, return a single clause instead
    if len(filtered_res) == 0 and last_found_always_true_clause:
        filtered_res.append(last_found_always_true_clause)
    return filtered_res

#This is the main function of this module that should be called from outside
def parse_logic_expression_query(input_str):
    return convert_to_list_and_simplify(flatten_tree(distribute_and_over_or(move_not_inwards(convert_to_and_or_not(parse(input_str))))))
