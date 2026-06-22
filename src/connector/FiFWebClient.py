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
        # 添加稳定性参数，避免 Chromium 崩溃导致 EPIPE
        launch_args = [
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
        ]
        try:
            self.browser = self.playwright.chromium.launch(
                headless=False,
                args=launch_args,
            )
        except Exception:
            # 回退：不带额外参数启动
            self.browser = self.playwright.chromium.launch(
                headless=False,
            )
        self.context = self.browser.new_context(permissions=["microphone"])
        self.page = self.context.new_page()
        self._logger = None

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

    def set_logger(self, fn):
        """设置日志回调函数，用于将日志回传到 GUI。"""
        self._logger = fn

    def _log_msg(self, msg):
        """内部日志方法：优先使用回调，兜底 print。"""
        if self._logger:
            self._logger(msg)
        print(msg)

    def manual_login(self):
        """打开登录页面，等待用户手动完成登录，然后提取授权令牌。"""
        import time

        self._log_msg("[FiF] 正在打开登录页面...")
        self.page.goto(self.urls["login"], timeout=60000)
        self._log_msg("[FiF] 请在浏览器中手动完成登录（最多等待 10 分钟）...")

        timeout = 600  # 10 分钟
        start = time.time()

        while time.time() - start < timeout:
            try:
                # 检测登录成功的标志：页面出现了 "FiF口语训练系统" 入口链接
                link = self.page.locator("span", has_text="FiF口语训练系统")
                if link.count() > 0:
                    self._log_msg("[FiF] 检测到登录成功！")
                    break

                # 兜底检测：已跳转离开登录页面
                current_url = self.page.url
                if "fifLogin" not in current_url:
                    self._log_msg("[FiF] 检测到页面跳转，登录成功！")
                    break
            except Exception:
                pass

            time.sleep(3)
        else:
            raise Exception("等待手动登录超时（10 分钟），请重试。")

        # 通过点击 "FiF口语训练系统" 弹窗进入，这样才能继承登录状态
        link = self.page.locator("span", has_text="FiF口语训练系统")
        if link.count() > 0:
            self._log_msg("[FiF] 正在通过入口进入口语训练系统（弹窗方式）...")
            try:
                with self.page.expect_popup(timeout=30000) as fif_page:
                    link.first.click()
                page1 = fif_page.value
                page1.wait_for_load_state("domcontentloaded", timeout=30000)
                page1.wait_for_timeout(3000)  # 等 SPA 初始化完毕
                # 提取令牌
                self.user_auth["token"] = page1.evaluate(
                    "localStorage.getItem('Authorization')"
                )
                self.user_auth["source"] = page1.evaluate(
                    "localStorage.getItem('source')"
                )
                # 用弹窗页面替换主页面（弹窗有正确的登录状态）
                try:
                    self.page.close()
                except Exception:
                    pass
                self.page = page1
            except Exception as e:
                self._log_msg(f"[FiF] 弹窗方式失败: {e}，尝试当前页面继续...")
                self.page.wait_for_timeout(3000)
                self.user_auth["token"] = self.page.evaluate(
                    "localStorage.getItem('Authorization')"
                )
                self.user_auth["source"] = self.page.evaluate(
                    "localStorage.getItem('source')"
                )
        else:
            # 兜底：已跳转但没有入口链接，从当前页面提取令牌
            self._log_msg("[FiF] 未找到入口链接，从当前页面提取令牌...")
            self.page.wait_for_timeout(3000)
            self.user_auth["token"] = self.page.evaluate(
                "localStorage.getItem('Authorization')"
            )
            self.user_auth["source"] = self.page.evaluate(
                "localStorage.getItem('source')"
            )

        # 打印 localStorage keys 诊断
        try:
            ls_keys = self.page.evaluate(
                """() => {
                    const keys = [];
                    for (let i = 0; i < localStorage.length; i++) {
                        keys.push(localStorage.key(i));
                    }
                    return keys;
                }"""
            )
            self._log_msg(f"[FiF] 登录后 localStorage keys: {ls_keys}")
        except Exception as e:
            self._log_msg(f"[FiF] 读取 localStorage keys 失败: {e}")

        if not self.user_auth["token"]:
            raise Exception("登录失败：未能获取授权令牌。请确认已成功登录。")

        self._log_msg("[FiF] 登录令牌获取成功！")
        return self.get_user_info()

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

        token = self.user_auth.get("token")
        token_preview = (token[:20] + "...") if token and len(token) > 20 else token
        self._log_msg(f"[FiF] 提取用户信息 (token={token_preview})...")

        # 从当前页面 dump 全部 localStorage
        ls_data = {}
        try:
            ls_data = self.page.evaluate(
                """() => {
                    const data = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        const val = localStorage.getItem(key);
                        // 截断过长的值以便日志显示
                        data[key] = val && val.length > 100 ? val.slice(0, 100) + '...(truncated)' : val;
                    }
                    return data;
                }"""
            )
            self._log_msg(f"[FiF] localStorage 全部内容: {json.dumps(ls_data, ensure_ascii=False)}")
        except Exception as e:
            self._log_msg(f"[FiF] localStorage 读取失败: {e}")

        userId = None
        realName = None

        # 尝试1：从 localStorage 常见 key 直接取
        id_keys = ["userId", "user_id", "uid", "id"]
        name_keys = ["realName", "userName", "nickname", "name", "username"]
        for key in id_keys:
            if key in ls_data and ls_data[key]:
                userId = str(ls_data[key])
                self._log_msg(f"[FiF] 从 localStorage[{key}] 获取 userId={userId}")
                break
        for key in name_keys:
            if key in ls_data and ls_data[key]:
                realName = str(ls_data[key])
                self._log_msg(f"[FiF] 从 localStorage[{key}] 获取 realName={realName}")
                break

        # 尝试2：从 JWT token 解码
        if not userId:
            try:
                import base64
                if token and token.count(".") == 2:
                    payload_part = token.split(".")[1]
                    padding = 4 - len(payload_part) % 4
                    if padding != 4:
                        payload_part += "=" * padding
                    decoded = base64.urlsafe_b64decode(payload_part)
                    jwt_payload = json.loads(decoded)
                    self._log_msg(f"[FiF] JWT payload: {json.dumps(jwt_payload, ensure_ascii=False)}")
                    # 遍历所有可能的 userId 字段
                    for field in ["userId", "user_id", "sub", "id", "uid", "jti"]:
                        if field in jwt_payload and jwt_payload[field]:
                            userId = str(jwt_payload[field])
                            self._log_msg(f"[FiF] 从 JWT.{field} 获取 userId={userId}")
                            break
                    for field in ["realName", "name", "userName", "nickname", "preferred_username"]:
                        if field in jwt_payload and jwt_payload[field]:
                            realName = str(jwt_payload[field])
                            self._log_msg(f"[FiF] 从 JWT.{field} 获取 realName={realName}")
                            break
            except Exception as e:
                self._log_msg(f"[FiF] JWT 解码失败: {e}")

        # 尝试3：从 localStorage JSON 对象中提取
        if not userId:
            for key, val in ls_data.items():
                if val is None:
                    continue
                try:
                    obj = json.loads(str(val))
                    if isinstance(obj, dict):
                        self._log_msg(f"[FiF] localStorage[{key}] 是 JSON 对象: keys={list(obj.keys())}")
                        for field in ["userId", "user_id", "id", "uid"]:
                            if field in obj and obj[field]:
                                userId = str(obj[field])
                                self._log_msg(f"[FiF] 从 localStorage[{key}].{field} 获取 userId={userId}")
                                break
                        for field in ["realName", "name", "userName", "nickname"]:
                            if field in obj and obj[field]:
                                realName = str(obj[field])
                                break
                        if userId:
                            break
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

        if not userId:
            raise Exception(
                "无法获取 userId。请将上面的 'localStorage 全部内容' 日志贴给开发者。\n"
            )

        self.user_info = {
            "data": {
                "userId": userId,
                "realName": realName or str(userId),
            }
        }
        self._log_msg(f"[FiF] 用户信息提取成功: userId={userId}, realName={realName}")
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
        self._log_msg(f"尝试加载 {level_id} 答案...")
        try:
            answer = self.get_level_answer(page, level_id, level_name)
            if answer:
                self._log_msg(f"已加载 {len(answer)} 条答案。")
            else:
                self._log_msg("未找到答案。")
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
            self._log_msg(f"回答 {answer_index + 1}/{len(answer)}: {answer_text[:60]}...")
            speaker.speak(answer_text)
            print(f"第{answer_index + 1}条回答完成。")
            page.frame_locator("iframe").get_by_text("结束录音").click()

        self._log_msg("挑战完成，等待 AI 评分...")
        page.get_by_text("AI 评分").is_enabled(timeout=0)

        # 提取分数
        score = None
        try:
            page.wait_for_timeout(2000)  # 等评分动画完成
            frame = page.frame_locator("iframe")
            # 尝试找包含分数的文本
            try:
                score_text = frame.locator("text=/[0-9]+\\s*(分|score|Score)/i").first.text_content(timeout=5000)
                nums = re.findall(r'(\d+)', score_text)
                if nums:
                    score = int(nums[0])
            except Exception:
                pass
            # 后备：找评分数字元素
            if score is None:
                score_elements = frame.locator("[class*=score], [class*=result], [class*=grade]")
                for i in range(min(score_elements.count(), 10)):
                    text = score_elements.nth(i).text_content() or ""
                    nums = re.findall(r'(\d+)', text)
                    if nums:
                        score = int(nums[0])
                        break
            if score is not None:
                self._log_msg(f"🎯 当前等级得分: {score}")
            else:
                self._log_msg("未能获取分数（页面结构可能已变更）")
        except Exception as e:
            self._log_msg(f"获取分数失败: {e}")

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
            # 非对话模式：获取答案文本（title 或 comment）
            answer = []
            for _i in qcontent.get("item", []):
                for _j in _i.get("questions", []):
                    # 优先取 title，为空则取 comment
                    text = (_j.get("title") or "").strip()
                    if not text:
                        text = (_j.get("comment") or "").strip()
                    # 去掉 HTML 标签
                    text = re.sub(r'<[^>]+>', '', text).strip()
                    if text:
                        answer.append(text)
            return answer


    def get_page(self):
        return self.page

    def reset_page(self):
        """重置页面释放内存，保留登录会话。"""
        try:
            old_page = self.page
            old_page.goto("about:blank")  # 释放页面资源
            self.page = self.context.new_page()  # 创建新页面
            old_page.close()  # 关闭旧页面
            self._log_msg("[FiF] 页面已重置，释放内存")
        except Exception as e:
            self._log_msg(f"[FiF] 页面重置失败: {e}")

    def get_context(self):
        return self.context
        
    def get_browser(self):
        return self.browser
        
    def get_playwright(self):
        return self.playwright
        
    def get_urls(self):
        return self.urls