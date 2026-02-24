import os
import cv2
import shutil
import pandas as pd

# 从 config.py 文件中导入我们定义好的配置
try:
    import config
except ImportError:
    print("❌ 错误：找不到配置文件 config.py！")
    print("请确保 config.py 和 main.py 在同一个文件夹下。")
    exit()

def extract_frames(video_path, image_dir):
    """
    从视频中提取所有帧并保存为图片。
    """
    # 【已修改】使用 CAP_DSHOW 后端，以提高在 Windows 上的视频解码兼容性
    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")

    os.makedirs(image_dir, exist_ok=True)
    
    idx = 1
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 使用从 config 文件导入的尺寸
        frame_resized = cv2.resize(frame, config.IMAGE_SIZE)
        
        out_path = os.path.join(image_dir, f"{idx:04d}.jpg")
        ok = cv2.imwrite(out_path, frame_resized)
        if not ok:
            raise RuntimeError(f"写入图片失败: {out_path}")
            
        idx += 1
        
    cap.release()
    
    if idx == 1:
        raise RuntimeError(
            "一帧都未能读取！很可能是视频编码问题，OpenCV 无法解码。"
        )
        
    return idx - 1

def count_csv_rows(csv_path):
    """
    计算 CSV 文件的数据行数 (不包括表头)。
    pandas 默认将第一行视为表头，所以 shape[0] 就是数据行数。
    """
    try:
        df = pd.read_csv(csv_path)
        return df.shape[0]
    except Exception as e:
        raise RuntimeError(f"读取或解析 CSV 文件失败: {csv_path} - {e}")

def main():
    """
    主执行函数
    """
    # ===== 1. 收集所有需要处理的实验 =====
    experiments = []
    print("▶ 开始扫描实验文件...")
    print(f"  - 根目录: {config.ROOT_DIR}")
    
    for root, _, files in os.walk(config.ROOT_DIR):
        for f in files:
            # 根据 config 里的配置查找视频文件
            if f.lower().endswith(config.VIDEO_EXTENSION):
                base_name = os.path.splitext(f)[0]
                # 根据 config 里的配置提取实验ID
                experiment_id = base_name.lower().replace(config.VIDEO_PREFIX_TO_REPLACE, "")
                
                # 根据 config 里的配置查找对应的 CSV 文件
                csv_file = next(
                    (x for x in files if x.lower().startswith(config.CSV_PREFIX) and experiment_id in x.lower()),
                    None
                )
                
                if csv_file:
                    experiments.append((root, f, csv_file, base_name))
                    print(f"  - 找到实验: {base_name}")

    if not experiments:
        print("🟡 扫描完成，但在指定目录下未找到任何匹配的 '视频-CSV' 文件对。")
        return

    print(f"✅ 扫描完成，共找到 {len(experiments)} 个待处理的实验。\n")

    # ===== 2. 逐个处理实验 =====
    for root, video_file, csv_file, exp_name in experiments:
        print(f"▶▶▶ 开始处理实验: {exp_name}")
        
        video_path = os.path.join(root, video_file)
        csv_path = os.path.join(root, csv_file)
        
        exp_dir = os.path.join(root, exp_name)
        img_dir = os.path.join(exp_dir, exp_name) # 图片子文件夹名 = 实验名
        
        try:
            if not os.path.exists(exp_dir):
                os.makedirs(img_dir)
            else:
                 # 如果文件夹已存在，为安全起见，先跳过
                 if os.path.exists(os.path.join(exp_dir, video_file)):
                    print(f"🟡 警告：实验文件夹 {exp_name} 已存在并且文件已移动，跳过此实验。")
                    continue

            # ① 提取视频帧
            print("  - 正在从视频提取图片...")
            frame_cnt = extract_frames(video_path, img_dir)
            print(f"    ✓ 成功生成 {frame_cnt} 张图片")

            # ② 校验 CSV 行数
            print("  - 正在校验 CSV 文件行数...")
            csv_cnt = count_csv_rows(csv_path)
            print(f"    ✓ CSV 数据行数为 {csv_cnt}")

            # ③ 对比数量
            if frame_cnt != csv_cnt:
                raise RuntimeError(f"帧数 ({frame_cnt}) ≠ CSV 行数 ({csv_cnt})，校验失败！")
            
            # ④ 移动文件
            print("  - 校验通过，正在整理文件...")
            shutil.move(video_path, os.path.join(exp_dir, video_file))
            shutil.move(csv_path, os.path.join(exp_dir, csv_file))
            print(f"  ✅ 实验 {exp_name} 处理完成！\n")

        except Exception as e:
            print(f"\n‼️ 处理实验 {exp_name} 时发生严重错误: {e}")
            print("‼️ 程序已中止。请检查错误信息并修正问题后重试。\n")
            break # 遇到任何一个实验的错误，就停止整个脚本

if __name__ == "__main__":
    main()

