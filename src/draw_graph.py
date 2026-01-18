import os
from excel_agent.graph import get_graph

def draw_graph():
    graph = get_graph()
    try:
        # 使用 mermaid 格式输出，这样不需要安装 heavy 的 graphviz 依赖
        print(graph.get_graph().draw_mermaid())
        
        # 同时也尝试保存为 png，如果环境支持
        try:
            png_data = graph.get_graph().draw_mermaid_png()
            with open("workflow_graph.png", "wb") as f:
                f.write(png_data)
            print("\nSuccessfully saved workflow graph to 'workflow_graph.png'")
        except Exception as e:
            print(f"\nCould not save PNG (this is expected if graphviz/mermaid-cli is not installed): {e}")
            print("You can copy the mermaid code above and paste it into https://mermaid.live/ to visualize it.")
            
    except Exception as e:
        print(f"Error drawing graph: {e}")

if __name__ == "__main__":
    draw_graph()
