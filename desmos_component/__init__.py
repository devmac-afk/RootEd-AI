# desmos_component/__init__.py

import os
import streamlit.components.v1 as components

# Declare the component, pointing to the build directory
_build_dir = os.path.join(os.path.dirname(__file__), "build")
_desmos_graph = components.declare_component("desmos_graph", path=_build_dir)

def show_desmos(expression, index: int):
    """
    Renders the Desmos graph component.

    Args:
        expression: The LaTeX string or list of strings to graph.
        index (int): A unique index (like the loop counter) to create a stable key.
    """
    # Use the index to create a unique and stable key for the component
    return _desmos_graph(latex=expression, key=f"desmos_component_{index}", default=None)