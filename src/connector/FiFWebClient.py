import json
import re
from typing import Dict, Any

from playwright.sync_api import Page, sync_playwright


class FiFWebClient:
    urls = {
        "login": "https://www.fifedu.com/iplat/fifLogin/index.html?v=5.3.3",
        "ai_task": "https://static.fifedu.com/static/fiforal/kyxl-web-static/student-h5/index.html#/pages/teaching/teaching",
        "unit_test": "https://static.fifedu.com/static/fiforal/kyxl-web-static/student-h5/index.html#/pages/webView/testWebView/testWebView?userId={}&taskId={}&unitId={}&gId={}",
    }
    api_urls = {
        "get_user_info": "https://www.fifedu.com/iplatform-zjzx/common/connect",
        "get_task_list": "https://moral.fifedu.com/kyxl-app/stu/task/teaTaskList",
        "get_task_detail": "https://moral.fifedu.com/kyxl-app/task/stu/teaTaskDetail",
        "get_unit_info": "https://moral.fifedu.com/kyxl-app/stu/column/stuUnitInfo?unitId={}&taskId={}",
        "post_test_results": "https://moral.fifedu.com/kyxl-app-challenge/evaluation/submitChallengeResults",
        "get_test_info": "https://moral.fifedu.com/kyxl-app/column/getLevelInfo",
    }
    user_auth = {"token": None, "source": None}
    user_info = None

    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
        )
        self.context = self.browser.new_context(permissions=["microphone"])
        self.page = self.context.new_page()

    def __del__(self):
        self.browser.close()
        self.playwright.stop()

    def login(self, username, password):
        self.page.goto(self.urls["login"], timeout=60000)
        self.page.fill('input[name="user"]', username)
        self.page.fill('input[name="pass"]', password)
        self.page.get_by_role("button", name="登录").click()
        self.page.wait_for_load_state("networkidle", timeout=60000)
        link = self.page.locator("span", has_text="FiF口语训练系统")
        with self.page.expect_popup() as fif_page:
            link.first.click()
        page1 = fif_page.value
        
        page1.wait_for_load_state("networkidle")
        self.user_auth["token"] = page1.evaluate(
            "localStorage.getItem('Authorization')"
        )
        self.user_auth["source"] = page1.evaluate("localStorage.getItem('source')")
        page1.close()
        if self.user_auth["token"] is None or self.user_auth["token"] == "":
            raise Exception("登录失败")
        return self.get_user_info()

    def get_user_info(self):
        if self.user_info is not None:
            return self.user_info
        else:
            response = self.page.request.fetch(
                self.api_urls["get_user_info"], method="GET"
            )
            if response.status != 200:
                raise Exception("获取用户信息失败")
            self.user_info = json.loads(response.body())
            return self.user_info

    def get_task_list(self, page):
        response = page.request.fetch(
            self.api_urls["get_task_list"],
            method="post",
            headers={
                "Authorization": "Bearer " + self.user_auth["token"], # type: ignore
                "source": self.user_auth["source"],
            },
            form={
                "userId": self.get_user_info()["data"]["userId"],
                "status": 1,
                "page": 1,
            },
        )
        json_data = response.json()
        if json_data["status"] == -1:
            raise Exception("获取任务列表失败")
        return json_data

    def get_ttd_list(self, page, task_id):
        response = page.request.fetch(
            self.api_urls["get_task_detail"],
            method="post",
            form={
                "userId": self.get_user_info()["data"]["userId"],
                "id": task_id,
            },
            headers={
                "Authorization": "Bearer " + self.user_auth["token"], # type: ignore
                "source": self.user_auth["source"],
            },
        )
        json_data = response.json()
        if json_data["status"] == -1:
            raise Exception("获取任务详情失败")
        return json_data

    def get_unit_info(self, page, unit_id, task_id):
        response = page.request.fetch(
            self.api_urls["get_unit_info"].format(unit_id, task_id),
            method="get",
            headers={
                "Authorization": "Bearer " + self.user_auth["token"], # type: ignore
                "source": self.user_auth["source"],
            },
        )
        json_data = response.json()
        if json_data["status"] == -1:
            raise Exception("获取单元信息失败")
        return json_data

    def start_level_test(self, page: Page, speaker, unit_id, task_id, level_id):
        print(f"尝试加载{level_id}答案。")
        try:
            answer = self.get_level_answer(page, level_id)
            if answer:
                print(f"已加载{len(answer)}条答案。")
            else:
                print("未找到答案。")
        except Exception as e:
            raise Exception(f"加载答案失败: {str(e)}")
        
        page.goto(
            self.urls["unit_test"].format(
                self.get_user_info()["data"]["userId"],
                task_id,
                unit_id,
                level_id,
            )
        )
        page.wait_for_load_state("load")
        page.frame_locator("iframe").get_by_role("tab", name="挑战").click()
        page.frame_locator("iframe").get_by_role("button", name="开始挑战").click()
        page.wait_for_timeout(3000)
        
        for answer_index, answer_text in enumerate(answer):
            print(f"等待开始录音。")
            page.frame_locator("iframe").get_by_text("结束录音").is_enabled(timeout=0)
            print(f"正在回答第{answer_index + 1}条。答案，内容为：\n{answer_text}")
            speaker.speak(answer_text)
            print(f"第{answer_index + 1}条回答完成。")
            page.frame_locator("iframe").get_by_text("结束录音").click()
            
        print("挑战完成。等待提交。")
        page.get_by_text("AI 评分").is_enabled(timeout=0)
        print("当前单元结束。")

    def get_level_answer(self, page: Page, level_id):
        response = page.request.fetch(
            self.api_urls["get_test_info"],
            method="post",
            form={
                "levelId": level_id,
            },
            headers={
                "Authorization": "Bearer " + self.user_auth["token"], # type: ignore
                "source": self.user_auth["source"],
            },
        ).json()
        
        if response["status"] != 1:
            raise Exception("获取答案失败")
            
        # 获取挑战模式的内容
        challenge_modes = [_i for _i in response["data"]["content"]["moshi"] if _i["name"] == "挑战"]
        if not challenge_modes:
            raise Exception("未找到挑战模式内容")
            
        qcontent = challenge_modes[0]["question"]["qcontent"]
        
        # 处理没有item字段的情况
        if "item" not in qcontent or not qcontent["item"]:
            qcontent = self._process_qcontent_without_item(qcontent)
            
        # 根据是否有photo字段选择不同的答案提取方式
        if "photo" in qcontent["item"][0]["questions"][0]:
            answer = self.get_playrole_type_answer(qcontent)
        else:
            answer = []
            for _i in qcontent["item"]:
                for _j in _i["questions"]:
                    answer.append(_j["title"])
                    
        return answer

    def _process_qcontent_without_item(self, qcontent: Dict[str, Any]) -> Dict[str, Any]:
        # 处理没有item字段的qcontent数据
        text = qcontent.get("text", "")
        if not text:
            return qcontent

        # 统一省略号为英文句号
        text = text.replace('...', '.').replace('…', '.')    
        # 按分隔符拆分为句子并过滤空段
        text_list = [seg.strip() for seg in text.split('##') if seg.strip()]
        
        # 分析角色出现情况
        roles_present = {
            "m1": any("m1:" in t for t in text_list),
            "w1": any("w1:" in t for t in text_list),
            "m2": any("m2:" in t for t in text_list),
            "w2": any("w2:" in t for t in text_list),
        }
        
        # 角色替换逻辑 
        
        # 情况1: 有两男或两女对话，进行角色替换
        if (roles_present["m2"] or roles_present["w2"]) and not (roles_present["m1"] and roles_present["w1"]):
            for i, text_seg in enumerate(text_list):
                # 两女对话
                if roles_present["w2"] and not roles_present["m1"] and "w2:" in text_seg:
                    text_list[i] = text_seg.replace("w2:", "m1:")
                # 两男对话
                elif roles_present["m2"] and not roles_present["w1"] and "m2:" in text_seg:
                    text_list[i] = text_seg.replace("m2:", "w1:")
        
        # 情况2: 三人对话，过滤并替换角色
        elif roles_present["m2"] or roles_present["w2"]:
            # 两女一男
            # 男生的台词去除
            if roles_present["w2"] and not roles_present["m2"]:
                filtered_text_list = []
                for text_seg in text_list:
                    if "m1:" in text_seg or "w2:" in text_seg:
                        if "w2:" in text_seg:
                            # 将女2替换为男1
                            text_seg = text_seg.replace("w2:", "m1:")
                        filtered_text_list.append(text_seg)
                text_list = filtered_text_list
            
            # 两男一女
            # 女生的台词去除
            elif roles_present["m2"] and not roles_present["w2"]:
                filtered_text_list = []
                for text_seg in text_list:
                    if "w1:" in text_seg or "m2:" in text_seg:
                        if "m2:" in text_seg:
                            # 将男2替换为女1
                            text_seg = text_seg.replace("m2:", "w1:")
                        filtered_text_list.append(text_seg)
                text_list = filtered_text_list
        
        # 角色排序逻辑
        if text_list and ("m1:" in text_list[0] or "w1:" in text_list[0]):
            first_role = "m1" if "m1:" in text_list[0] else "w1"
            
            def role_key(text_seg):
                if first_role == "m1":
                    return 0 if "w1:" in text_seg else 1
                else:
                    return 0 if "m1:" in text_seg else 1
            
            text_list.sort(key=role_key)
        
        # 特殊文本替换
        #for i, text_seg in enumerate(text_list):
            #if text_seg == "OK":
                #text_list[i] = "Okay"
        
        # 构建新的qcontent结构
        questions = [{"text": "", "title": t} for t in text_list]
        
        return {
            "item": [
                {
                    "questions": questions,
                    "title": ""
                }
            ],
            "titlenum": "1",
            "description": "",
            "sample": ""
        }

    def get_playrole_type_answer(self, qcontent):
        answer = {}
        role_init_count = {}
        
        # 初始化角色位置计数
        for _i in qcontent["item"]:
            for _j in _i["questions"]:
                locate = -1
                rec_time = _j.get("recordingTime", "").strip()
                if rec_time:
                    parts = rec_time.split("#")
                    # 检查分割后是否有有效值
                    if parts and parts[0].strip().isdigit():
                        try:
                            locate = int(parts[0].strip())
                        except (ValueError, IndexError):
                            locate = -1
                
                role_init_count[_j["photo"]] = locate if locate != -1 else 0
        
        # 修复点2：同步修改答案处理逻辑
        for _i in qcontent["item"]:
            for _j in _i["questions"]:
                locate = -1
                rec_time = _j.get("recordingTime", "").strip()
                if rec_time:
                    parts = rec_time.split("#")
                    if parts and parts[0].strip().isdigit():
                        try:
                            locate = int(parts[0].strip())
                        except (ValueError, IndexError):
                            locate = -1
                
                answer_string = _j["title"]
                answer_string = re.sub(r'<[^>]+>', '', answer_string)
                
                if _j["photo"] not in answer:
                    answer[_j["photo"]] = []
                
                # 确保locate有效
                if locate != -1 and locate > 0:  
                    while len(answer[_j["photo"]]) < locate - 1:
                        answer[_j["photo"]].append("")
                    if locate <= len(answer[_j["photo"]]):
                        answer[_j["photo"]][locate - 1] += answer_string
                    else:
                        answer[_j["photo"]].append(answer_string)
                else:
                    answer[_j["photo"]].append(answer_string)
        
        result = []
        sample = qcontent.get("sample", "")
        sample_roles = sample.split("#") if sample else list(answer.keys())
        
        for role in sample_roles:
            if role in answer:
                result.extend(answer[role])
                
        return result

    def get_page(self):
        return self.page
        
    def get_context(self):
        return self.context
        
    def get_browser(self):
        return self.browser
        
    def get_playwright(self):
        return self.playwright
        
    def get_urls(self):
        return self.urls