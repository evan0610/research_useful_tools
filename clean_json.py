import os

root_dir = r"F:\frame_consistency_framework\yolo_datasets\ours_fangti2"

for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file == "yolo_auto_gen.json":
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                print(f"已删除: {file_path}")
            except Exception as e:
                print(f"删除失败: {file_path}, 错误: {e}")