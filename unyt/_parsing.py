"""
parsing utilities



"""

# -----------------------------------------------------------------------------
# Copyright (c) 2019, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the LICENSE file, distributed with this software.
# -----------------------------------------------------------------------------


from keyword import iskeyword
from sympy.parsing.sympy_parser import parse_expr, auto_number, rationalize
from sympy import Basic, Float, Integer, Rational, sqrt, Symbol
import token

from unyt.exceptions import UnitParseError
from unyt._unit_lookup_table import inv_name_alternatives


def _auto_positive_symbol(tokens, local_dict, global_dict):
    """
    Inserts calls to ``Symbol`` for undefined variables.
    Passes in positive=True as a keyword argument.
    Adapted from sympy.sympy.parsing.sympy_parser.auto_symbol
    """
    result = []
    prevTok = (None, None)

    tokens.append((None, None))  # so zip traverses all tokens
    for tok, nextTok in zip(tokens, tokens[1:]):
        tokNum, tokVal = tok
        nextTokNum, nextTokVal = nextTok
        if tokNum == token.NAME:
            name = tokVal
            if (
                name in ["True", "False", "None"]
                # special case 'as' for attosecond
                or (iskeyword(name) and name != "as")
                or name in local_dict
                # Don't convert attribute access
                or (prevTok[0] == token.OP and prevTok[1] == ".")
                # Don't convert keyword arguments
                or (
                    prevTok[0] == token.OP
                    and prevTok[1] in ("(", ",")
                    and nextTokNum == token.OP
                    and nextTokVal == "="
                )
            ):
                result.append((token.NAME, name))
                continue
            elif name in global_dict:
                obj = global_dict[name]
                if isinstance(obj, (Basic, type)) or callable(obj):
                    result.append((token.NAME, name))
                    continue

            # try to resolve known alternative unit name
            try:
                used_name = inv_name_alternatives[str(name)]
            except KeyError:
                # if we don't know this name it's a user-defined unit name
                # so we should create a new symbol for it
                used_name = str(name)

            result.extend(
                [
                    (token.NAME, "Symbol"),
                    (token.OP, "("),
                    (token.NAME, repr(used_name)),
                    (token.OP, ","),
                    (token.NAME, "positive"),
                    (token.OP, "="),
                    (token.NAME, "True"),
                    (token.OP, ")"),
                ]
            )
        else:
            result.append((tokNum, tokVal))

        prevTok = (tokNum, tokVal)

    return result


global_dict = {
    "Symbol": Symbol,
    "Integer": Integer,
    "Float": Float,
    "Rational": Rational,
    "sqrt": sqrt,
}

unit_text_transform = (_auto_positive_symbol, rationalize, auto_number)


def parse_unyt_expr(unit_expr):
    if not unit_expr:
        # Bug catch...
        # if unit_expr is an empty string, parse_expr fails hard...
        unit_expr = "1"
    try:
        unit_expr = parse_expr(
            unit_expr, global_dict=global_dict, transformations=unit_text_transform
        )
    except SyntaxError as e:
        msg = "Unit expression '%s' raised an error during parsing:\n%s" % (
            unit_expr,
            repr(e),
        )
        raise UnitParseError(msg)
    return unit_expr
