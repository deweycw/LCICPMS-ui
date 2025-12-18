"""Utility functions for formatting analyte names with superscripts and subscripts."""

import re


def format_analyte_html(analyte):
    """
    Format analyte string with HTML superscripts and subscripts for PyQtGraph.

    Examples:
        "56Fe" -> "<sup>56</sup>Fe"
        "238UO2" -> "<sup>238</sup>UO<sub>2</sub>"
        "32S|32SO" -> "<sup>32</sup>S(<sup>32</sup>SO)"
        "32S|32S.16O" -> "<sup>32</sup>S(<sup>32</sup>S<sup>16</sup>O)"

    Args:
        analyte: Raw analyte string

    Returns:
        HTML-formatted string
    """
    def format_part(part):
        """Format a single analyte part, handling multiple elements separated by periods."""
        # Remove periods that separate elements
        part = part.replace('.', '')

        # Pattern to match all isotope-element pairs in the string
        # This handles cases like "32S16O" where we have multiple isotope-element pairs
        result = ''
        remaining = part

        while remaining:
            # Try to match isotope number + element symbol at the start
            match = re.match(r'^(\d+)([A-Z][a-z]?)', remaining)
            if match:
                isotope = match.group(1)
                element = match.group(2)
                result += f'<sup>{isotope}</sup>{element}'
                remaining = remaining[len(match.group(0)):]
            else:
                # Check if there's a number (stoichiometry)
                match = re.match(r'^(\d+)', remaining)
                if match:
                    number = match.group(1)
                    result += f'<sub>{number}</sub>'
                    remaining = remaining[len(number):]
                else:
                    # Just add the character as-is
                    result += remaining[0]
                    remaining = remaining[1:]

        return result

    # Split by pipe and process each part
    parts = analyte.split('|')
    formatted_parts = [format_part(part) for part in parts]

    # Join with parentheses if there are multiple parts (no spaces)
    if len(formatted_parts) == 2:
        return f'{formatted_parts[0]}({formatted_parts[1]})'
    elif len(formatted_parts) > 2:
        return f'{formatted_parts[0]}({",".join(formatted_parts[1:])})'
    else:
        return formatted_parts[0]


def format_analyte_latex(analyte):
    """
    Format analyte string with LaTeX superscripts and subscripts for Matplotlib.

    Examples:
        "56Fe" -> r"$^{56}$Fe"
        "238UO2" -> r"$^{238}$UO$_{2}$"
        "32S|32SO" -> r"$^{32}$S($^{32}$SO)"
        "32S|32S.16O" -> r"$^{32}$S($^{32}$S$^{16}$O)"

    Args:
        analyte: Raw analyte string

    Returns:
        LaTeX-formatted string
    """
    def format_part(part):
        """Format a single analyte part, handling multiple elements separated by periods."""
        # Remove periods that separate elements
        part = part.replace('.', '')

        # Pattern to match all isotope-element pairs in the string
        result = ''
        remaining = part

        while remaining:
            # Try to match isotope number + element symbol at the start
            match = re.match(r'^(\d+)([A-Z][a-z]?)', remaining)
            if match:
                isotope = match.group(1)
                element = match.group(2)
                result += f'$^{{{isotope}}}${element}'
                remaining = remaining[len(match.group(0)):]
            else:
                # Check if there's a number (stoichiometry)
                match = re.match(r'^(\d+)', remaining)
                if match:
                    number = match.group(1)
                    result += f'$_{{{number}}}$'
                    remaining = remaining[len(number):]
                else:
                    # Just add the character as-is
                    result += remaining[0]
                    remaining = remaining[1:]

        return result

    # Split by pipe and process each part
    parts = analyte.split('|')
    formatted_parts = [format_part(part) for part in parts]

    # Join with parentheses if there are multiple parts (no spaces)
    if len(formatted_parts) == 2:
        return f'{formatted_parts[0]}({formatted_parts[1]})'
    elif len(formatted_parts) > 2:
        return f'{formatted_parts[0]}({",".join(formatted_parts[1:])})'
    else:
        return formatted_parts[0]
