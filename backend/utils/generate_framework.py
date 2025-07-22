from graphviz import Digraph
import os

def generate_framework(gioia_text, output_path):
    """
    gioia_text: string (Gioia analysis in Markdown)
    output_path: path to save the PNG
    Returns: output_path
    """
    lines = gioia_text.splitlines()
    dot = Digraph(comment="Theoretical Framework")
    dimension, theme = None, None
    for line in lines:
        line = line.strip()
        if line.startswith("Dimension:"):
            dimension = line.replace("Dimension:", "").strip()
            dot.node(dimension, shape='box', style='filled', fillcolor='lightblue')
        elif line.startswith("Theme:"):
            theme = line.replace("Theme:", "").strip()
            dot.node(theme, shape='ellipse', style='filled', fillcolor='lightgreen')
            dot.edge(theme, dimension)
        elif line.startswith("- "):
            code = line.replace("- ", "").strip()
            dot.node(code, shape='note')
            dot.edge(code, theme)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    dot.render(output_path, format="png", cleanup=True)
    return output_path + ".png" 