import os
import shutil

# --- 用户配置 ---
# 1. 设置你要清理的根目录
ROOT_DIR = r"D:/2.3/2.3"

# 2. 安全开关：True = 只看不做 (演习模式)，False = 实际执行 (危险！)
# !!! 强烈建议先在 True 模式下运行，检查输出日志是否符合预期 !!!
DRY_RUN = False
# -----------------

def repair_structure(base_dir):
    """
    专门修复三层嵌套 -> 两层嵌套的函数。
    """
    print(f"\n▶ 发现疑似三层嵌套结构: {base_dir}")

    level1_dir = base_dir
    level2_dir = os.path.join(level1_dir, os.path.basename(level1_dir))
    level3_dir = os.path.join(level2_dir, os.path.basename(level2_dir))

    # --- 执行清理 ---
    # 1. 删除第2层嵌套里的所有 .jpg 照片
    print(f"  - 计划删除第2层 [{level2_dir}] 中的 .jpg 文件...")
    if not DRY_RUN:
        for item in os.listdir(level2_dir):
            if item.lower().endswith(".jpg"):
                try:
                    os.remove(os.path.join(level2_dir, item))
                except Exception as e:
                    print(f"    - 删除失败: {item}, 原因: {e}")
    print("    ✓ (计划)完成。")


    # 2. "删除第1层"，即用第2层的内容替换第1层
    # 策略：将第2层的所有内容移动到临时位置，删除第1层，再将临时位置重命名
    parent_dir = os.path.dirname(level1_dir)
    temp_dir_name = f"{os.path.basename(level1_dir)}_temp_{os.getpid()}"
    temp_dir_path = os.path.join(parent_dir, temp_dir_name)

    print(f"  - 计划将第2层 [{level2_dir}] 移动到临时位置 [{temp_dir_path}]...")
    if not DRY_RUN:
        try:
            shutil.move(level2_dir, temp_dir_path)
        except Exception as e:
            print(f"    ❌ 移动到临时位置失败: {e}")
            return # 关键步骤失败，中止此文件夹的修复
    print("    ✓ (计划)完成。")

    print(f"  - 计划删除残留的第1层文件夹 [{level1_dir}]...")
    if not DRY_RUN:
        try:
            shutil.rmtree(level1_dir)
        except Exception as e:
            print(f"    ❌ 删除第1层失败: {e}")
            # 尝试把文件移回去，恢复原状
            shutil.move(temp_dir_path, level2_dir) 
            return
    print("    ✓ (计划)完成。")

    print(f"  - 计划将临时文件夹重命名，完成替换 [{temp_dir_path}] -> [{level1_dir}]")
    if not DRY_RUN:
        try:
            os.rename(temp_dir_path, level1_dir)
        except Exception as e:
            print(f"    ❌ 最终重命名失败: {e}")
            return
    print("    ✓ (计划)完成。")

    print(f"✅ 实验 [{os.path.basename(base_dir)}] 结构修复(计划)成功！")


def main():
    """
    主函数
    """
    if DRY_RUN:
        print("--- 正在以 DRY_RUN (演习) 模式运行 ---")
        print("--- 不会修改任何文件，只会打印计划 ---")
    else:
        print("--- !!! 警告：正在以实际执行模式运行 !!! ---")
        print("--- 将会实际删除和移动文件，操作不可逆！ ---")

    # 扫描所有文件夹
    for root, dirs, _ in os.walk(ROOT_DIR, topdown=True):
        for dir_name in list(dirs): # 使用 list 副本，因为我们可能会修改 dirs
            # 检查是否存在 "X/X/X" 的三层嵌套结构
            level1_name = dir_name
            level1_path = os.path.join(root, level1_name)
            
            level2_path = os.path.join(level1_path, level1_name)
            level3_path = os.path.join(level2_path, level1_name)

            if os.path.isdir(level3_path):
                repair_structure(level1_path)
                # 从目录列表中移除，防止 os.walk 继续深入这个已经处理的目录
                dirs.remove(level1_name) 

    print("\n--- 所有操作执行完毕 ---")


if __name__ == "__main__":
    main()
