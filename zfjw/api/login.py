"""登录（密码 / 验证码）。"""
import base64
import os
import time
import traceback
from typing import Optional
from pyquery import PyQuery as pq
from requests import exceptions


class LoginMixin:
    def prepare_captcha_login(self, state=None, force_captcha=False):
        """登录前置流程：访问登录页 → 解析 CSRF → 获取公钥 → 必要时取验证码图片。

        返回 (data, error) 二元组：
          - 成功：error 为 None，data 含 csrf_token / cookies / modulus /
            exponent / needs_captcha / kaptcha_pic / kaptcha_size / need_verify
          - 失败：data 为 None，error 为可直接作为接口响应返回的字典

        state 为调用方传入的可变字典；在发起验证码请求前置
        state["need_verify"] = True，便于调用方在异常分支区分超时提示。

        force_captcha 为 True 时，无论登录页是否需要验证码都会拉取验证码图片
        （用于兼容旧 /api/get_captcha 接口的行为）。

        注意：网络异常（超时/请求错误）不在此处捕获，由调用方统一处理。
        """
        # 验证必需URL配置
        if not self.login_url:
            return None, {"code": 2333, "msg": "登录URL未设置，请检查base_url配置"}
        if not self.key_url:
            return None, {"code": 2333, "msg": "公钥URL未设置，请检查base_url配置"}
        if not self.kaptcha_url:
            return None, {"code": 2333, "msg": "验证码URL未设置，请检查base_url配置"}

        # 步骤1: 访问登录页面
        print(f"步骤1: 访问登录页面 {self.login_url}")
        req_csrf = self.sess.get(self.login_url, timeout=self.timeout, verify=False)

        if req_csrf.status_code != 200:
            print(f"登录页面访问失败，状态码: {req_csrf.status_code}")
            return None, {"code": 2333, "msg": f"登录页面访问失败，状态码: {req_csrf.status_code}"}

        print(f"登录页面访问成功，内容长度: {len(req_csrf.text)}")

        # 解析CSRF令牌
        print("步骤2: 解析CSRF token")
        doc = pq(req_csrf.text)
        csrf_token = doc("#csrftoken").attr("value")

        if not csrf_token:
            print("CSRF token解析失败")
            return None, {"code": 2333, "msg": "无法获取CSRF token"}

        print(f"CSRF token: {csrf_token}")

        # 缓存当前会话cookies
        pre_cookies = self.sess.cookies.get_dict()
        print(f"当前cookies: {pre_cookies}")

        # 步骤3: 获取公钥
        print(f"步骤3: 获取公钥 {self.key_url}")
        req_pubkey = self.sess.get(self.key_url, timeout=self.timeout, verify=False)

        if req_pubkey.status_code != 200:
            print(f"公钥获取失败，状态码: {req_pubkey.status_code}")
            return None, {"code": 2333, "msg": f"公钥获取失败，状态码: {req_pubkey.status_code}"}

        try:
            pubkey_data = req_pubkey.json()
            print(f"公钥数据: {pubkey_data}")
        except Exception as e:
            print(f"公钥解析失败: {str(e)}")
            return None, {"code": 2333, "msg": f"公钥解析失败: {str(e)}"}

        modulus = pubkey_data.get("modulus")
        exponent = pubkey_data.get("exponent")

        if not modulus or not exponent:
            return None, {"code": 2333, "msg": "公钥数据不完整"}

        # 步骤4: 检查是否需要验证码
        print("步骤4: 检查验证码需求")
        yzm_input = doc("input#yzm")
        needs_captcha = str(yzm_input) != ""
        print(f"需要验证码: {needs_captcha}")

        data = {
            "csrf_token": csrf_token,
            "cookies": pre_cookies,
            "modulus": modulus,
            "exponent": exponent,
            "needs_captcha": needs_captcha,
            "kaptcha_pic": None,
            "need_verify": False,
        }

        if not needs_captcha and not force_captcha:
            return data, None

        print("需要验证码，获取验证码图片")
        if state is not None:
            state["need_verify"] = True
        data["need_verify"] = True

        req_kaptcha = self.sess.get(self.kaptcha_url, timeout=self.timeout, verify=False)

        if req_kaptcha.status_code != 200:
            print(f"验证码获取失败，状态码: {req_kaptcha.status_code}")
            return None, {"code": 2333, "msg": f"验证码获取失败，状态码: {req_kaptcha.status_code}"}

        kaptcha_pic = base64.b64encode(req_kaptcha.content).decode()
        print(f"验证码获取成功，大小: {len(req_kaptcha.content)} bytes")
        data["kaptcha_pic"] = kaptcha_pic
        data["kaptcha_size"] = len(req_kaptcha.content)
        return data, None

    def login(self, sid, password):
        """登录教务系统"""
        print("开始登录流程:")
        print(f"  学号: {sid}")
        print(f"  密码长度: {len(password)}")
        
        need_verify = False
        state = {"need_verify": False}
        try:
            # 步骤1-4: 访问登录页、取 CSRF、取公钥、必要时取验证码
            prep, err = self.prepare_captcha_login(state)
            need_verify = state["need_verify"]
            if err:
                return err

            csrf_token = prep["csrf_token"]
            pre_cookies = prep["cookies"]
            modulus = prep["modulus"]
            exponent = prep["exponent"]

            if prep["needs_captcha"]:
                return {
                    "code": 1001,
                    "msg": "获取验证码成功",
                    "data": {
                        "sid": sid,
                        "csrf_token": csrf_token,
                        "cookies": pre_cookies,
                        "password": password,
                        "modulus": modulus,
                        "exponent": exponent,
                        "kaptcha_pic": prep["kaptcha_pic"],
                        "timestamp": time.time(),
                    },
                }

            # 步骤5: 不需要验证码，直接登录
            print("步骤5: 加密密码并登录")
            
            try:
                encrypt_password_result = self.encrypt_password(password, modulus, exponent)
                print(f"密码加密成功，长度: {len(encrypt_password_result)}")
            except Exception as e:
                print(f"密码加密失败: {str(e)}")
                return {"code": 2333, "msg": f"密码加密失败: {str(e)}"}
            
            # 登录数据
            login_data = {
                "csrftoken": csrf_token,
                "yhm": sid,
                "mm": encrypt_password_result.decode('utf-8'),
            }
            print(f"登录数据: {login_data}")
            
            # 请求登录
            print("步骤6: 执行登录请求")
            if not self.login_url:
                return {"code": 2333, "msg": "登录URL未设置，请检查base_url配置"}
                
            req_login = self.sess.post(
                self.login_url,
                data=login_data,
                timeout=self.timeout,
                verify=False
            )
            
            print(f"登录响应状态码: {req_login.status_code}")
            print(f"登录后cookies: {self.sess.cookies.get_dict()}")
            
            if req_login.status_code != 200:
                return {"code": 2333, "msg": f"登录请求失败，状态码: {req_login.status_code}"}
            
            # 分析登录响应
            print("步骤7: 分析登录响应")
            doc = pq(req_login.text)
            tips = doc("p#tips")
            tip_text = str(tips.text() or "").strip()
            
            # 注意：正方登录页中的 <p id="tips"> 始终存在（默认 display:none），
            # 必须用其文本内容判断，否则登录失败时会返回空的错误消息
            if tip_text:
                print(f"发现错误提示: {tip_text}")
                
                if "用户名或密码" in tip_text:
                    return {"code": 1002, "msg": "用户名或密码不正确"}
                return {"code": 998, "msg": tip_text}
            
            # 检查是否登录成功
            if "退出登录" in req_login.text or "个人信息" in req_login.text or "main" in req_login.text:
                print("✅ 登录成功！")
                self.cookies = self.sess.cookies.get_dict()
                return {"code": 1000, "msg": "登录成功", "data": {"cookies": self.cookies}}
            
            # 如果没有明显的成功标志，检查其他指标
            content_length = len(req_login.text)
            print(f"登录响应内容长度: {content_length}")
            
            return {
                "code": 999,
                "msg": "未知登录状态，请检查响应",
                "debug": {
                    "content_length": content_length,
                    "has_tips": bool(tip_text),
                    "cookies": self.sess.cookies.get_dict()
                }
            }
            
        except exceptions.Timeout as e:
            msg = "获取验证码超时" if need_verify else "登录超时"
            print(f"超时错误: {msg} - {str(e)}")
            return {"code": 1003, "msg": f"{msg}: {str(e)}"}
        
        except exceptions.RequestException as e:
            print(f"请求异常: {str(e)}")
            return {"code": 2333, "msg": f"请求异常: {str(e)}"}        
        except Exception as e:
            print(f"未知错误: {str(e)}")
            traceback.print_exc()
            msg = "获取验证码时未记录的错误" if need_verify else "登录时未记录的错误"
            return {"code": 999, "msg": f"{msg}：{str(e)}"}

    def login_with_kaptcha(
        self, sid, csrf_token, cookies, password, modulus, exponent, kaptcha, **kwargs
    ):
        """通过验证码登录教务系统"""
        print("开始验证码登录流程:")
        print(f"  学号: {sid}")
        print(f"  验证码: {kaptcha}")
        print(f"  CSRF token: {csrf_token}")
        print(f"  Cookies: {cookies}")
        
        # 验证登录URL配置
        if not self.login_url:
            return {"code": 2333, "msg": "登录URL未设置，请检查base_url配置"}
        
        try:
            # 关键修复：把获取验证码阶段拿到的 cookies 写入会话 jar。
            # 正方教务系统前面有负载均衡，route cookie 决定请求落到哪台后端节点，
            # 且会话只存在于该节点上。若只通过 requests 的 cookies 参数传递，
            # 这些 cookie 仅对本次请求生效，重定向和后续请求都会丢失 route，
            # 从而被判定为未登录（返回登录页 / 状态未知）。
            if cookies:
                for name, value in cookies.items():
                    self.sess.cookies.set(name, value)
                print(f"已将登录页 cookies 写入会话: {self.sess.cookies.get_dict()}")
            
            # 加密密码
            encrypt_password_result = self.encrypt_password(password, modulus, exponent)
            print(f"密码加密成功，长度: {len(encrypt_password_result)}")
            
            login_data = {
                "csrftoken": csrf_token,
                "language": "zh_CN",
                "yhm": sid,
                "mm": encrypt_password_result.decode('utf-8'),
                "yzm": kaptcha,
            }
            print(f"验证码登录数据: {login_data}")
            
            # 执行登录（cookies 已写入会话，无需再传 cookies 参数，
            # 否则请求级 cookie 会覆盖会话中服务端刷新后的 route）
            req_login = self.sess.post(
                self.login_url,
                data=login_data,
                timeout=self.timeout,
                verify=False
            )
            
            print(f"验证码登录响应状态码: {req_login.status_code}")
            print(f"验证码登录后cookies: {self.sess.cookies.get_dict()}")
            
            if req_login.status_code != 200:
                return {"code": 2333, "msg": f"验证码登录请求失败，状态码: {req_login.status_code}"}
            
            # 分析登录响应
            resp_text = req_login.text
            doc = pq(resp_text)
            tip_text = str(doc("p#tips").text() or "").strip()
            # 登录失败时正方会把登录页原样返回（含 <input id="csrftoken">），
            # 这是判断"仍然停留在登录页"最可靠的依据
            still_login_page = 'id="csrftoken"' in resp_text
            
            if tip_text and still_login_page:
                print(f"验证码登录错误提示: {tip_text}")
                
                if "验证码" in tip_text:
                    return {"code": 1004, "msg": "验证码输入错误"}
                if "用户名或密码" in tip_text:
                    return {"code": 1002, "msg": "用户名或密码不正确"}
                return {"code": 998, "msg": tip_text}
            
            # 检查是否登录成功
            login_success = (not still_login_page) and (
                "退出登录" in resp_text or "个人信息" in resp_text or "main" in resp_text
            )
            
            # 响应页面陌生（既不是登录页、也没有命中常见标志）时，
            # 直接访问主页做最终判定，避免误报"状态未知"
            if not login_success and not still_login_page:
                print("登录响应中未匹配到常见成功标志，改用主页探针判定登录状态")
                login_success = self._check_logged_in()
            
            if login_success:
                print("✅ 验证码登录成功！")
                self.cookies = self.sess.cookies.get_dict()
                
                # 不同学校系统兼容差异：route 等登录前 cookie 绝不能丢，
                # 否则后续接口请求会被负载均衡调度到没有会话的节点而判定未登录
                for name, value in (cookies or {}).items():
                    if not self.cookies.get(name):
                        self.cookies[name] = value
                        self.sess.cookies.set(name, value)
                
                print(f"登录成功后的 cookies: {self.cookies}")
                return {"code": 1000, "msg": "登录成功", "data": {"cookies": self.cookies}}
            
            # 状态未知：把响应落盘并输出页面标题，便于定位是哪个页面
            page_title = doc("title").text()
            debug_file = self._dump_login_response(resp_text)
            print(f"验证码登录状态未知 -> 页面标题: {page_title!r}, 长度: {len(resp_text)}")
            
            return {
                "code": 999,
                "msg": "验证码登录状态未知",
                "debug": {
                    "content_length": len(resp_text),
                    "final_url": req_login.url,
                    "page_title": page_title,
                    "has_tips": bool(tip_text),
                    "tips": tip_text,
                    "cookies": self.sess.cookies.get_dict(),
                    "original_cookies": cookies,
                    "response_file": debug_file
                }
            }
            
        except exceptions.Timeout as e:
            print(f"验证码登录超时: {str(e)}")
            return {"code": 1003, "msg": f"验证码登录超时: {str(e)}"}        
        except exceptions.RequestException as e:
            print(f"验证码登录请求异常: {str(e)}")
            return {"code": 2333, "msg": f"验证码登录请求异常: {str(e)}"}
        
        except Exception as e:
            print(f"验证码登录未知错误: {str(e)}")
            traceback.print_exc()
            return {"code": 999, "msg": f"验证码登录未知错误: {str(e)}"}

    def _check_logged_in(self) -> bool:
        """
        通过访问教务系统主页判断当前会话是否已经登录。

        正方系统在未登录访问受保护页面时会 302 回 login_slogin.html，
        因此只需确认最终页面不是登录页即可。
        """
        if not self.login_url:
            return False
        
        menu_url = self.login_url.replace("login_slogin.html", "index_initMenu.html")
        try:
            req = self.sess.get(
                menu_url,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True,
            )
            if req.status_code != 200:
                return False
            if "login_slogin.html" in req.url or 'id="csrftoken"' in req.text:
                return False
            return "个人信息" in req.text or "退出登录" in req.text or "main" in req.text
        except Exception as e:
            print(f"登录状态探针请求失败: {str(e)}")
            return False

    def _dump_login_response(self, text: str) -> Optional[str]:
        """把无法识别的登录响应保存到 data/ 目录，便于排查问题"""
        try:
            debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            os.makedirs(debug_dir, exist_ok=True)
            path = os.path.join(debug_dir, f"login_debug_{int(time.time())}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"未知登录状态响应已保存: {path}")
            return path
        except Exception as e:
            print(f"保存登录响应失败: {str(e)}")
            return None
