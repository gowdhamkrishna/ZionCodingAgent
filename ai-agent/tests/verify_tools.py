import os
import sys

# Add parent directory to path to import tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.filesystem_tools import ReadFileTool, EditFileTool, ListDirTool, SearchFileTool, WriteFileTool

def test_tools():
    print("Testing File System Tools...")
    
    # Setup
    test_dir = "test_artifacts"
    os.makedirs(test_dir, exist_ok=True)
    file_path = os.path.join(test_dir, "test_file.txt")
    
    # 1. Test WriteFileTool (Existing/Modified)
    write_tool = WriteFileTool()
    content = "Line 1\nLine 2\nLine 3\nTarget String\nLine 5"
    print(f"1. Testing WriteFileTool...")
    result = write_tool.execute(file_path, content)
    print(f"   Result: {result}")
    assert "Successfully wrote" in result

    # 2. Test ReadFileTool (Enhanced)
    read_tool = ReadFileTool()
    print(f"2. Testing ReadFileTool (Lines 2-3)...")
    content_read = read_tool.execute(file_path, start_line=2, end_line=3)
    print(f"   Result: {repr(content_read)}")
    assert "Line 2\nLine 3" in content_read

    # 3. Test EditFileTool (New)
    edit_tool = EditFileTool()
    print(f"3. Testing EditFileTool (Replace 'Target String' -> 'Replaced')...")
    edit_result = edit_tool.execute(file_path, "Target String", "Replaced")
    print(f"   Result: {edit_result}")
    assert "Successfully edited" in edit_result
    
    # Verify edit
    full_content = read_tool.execute(file_path)
    assert "Replaced" in full_content
    assert "Target String" not in full_content

    # 4. Test ListDirTool (Enhanced)
    list_tool = ListDirTool()
    print(f"4. Testing ListDirTool...")
    list_result = list_tool.execute(test_dir)
    print(f"   Result:\n{list_result}")
    assert "[FILE] test_file.txt" in list_result

    # 5. Test SearchFileTool (New)
    search_tool = SearchFileTool()
    print(f"5. Testing SearchFileTool (Searching for 'Replaced')...")
    search_result = search_tool.execute(test_dir, "Replaced")
    print(f"   Result:\n{search_result}")
    assert "test_file.txt" in search_result
    assert "Replaced" in search_result

    print("\nAll tests passed successfully!")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_tools()
