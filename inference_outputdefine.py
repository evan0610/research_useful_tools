import os
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd
import sys

# =========================
# ⚙️ Windows 用户配置区
# =========================

# 1. 设置数据根目录 (注意：Windows路径前加 r，或者用双反斜杠 \\)
ROOT_DIR = r"D:\new_data" 

# 2. 设置 FFmpeg 的 bin 文件夹路径 (包含 ffmpeg.exe 的那个文件夹)
#    如果您的 ffmpeg 就在系统路径里，可以留空 ""
FFMPEG_DIR = r"D:/ffmpeg-master-latest-win64-gpl\bin"  # <--- 请修改为您解压后的实际路径！

# 采样率
TARGET_FPS = 20
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_EXTS = [".avi", ".mp4", ".mov", ".mkv"]

# =========================
# 核心逻辑
# =========================

def get_exe_path(tool_name):
    """自动处理 Windows 的 .exe 后缀和路径拼接"""
    if sys.platform.startswith("win"):
        if not tool_name.endswith(".exe"):
            tool_name += ".exe"
    
    if FFMPEG_DIR and os.path.exists(FFMPEG_DIR):
        return os.path.join(FFMPEG_DIR, tool_name)
    return tool_name

def _run(cmd: List[str]) -> Tuple[int, str, str]:
    # Windows 下 subprocess 需要处理路径空格等问题，通常直接传入列表即可
    try:
        # startupinfo 用于隐藏 Windows 下弹出的黑框
        startupinfo = None
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        p = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            encoding='utf-8', # 防止中文乱码
            errors='ignore',
            startupinfo=startupinfo
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return -1, "", f"找不到命令: {cmd[0]}"

def ensure_ffmpeg() -> None:
    ffmpeg_exe = get_exe_path("ffmpeg")
    
    print(f"正在检查 FFmpeg: {ffmpeg_exe}")
    rc, _, _ = _run([ffmpeg_exe, "-version"])
    if rc != 0:
        raise RuntimeError(
            f"\n❌ 错误：无法运行 FFmpeg！\n"
            f"请检查代码中的 FFMPEG_DIR 路径是否正确：{FFMPEG_DIR}\n"
            f"系统报错：找不到文件 {ffmpeg_exe}"
        )
    print("✅ FFmpeg 检查通过")

def ffprobe_info(video_path: Path) -> Tuple[Optional[int], Optional[float]]:
    cmd = [
        get_exe_path("ffprobe"), "-v", "error", "-select_streams", "v:0",
        "-count_frames", "-show_entries", "stream=nb_read_frames:format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(video_path)
    ]
    rc, out, _ = _run(cmd)
    frames, duration = None, None
    if rc == 0:
        lines = out.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.isdigit(): 
                frames = int(line)
            else:
                try: duration = float(line)
                except: pass
    return frames, duration

def extract_ts(name: str) -> Optional[datetime]:
    m = re.search(r"(\d{8})[-_](\d{6})", name)
    if not m: return None
    try: return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except: return None

def find_video_for_csv(csv_path: Path) -> Optional[Path]:
    parent_dir = csv_path.parent
    stem = csv_path.stem
    stem_vid = stem.replace("data_", "video_")
    
    # 规则1 & 2
    for ext in VIDEO_EXTS:
        if (parent_dir / f"{stem_vid}{ext}").exists(): return parent_dir / f"{stem_vid}{ext}"
        if (parent_dir / f"{stem}{ext}").exists(): return parent_dir / f"{stem}{ext}"

    # 规则3: 时间戳
    ts = extract_ts(csv_path.name)
    if not ts: return None
    
    best, best_dt = None, 1e9
    # 扫描目录下所有文件
    for v in parent_dir.iterdir():
        if v.suffix in VIDEO_EXTS and "tmp_align" not in v.name:
            ts_v = extract_ts(v.name)
            if not ts_v: continue
            dt = abs((ts_v - ts).total_seconds())
            if dt < 60 and dt < best_dt:
                best, best_dt = v, dt
    return best

def transcode_video_safe(src: Path, dst_tmp: Path, T: int, input_fps: float = None, src_dur: float = None) -> None:
    csv_dur = T / float(TARGET_FPS)
    margin = 2.0
    if input_fps: pad = margin
    elif src_dur and src_dur > 0: pad = max(margin, (csv_dur - src_dur) + margin)
    else: pad = csv_dur + margin

    pre_args = ["-r", f"{input_fps:.6f}"] if input_fps else []
    
    # Windows 路径转字符串
    src_str = str(src)
    dst_str = str(dst_tmp)

    vf = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:flags=bicubic,tpad=stop_mode=clone:stop_duration={pad},fps={TARGET_FPS}"
    
    cmd = [
        get_exe_path("ffmpeg"), "-y", "-loglevel", "error", "-fflags", "+genpts",
        *pre_args, "-i", src_str,
        "-vf", vf,
        "-vsync", "1", # 兼容参数
        "-frames:v", str(int(T)),
        "-an", "-c:v", "mjpeg", "-q:v", "3", 
        dst_str
    ]
    rc, _, err = _run(cmd)
    if rc != 0: raise RuntimeError(f"FFmpeg Error: {err[:500]}")

def main():
    try:
        ensure_ffmpeg()
    except RuntimeError as e:
        print(e)
        return

    root = Path(ROOT_DIR)
    if not root.exists():
        print(f"❌ 错误: 找不到数据目录 -> {root}")
        return

    print(f"=== 🚀 Windows 对齐工具启动 ===")
    print(f"扫描目录: {root}\n")
    
    all_csvs = sorted(list(root.rglob("*.csv")))
    all_csvs = [f for f in all_csvs if "tmp_" not in f.name]
    
    success_count = 0
    
    for i, csv_path in enumerate(all_csvs):
        print(f"[{i+1}/{len(all_csvs)}] {csv_path.name}")
        
        video_src = find_video_for_csv(csv_path)
        if not video_src:
            print(f"   └── ⚠️ 跳过: 无对应视频")
            continue

        try:
            df = pd.read_csv(csv_path, usecols=[0]) 
            T = len(df)
            if T < 10:
                print(f"   └── ⚠️ 跳过: 数据过短")
                continue

            raw_frames, vid_dur = ffprobe_info(video_src)
            if not raw_frames:
                print(f"   └── ❌ 错误: 视频无法读取")
                continue

            input_fps = None
            if vid_dur:
                csv_dur = T / float(TARGET_FPS)
                diff = csv_dur - vid_dur
                if diff > 0.3 and (diff / max(csv_dur, 1e-6) > 0.015):
                    input_fps = raw_frames / csv_dur
                    print(f"   └── 🔧 修复快进 (差 {diff:.2f}s)")

            tmp_vid = csv_path.parent / f"tmp_align_{csv_path.stem}.avi"
            transcode_video_safe(video_src, tmp_vid, T, input_fps, vid_dur)

            out_frames, _ = ffprobe_info(tmp_vid)
            if out_frames != T:
                print(f"   └── ❌ 校验失败: CSV={T} Video={out_frames}")
                if tmp_vid.exists(): os.remove(tmp_vid)
                continue

            target_vid = video_src.with_suffix(".avi")
            
            # Windows 下替换文件建议先删除目标
            if target_vid.exists():
                os.remove(target_vid)
            os.rename(tmp_vid, target_vid)
            
            # 删除旧格式视频 (如 mp4)
            if video_src != target_vid and video_src.exists():
                os.remove(video_src)

            print(f"   └── ✅ 成功 (帧数: {T})")
            success_count += 1

        except Exception as e:
            print(f"   └── 💥 异常: {e}")
            if 'tmp_vid' in locals() and tmp_vid.exists(): os.remove(tmp_vid)

    print(f"\n=== 处理完成: {success_count} 个 ===")

if __name__ == "__main__":
    main()
