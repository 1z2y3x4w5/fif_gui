import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import re
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
        # 跳过规则, 每项为 dict {unit_pattern, chapter_type, chapter_num}
        self.skip_rules = []
        # 等级类型规则: 每项为 dict {unit_pattern, level_pattern, level_type}
        # level_type 使用 "Role-play"（对话） 或 "Read"（跟读）
        self.level_type_rules = []
        
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

        # 目标音色
        ttk.Label(self.login_frame, text="目标音色文件:").grid(row=2, column=0, sticky='w', pady=5)
        ttk.Entry(self.login_frame, textvariable=self.target_voice_path, width=30).grid(row=2, column=1, pady=5, padx=5)
        ttk.Button(self.login_frame, text="浏览", command=self.browse_voice_file).grid(row=2, column=2, pady=5, padx=5)

        ttk.Label(self.login_frame, text="跳过分数:").grid(row=3, column=0, sticky='w', pady=5)

        # 滑动条和输入框的框架
        score_frame = ttk.Frame(self.login_frame)
        score_frame.grid(row=3, column=1, sticky='ew', pady=5, padx=5)
        
        self.score_scale = ttk.Scale(score_frame, from_=0, to=100, variable=self.skip_score, 
                                    orient='horizontal', command=self.on_scale_change)
        self.score_scale.pack(side='left', fill='x', expand=True)
        
        self.score_entry = ttk.Entry(score_frame, textvariable=self.skip_score, width=5)
        self.score_entry.pack(side='right', padx=(5, 0))
        self.score_entry.bind('<Return>', self.on_entry_change)
        self.score_entry.bind('<FocusOut>', self.on_entry_change)
        
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
        
        self.log_text = tk.Text(self.log_frame, height=22, state='disabled')
        self.log_scrollbar = ttk.Scrollbar(self.log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        self.log_scrollbar.pack(side='right', fill='y')

        # 跳过规则标签页
        self.skip_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.skip_frame, text="跳过设置")

        ttk.Label(self.skip_frame, text="单元匹配文本 (例如: Unit 1):").grid(row=0, column=0, sticky='w', pady=5)
        self.skip_unit_entry = ttk.Entry(self.skip_frame, width=25)
        self.skip_unit_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(self.skip_frame, text="等级类型:").grid(row=1, column=0, sticky='w', pady=5)
        self.chapter_type = tk.StringVar(value="Any")
        self.chapter_type_combo = ttk.Combobox(self.skip_frame, textvariable=self.chapter_type, width=22)
        self.chapter_type_combo['values'] = ("Any", "Role-play", "Expressions", "Group discussion", "Read aloud", "Vocabulary", "Grammar", "Listening")
        self.chapter_type_combo.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(self.skip_frame, text="等级编号 (可选):").grid(row=2, column=0, sticky='w', pady=5)
        self.chapter_num_entry = ttk.Entry(self.skip_frame, width=10)
        self.chapter_num_entry.grid(row=2, column=1, pady=5, padx=5, sticky='w')

        add_btn = ttk.Button(self.skip_frame, text="添加跳过规则", command=self.add_skip_rule)
        add_btn.grid(row=3, column=0, pady=10)

        remove_btn = ttk.Button(self.skip_frame, text="删除选中规则", command=self.remove_selected_rule)
        remove_btn.grid(row=3, column=1, pady=10, sticky='w')

        # 列表显示当前规则
        self.skip_listbox = tk.Listbox(self.skip_frame, height=8)
        self.skip_listbox.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=5)

        self.skip_frame.columnconfigure(1, weight=1)
        # 等级类型规则标签页（放在 create_widgets 内）
        self.level_type_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.level_type_frame, text="等级类型规则")

        ttk.Label(self.level_type_frame, text="单元匹配文本: (例如: Unit 1)").grid(row=0, column=0, sticky='w', pady=5)
        self.lt_unit_entry = ttk.Entry(self.level_type_frame, width=25)
        self.lt_unit_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(self.level_type_frame, text="等级匹配文本: (例如: Role-play 1 / Group discussion 1 / Expressions 1)").grid(row=1, column=0, sticky='w', pady=5)
        self.lt_level_entry = ttk.Entry(self.level_type_frame, width=25)
        self.lt_level_entry.grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(self.level_type_frame, text="类型:Role-play为对话，Read为跟读").grid(row=2, column=0, sticky='w', pady=5)
        self.level_type_var = tk.StringVar(value="Role-play")
        self.level_type_combo = ttk.Combobox(self.level_type_frame, textvariable=self.level_type_var, state='readonly', width=22)
        self.level_type_combo['values'] = ("Role-play", "Read")
        self.level_type_combo.grid(row=2, column=1, pady=5, padx=5)

        add_lt_btn = ttk.Button(self.level_type_frame, text="添加等级类型规则", command=self.add_level_type_rule)
        add_lt_btn.grid(row=3, column=0, pady=10)

        remove_lt_btn = ttk.Button(self.level_type_frame, text="删除选中规则", command=self.remove_selected_level_type_rule)
        remove_lt_btn.grid(row=3, column=1, pady=10, sticky='w')

        # 列表显示当前等级类型规则
        self.lt_listbox = tk.Listbox(self.level_type_frame, height=8)
        self.lt_listbox.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=5)

        self.level_type_frame.columnconfigure(1, weight=1)
    
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
                    # load skip rules if any
                    self.skip_rules = config.get("skip_rules", []) or []
                    # load level type rules if any
                    self.level_type_rules = config.get("level_type_rules", []) or []
                    # refresh listbox if widget exists
                    try:
                        self.refresh_skip_listbox()
                        self.refresh_level_type_listbox()
                    except Exception:
                        pass
        except Exception as e:
            self.log_message(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        try:
            config = {
                "username": self.username.get(),
                "password": self.password.get(),
                "skip_score": self.skip_score.get(),
                "target_voice_path": self.target_voice_path.get(),
            }
            # persist skip rules
            config["skip_rules"] = self.skip_rules
            # persist level type rules
            config["level_type_rules"] = self.level_type_rules
            with open("config.json", "w", encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log_message("配置已保存")
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}")

    def add_skip_rule(self):
        unit_text = self.skip_unit_entry.get().strip()
        chapter_type = self.chapter_type.get().strip()
        chapter_num = self.chapter_num_entry.get().strip()

        if not unit_text:
            messagebox.showerror("错误", "请填写单元匹配文本，例如: Unit 1")
            return

        rule = {
            "unit_pattern": unit_text,
            "chapter_type": chapter_type,
            "chapter_num": chapter_num,
        }
        self.skip_rules.append(rule)
        self.refresh_skip_listbox()

    def add_level_type_rule(self):
        unit_text = self.lt_unit_entry.get().strip()
        level_text = self.lt_level_entry.get().strip()
        level_type = self.level_type_var.get().strip()

        if not unit_text and not level_text:
            messagebox.showerror("错误", "请填写单元或等级匹配文本至少一项")
            return

        rule = {
            "unit_pattern": unit_text,
            "level_pattern": level_text,
            "level_type": level_type,
        }
        self.level_type_rules.append(rule)
        self.refresh_level_type_listbox()

    def remove_selected_level_type_rule(self):
        sel = self.lt_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            self.level_type_rules.pop(idx)
        except Exception:
            pass
        self.refresh_level_type_listbox()

    def refresh_level_type_listbox(self):
        self.lt_listbox.delete(0, 'end')
        for r in self.level_type_rules:
            up = r.get('unit_pattern', '')
            lp = r.get('level_pattern', '')
            lt = r.get('level_type', '')
            if lp:
                text = f"{up} · {lp} · {lt}"
            else:
                text = f"{up} · {lt}"
            self.lt_listbox.insert('end', text)

    def _apply_level_type_rules(self, unit_name: str, level_name: str) -> str:
        """根据用户配置的规则决定传入 start_level_test 的 level_name。

        如果匹配到 type 为 Role-play 的规则，会在 level_name 后添加关键词 ' role'，
        以便 FiFWebClient.get_level_answer 能通过检查 'role' 识别为对话类型。
        """
        if not level_name:
            return level_name

        uname = (unit_name or '').lower()
        lname = (level_name or '').lower()

        for r in self.level_type_rules:
            upat = r.get('unit_pattern', '').lower()
            lpat = r.get('level_pattern', '').lower()
            ltype = r.get('level_type', '')

            if upat and upat not in uname:
                continue
            if lpat and lpat not in lname:
                continue

            if ltype == 'Role-play':
                # 如果已经包含 role 则不重复添加
                if 'role' in lname:
                    return level_name
                return level_name + ' role'
            else:
                return level_name

        return level_name

    def remove_selected_rule(self):
        sel = self.skip_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            self.skip_rules.pop(idx)
        except Exception:
            pass
        self.refresh_skip_listbox()

    def refresh_skip_listbox(self):
        # update listbox from skip_rules
        self.skip_listbox.delete(0, 'end')
        for r in self.skip_rules:
            unit = r.get('unit_pattern', '')
            ctype = r.get('chapter_type', 'Any')
            cnum = r.get('chapter_num', '')
            if cnum:
                text = f"{unit} · {ctype} {cnum}"
            else:
                text = f"{unit} · {ctype}"
            self.skip_listbox.insert('end', text)

    def should_skip(self, unit_name: str, level_name: str) -> bool:
        """根据已添加的规则判断是否跳过当前单元/章节。"""
        if not unit_name:
            return False
        for r in self.skip_rules:
            upat = r.get('unit_pattern', '').lower()
            ctype = r.get('chapter_type', 'Any')
            cnum = r.get('chapter_num', '').strip()

            if upat and upat not in unit_name.lower():
                continue

            # 如果选择 Any，则跳过整个单元
            if ctype == 'Any' or not ctype:
                return True

            if not level_name:
                continue
            lname = level_name.lower()
            if ctype.lower() in lname:
                if not cnum:
                    return True
                # 尝试从 level_name 中提取数字并比较
                nums = re.findall(r"(\d+)", level_name)
                if nums and cnum in nums:
                    return True
                # 如果没有数字直接比较全文
                if cnum and cnum in level_name:
                    return True

        return False
    
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

            # 自动检测 GPU
            try:
                import torch
                if torch.cuda.is_available():
                    tts_mode = "cuda"
                    self.log_message(f"[main] 检测到 GPU: {torch.cuda.get_device_name(0)}，使用 CUDA 加速")
                else:
                    tts_mode = "cpu"
                    self.log_message("[main] 未检测到 GPU，使用 CPU 模式（较慢）")
            except Exception:
                tts_mode = "cpu"
                self.log_message("[main] 无法检测 GPU，使用 CPU 模式")

            fif = FiFWebClient()
            fif.set_logger(self.log_message)

            # 初始化语音合成器（YourTTS 本地 GPU）
            speaker = Speaker(
                "tts_models/multilingual/multi-dataset/your_tts",
                tts_mode,
                "VirtualPipeMic",
                self.target_voice_path.get(),
            )
            
            self.log_message("[main] FiF口语,启动!")
            
            # 手动登录：打开浏览器后等待用户手动完成登录
            user_info = fif.manual_login()
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

                        # 判断是否匹配跳过规则（优先于分数判断）
                        unit_name = ttd.get("unitName", "") if isinstance(ttd, dict) else ""
                        level_name = level.get("levelName", "") if isinstance(level, dict) else ""
                        try:
                            if self.should_skip(unit_name, level_name):
                                self.log_message(f"[main] 跳过规则匹配: 单元 {unit_name} 等级 {level_name} 已跳过。")
                                continue
                        except Exception:
                            # 若规则检查出错，忽略并继续
                            pass

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
                            # 根据用户设置的等级类型规则决定传入的 level_name
                            level_name=self._apply_level_type_rules(unit_name, level.get("levelName", "")),
                        )
                        
                        self.log_message("[main] 第{}个等级完成。".format(k + 1))
                        # 每个等级完成后重置页面释放内存，防止 Chromium 崩溃
                        try:
                            fif.reset_page()
                        except Exception:
                            pass

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