import json
import re
import logging
from typing import Optional

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)


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
        try:
            if getattr(self, 'browser', None):
                self.browser.close()
        except Exception as e:
            logger.exception("Error closing browser: %s", e)
        try:
            if getattr(self, 'playwright', None):
                self.playwright.stop()
        except Exception as e:
            logger.exception("Error stopping playwright: %s", e)

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

    def start_level_test(self, page: Page, speaker, unit_id, task_id, level_id, level_name: Optional[str] = None):
        print(f"尝试加载{level_id}答案。")
        try:
            answer = self.get_level_answer(page, level_id, level_name)
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

    def get_level_answer(self, page: Page, level_id, level_name: Optional[str] = None):
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
        
        # 判断模式：如果有"roles"字段，则为对话模式，否则为非对话模式
        if "roles" in qcontent:
            # 对话模式：获取"text"标签后的句子
            text = qcontent.get("text", "")
            if not text:
                return []
            
            # 按##分割句子
            sentences = [seg.strip() for seg in text.split('##') if seg.strip()]
            
            roles = qcontent.get("roles", "")
            if not roles:
                # 如果没有roles，按原顺序，去除前缀
                result = [re.sub(r'^\w+:\s*', '', sent) for sent in sentences if ": " in sent]
                return result
            
            # 解析roles，如"w1#m1"
            roles_list = roles.split("#")
            
            # 收集每个角色的句子
            role_sentences = {}
            for sent in sentences:
                if ": " in sent:
                    role, content = sent.split(": ", 1)
                    if role not in role_sentences:
                        role_sentences[role] = []
                    role_sentences[role].append(content.strip())
            
            # 按roles顺序排列句子
            result = []
            for r in roles_list:
                if r in role_sentences:
                    result.extend(role_sentences[r])
            
            return result
        else:
            # 非对话模式：获取"title"标签后的句子
            answer = []
            for _i in qcontent.get("item", []):
                for _j in _i.get("questions", []):
                    title = _j.get("title", "")
                    # 去掉可能的 HTML 标签并修剪
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    if title:
                        answer.append(title)
            return answer


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