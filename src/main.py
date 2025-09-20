import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import platform
import io
import threading
import sys
import importlib

# 添加模块路径
sys.path.append('./connector')
sys.path.append('./speaker')
sys.path.append('./vmic')
sys.path.append('./tts')

# 确保tmp目录存在
os.makedirs("tmp", exist_ok=True)

# 动态导入模块
FiFWebClient = importlib.import_module('connector.FiFWebClient').FiFWebClient
Speaker = importlib.import_module('speaker.Speaker').Speaker

class FiFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FiF口语自动化工具")
        self.root.geometry("700x550")
        self.root.resizable(False, False)
        
        # 配置变量
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.skip_score = tk.IntVar(value=80)
        self.target_voice_path = tk.StringVar(value="draft/target_voice.wav")
        self.is_running = False
        
        # 确保draft目录存在
        os.makedirs("draft", exist_ok=True)
        
        self.create_widgets()
        self.load_config()
    
    def create_widgets(self):
        # 创建标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 登录配置标签页
        self.login_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.login_frame, text="登录配置")
        
        ttk.Label(self.login_frame, text="用户名:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(self.login_frame, textvariable=self.username, width=30).grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(self.login_frame, text="密码:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(self.login_frame, textvariable=self.password, show="*", width=30).grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(self.login_frame, text="跳过分数:").grid(row=2, column=0, sticky='w', pady=5)
        
        # 滑动条和输入框的框架
        score_frame = ttk.Frame(self.login_frame)
        score_frame.grid(row=2, column=1, sticky='ew', pady=5, padx=5)
        
        self.score_scale = ttk.Scale(score_frame, from_=0, to=100, variable=self.skip_score, 
                                    orient='horizontal', command=self.on_scale_change)
        self.score_scale.pack(side='left', fill='x', expand=True)
        
        self.score_entry = ttk.Entry(score_frame, textvariable=self.skip_score, width=5)
        self.score_entry.pack(side='right', padx=(5, 0))
        self.score_entry.bind('<Return>', self.on_entry_change)
        self.score_entry.bind('<FocusOut>', self.on_entry_change)
        
        # 语音配置标签页
        self.voice_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.voice_frame, text="语音配置")
        
        ttk.Label(self.voice_frame, text="目标音色文件:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(self.voice_frame, textvariable=self.target_voice_path, width=30).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(self.voice_frame, text="浏览", command=self.browse_voice_file).grid(row=0, column=2, pady=5, padx=5)
        
        # 控制按钮
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_btn = ttk.Button(self.control_frame, text="开始运行", command=self.toggle_run)
        self.start_btn.pack(side='left', padx=5)
        
        self.save_btn = ttk.Button(self.control_frame, text="保存配置", command=self.save_config)
        self.save_btn.pack(side='left', padx=5)
        
        # 日志区域
        self.log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=10)
        self.log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = tk.Text(self.log_frame, height=15, state='disabled')
        self.log_scrollbar = ttk.Scrollbar(self.log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        self.log_scrollbar.pack(side='right', fill='y')
    
    def on_scale_change(self, value):
        """当滑动条变化时更新输入框"""
        try:
            score = int(float(value))
            self.skip_score.set(score)
        except ValueError:
            pass
    
    def on_entry_change(self, event):
        """当输入框变化时更新滑动条"""
        try:
            score = int(self.score_entry.get())
            if 0 <= score <= 100:
                self.skip_score.set(score)
            else:
                messagebox.showerror("错误", "分数必须在0-100之间")
                self.skip_score.set(80)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            self.skip_score.set(80)
    
    def browse_voice_file(self):
        filename = filedialog.askopenfilename(
            title="选择目标音色文件",
            filetypes=[("WAV文件", "*.wav"), ("所有文件", "*.*")]
        )
        if filename:
            self.target_voice_path.set(filename)
    
    def load_config(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding='utf-8') as f:
                    config = json.load(f)
                    self.username.set(config.get("username", ""))
                    self.password.set(config.get("password", ""))
                    self.skip_score.set(config.get("skip_score", 80))
                    self.target_voice_path.set(config.get("target_voice_path", "draft/target_voice.wav"))
        except Exception as e:
            self.log_message(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        try:
            config = {
                "username": self.username.get(),
                "password": self.password.get(),
                "skip_score": self.skip_score.get(),
                "target_voice_path": self.target_voice_path.get()
            }
            with open("config.json", "w", encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log_message("配置已保存")
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}")
    
    def log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
    
    def toggle_run(self):
        if self.is_running:
            self.is_running = False
            self.start_btn.config(text="开始运行")
            self.log_message("程序已停止")
        else:
            if not self.username.get() or not self.password.get():
                messagebox.showerror("错误", "请输入用户名和密码")
                return
            
            # 确保tmp目录存在
            os.makedirs("tmp", exist_ok=True)
            
            if not os.path.exists(self.target_voice_path.get()):
                messagebox.showerror("错误", "目标音色文件不存在")
                return
            
            self.is_running = True
            self.start_btn.config(text="停止运行")
            self.save_config()
            
            # 在新线程中运行主程序
            thread = threading.Thread(target=self.run_main)
            thread.daemon = True
            thread.start()
    
    def run_main(self):
        try:
            # 确保tmp目录存在
            os.makedirs("tmp", exist_ok=True)
            
            self.log_message("[main] 正在检测环境并加载神经网络。")
            self.log_message(f"[main] 运行在: {platform.system()}")
            
            fif = FiFWebClient()
            
            # 初始化语音合成器
            speaker = Speaker(
                "tts_models/multilingual/multi-dataset/your_tts",
                "cpu",
                "VirtualPipeMic",
                self.target_voice_path.get(),
            )
            
            self.log_message("[main] FiF口语,启动!")
            
            # 登录
            user_info = fif.login(self.username.get(), self.password.get())
            self.log_message(
                "[main] {}登录成功。用户ID为{}。".format(
                    user_info["data"]["realName"], user_info["data"]["userId"]
                )
            )
            
            # 获取任务列表
            task_list = fif.get_task_list(fif.get_page())["data"]["ttiList"]
            
            for i, task in enumerate(task_list):
                if not self.is_running:
                    break
                    
                ttd_list = fif.get_ttd_list(fif.get_page(), task["id"])
                self.log_message(
                    "[main] 正在开始第{}个任务。任务代码为{}。任务名为{}。".format(i + 1, task["id"], task["taskName"])
                )
                
                for j, ttd in enumerate(ttd_list["data"]["ttdList"]):
                    if not self.is_running:
                        break
                        
                    self.log_message(
                        "[main] 正在开始第{}个单元。单元代码为{}。单元名为{}。".format(
                            j + 1, ttd["id"], ttd["unitName"]
                        )
                    )
                    
                    unit_info = fif.get_unit_info(fif.get_page(), ttd["unitid"], task["taskId"])["data"]
                    self.log_message("[main] 正在开始第{}个单元。单元代码为{}。".format(j + 1, unit_info["id"]))
                    
                    for k, level in enumerate(unit_info["levelList"]):
                        if not self.is_running:
                            break
                            
                        if level["levelScore"] >= self.skip_score.get():
                            self.log_message("[main] 等级{}超过目标分数。已跳过。".format(level["levelName"]))
                            continue
                            
                        self.log_message(
                            "[main] 正在开始第{}个等级。等级代码为{}。等级名为{}。".format(
                                k + 1, level["levelId"], level["levelName"]
                            )
                        )
                        
                        fif.start_level_test(
                            fif.get_page(),
                            speaker,
                            unit_id=unit_info["id"],
                            task_id=task["id"],
                            level_id=level["levelId"],
                        )
                        
                        self.log_message("[main] 第{}个等级完成。".format(k + 1))
            
            self.log_message("[main] 所有任务已完成!")
            
        except Exception as e:
            self.log_message(f"[main] 发生错误: {str(e)}")
        
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(text="开始运行"))

def main():
    # 确保必要的目录存在
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("draft", exist_ok=True)
    
    root = tk.Tk()
    app = FiFApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()