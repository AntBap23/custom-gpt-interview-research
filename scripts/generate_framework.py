from graphviz import Digraph

def generate_framework(gioia_path, output_path):
    with open(gioia_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

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

    dot.render(output_path, format="png", cleanup=True)
