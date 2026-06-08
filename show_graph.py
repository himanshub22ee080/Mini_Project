# print_graph.py
from src.agents.graph import ExchangeGraph

graph = ExchangeGraph()
app = graph.workflow

print("Generating graph.png...")
try:
    # Get the PNG bytes
    png_bytes = app.get_graph().draw_mermaid_png()
    
    # Write bytes to a file
    with open("graph_visualization.png", "wb") as f:
        f.write(png_bytes)
        
    print("✅ Graph successfully saved as 'graph_visualization.png'")
except Exception as e:
    print(f"❌ Failed to generate PNG: {e}")