"""Utility functions for formatting analyte names with superscripts and subscripts."""

import re


def format_analyte_html(analyte):
    """
    Format analyte string with HTML superscripts and subscripts for PyQtGraph.

    Examples:
        "56Fe" -> "<sup>56</sup>Fe"
        "238UO2" -> "<sup>238</sup>UO<sub>2</sub>"
        "32S|32SO" -> "<sup>32</sup>S (<sup>32</sup>SO)"

    Args:
        analyte: Raw analyte string

    Returns:
        HTML-formatted string
    """
    # Split by pipe and process each part
    parts = analyte.split('|')
    formatted_parts = []

    for part in parts:
        # Pattern to match isotope number at start, element symbol, and optional stoichiometry
        match = re.match(r'^(\d+)([A-Z][a-z]?)(.*)$', part)

        if match:
            isotope = match.group(1)  # e.g., "56"
            element = match.group(2)  # e.g., "Fe"
            suffix = match.group(3)   # e.g., "O2", "O", ""

            # Format isotope as superscript
            formatted = f'<sup>{isotope}</sup>{element}'

            # Format stoichiometry (numbers after element) as subscript
            if suffix:
                formatted_suffix = re.sub(r'(\d+)', r'<sub>\1</sub>', suffix)
                formatted += formatted_suffix

            formatted_parts.append(formatted)
        else:
            # If pattern doesn't match, use as-is
            formatted_parts.append(part)

    # Join with parentheses if there are multiple parts
    if len(formatted_parts) == 2:
        return f'{formatted_parts[0]} ({formatted_parts[1]})'
    elif len(formatted_parts) > 2:
        return f'{formatted_parts[0]} ({", ".join(formatted_parts[1:])})'
    else:
        return formatted_parts[0]


def format_analyte_latex(analyte):
    """
    Format analyte string with LaTeX superscripts and subscripts for Matplotlib.

    Examples:
        "56Fe" -> r"$^{56}$Fe"
        "238UO2" -> r"$^{238}$UO$_{2}$"
        "32S|32SO" -> r"$^{32}$S ($^{32}$SO)"

    Args:
        analyte: Raw analyte string

    Returns:
        LaTeX-formatted string
    """
    # Split by pipe and process each part
    parts = analyte.split('|')
    formatted_parts = []

    for part in parts:
        # Pattern to match isotope number at start, element symbol, and optional stoichiometry
        match = re.match(r'^(\d+)([A-Z][a-z]?)(.*)$', part)

        if match:
            isotope = match.group(1)  # e.g., "56"
            element = match.group(2)  # e.g., "Fe"
            suffix = match.group(3)   # e.g., "O2", "O", ""

            # Format isotope as superscript
            formatted = f'$^{{{isotope}}}${element}'

            # Format stoichiometry (numbers after element) as subscript
            if suffix:
                formatted_suffix = re.sub(r'(\d+)', r'$_{\1}$', suffix)
                formatted += formatted_suffix

            formatted_parts.append(formatted)
        else:
            # If pattern doesn't match, use as-is
            formatted_parts.append(part)

    # Join with parentheses if there are multiple parts
    if len(formatted_parts) == 2:
        return f'{formatted_parts[0]} ({formatted_parts[1]})'
    elif len(formatted_parts) > 2:
        return f'{formatted_parts[0]} ({", ".join(formatted_parts[1:])})'
    else:
        return formatted_parts[0]
