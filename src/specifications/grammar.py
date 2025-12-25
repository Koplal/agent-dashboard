"""
Specification Language Grammar.

Defines the Lark grammar for the agent specification DSL.

Version: 2.6.0
"""

# Lark grammar for agent specification language
SPECIFICATION_GRAMMAR = r"""
// Agent Specification Grammar

?start: specification

specification: "AGENT" IDENTIFIER ":" agent_body

agent_body: tier_decl tools_decl? output_spec? behavior_spec? limits_spec?

tier_decl: "TIER:" tier_name
tier_name: "opus" | "sonnet" | "haiku"

tools_decl: "TOOLS:" "[" tool_list "]"
tool_list: IDENTIFIER ("," IDENTIFIER)*

output_spec: "OUTPUT" "MUST" "SATISFY:" constraint_list
constraint_list: constraint+

constraint: quantified_constraint
          | simple_constraint
          | conditional_constraint

quantified_constraint: quantifier IDENTIFIER "in" path ":" constraint
quantifier: "forall" -> forall_quant
          | "exists" -> exists_quant

conditional_constraint: "if" condition ":" constraint

simple_constraint: path comparator value -> comparison_constraint
                 | path "IS" type_check -> type_constraint
                 | path "IN" "RANGE" "[" number "," number "]" -> range_constraint
                 | path "IN" "[" value_list "]" -> in_list_constraint
                 | "NOT" constraint -> not_constraint
                 | constraint "AND" constraint -> and_constraint
                 | constraint "OR" constraint -> or_constraint

condition: path comparator value -> comparison_condition
         | path "IS" type_check -> type_condition
         | "count" "(" path ")" comparator number -> count_condition
         | "any" "(" predicate ")" -> any_condition
         | "all" "(" predicate ")" -> all_condition
         | condition "AND" condition -> and_condition
         | condition "OR" condition -> or_condition
         | "NOT" condition -> not_condition

predicate: path comparator value
         | path "IS" type_check

comparator: "==" -> eq
          | "!=" -> ne
          | "<" -> lt
          | ">" -> gt
          | "<=" -> le
          | ">=" -> ge

type_check: "VALID_URL" -> valid_url
          | "VALID_EMAIL" -> valid_email
          | "VALID_DATE" -> valid_date
          | "STRING" -> string_type
          | "NUMBER" -> number_type
          | "BOOLEAN" -> boolean_type
          | "LIST" -> list_type
          | "OBJECT" -> object_type
          | "NOT_EMPTY" -> not_empty

behavior_spec: "BEHAVIOR:" behavior_list
behavior_list: behavior_rule+

behavior_rule: prefer_rule
             | never_rule
             | always_rule
             | when_rule

prefer_rule: "PREFER" value "OVER" value
never_rule: "NEVER" action_desc
always_rule: "ALWAYS" action_desc
when_rule: "WHEN" condition ":" action_desc

action_desc: action_word+ -> action
action_word: IDENTIFIER | STRING_VALUE

limits_spec: "LIMITS:" limit_list
limit_list: limit_decl+

limit_decl: IDENTIFIER ":" number

path: IDENTIFIER ("." IDENTIFIER)*

value: number | STRING_VALUE | "TRUE" | "FALSE" | "NULL" | "TODAY" | date_expr

date_expr: "TODAY" date_offset?
date_offset: ("+" | "-") number time_unit
time_unit: "DAYS" | "HOURS" | "MINUTES" | "SECONDS"

value_list: value ("," value)*

number: SIGNED_NUMBER

// Terminals
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING_VALUE: /"[^"]*"/ | /'[^']*'/
SIGNED_NUMBER: /-?[0-9]+(\.[0-9]+)?/

// Comments and whitespace
COMMENT: /#[^\n]*/
%import common.WS
%ignore WS
%ignore COMMENT
"""

# Simplified grammar for basic parsing (fallback if Lark not available)
SIMPLE_GRAMMAR_PATTERNS = {
    "agent_name": r"AGENT\s+(\w+)\s*:",
    "tier": r"TIER:\s*(opus|sonnet|haiku)",
    "tools": r"TOOLS:\s*\[([\w\s,]+)\]",
    "output_spec": r"OUTPUT\s+MUST\s+SATISFY:\s*(.*?)(?=BEHAVIOR:|LIMITS:|$)",
    "behavior_spec": r"BEHAVIOR:\s*(.*?)(?=LIMITS:|$)",
    "limits_spec": r"LIMITS:\s*(.*?)$",
}
