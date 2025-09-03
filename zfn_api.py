import base64
import binascii
import json
import re
import time
import traceback
import unicodedata
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
import rsa
from pyquery import PyQuery as pq
from requests import exceptions
from bs4 import BeautifulSoup

# 导入学校配置管理器
try:
    from school_config import school_config_manager
except ImportError:
    school_config_manager = None

RASPIANIE = [
    ["8:00", "8:40"],
    ["8:45", "9:25"],
    ["9:30", "10:10"],
    ["10:30", "11:10"],
    ["11:15", "11:55"],
    ["14:30", "15:10"],
    ["15:15", "15:55"],
    ["16:05", "16:45"],
    ["16:50", "17:30"],
    ["18:40", "19:20"],
    ["19:25", "20:05"],
    ["20:10", "20:50"],
    ["20:55", "21:35"],
]


class Client:
    raspisanie = []
    ignore_type = []

    def __init__(self, cookies={}, **kwargs):
        # 基础配置
        self.school_name = kwargs.get("school_name", "九江学院")  # 默认使用九江学院
        self.base_url = kwargs.get("base_url")
        self.raspisanie = kwargs.get("raspisanie", RASPIANIE)
        self.ignore_type = kwargs.get("ignore_type", [])
        self.detail_category_type = kwargs.get("detail_category_type", [])
        self.timeout = kwargs.get("timeout", 30)  # 设置默认超时时间
        Client.raspisanie = self.raspisanie
        Client.ignore_type = self.ignore_type

        # 从学校配置获取base_url
        if school_config_manager and not self.base_url:
            school_config = school_config_manager.get_school_config(self.school_name)
            if school_config:
                self.base_url = school_config.get("base_url", "")
                print(f"从配置中获取 {self.school_name} 的 base_url: {self.base_url}")

        # 加载学校URL配置
        self.school_urls = None
        if school_config_manager:
            school_config = school_config_manager.get_school_config(self.school_name)
            if school_config:
                self.school_urls = school_config.get('urls', {})

        # 根据配置构造URL
        if self.base_url:
            if not self.base_url.endswith('/'):
                self.base_url = self.base_url + '/'
            def url_from_config(key, default_path):
                if self.school_urls and key in self.school_urls:
                    # 验证base_url有效性
                    if self.base_url:
                        return urljoin(self.base_url, self.school_urls[key])
                if self.base_url:
                    return urljoin(self.base_url, default_path)
                return None
            self.key_url = url_from_config('key', 'xtgl/login_getPublicKey.html')
            self.login_url = url_from_config('login', 'xtgl/login_slogin.html')
            self.kaptcha_url = url_from_config('kaptcha', 'kaptcha')
        else:
            # base_url未配置时的处理
            self.key_url = None
            self.login_url = None
            self.kaptcha_url = None
            print("警告: 未设置 base_url，某些功能可能无法正常工作")
          # 配置HTTP请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.login_url
        }
        
        # 创建会话
        self.sess = requests.Session()
        self.sess.headers.update(self.headers)
        # self.sess.keep_alive = False  # keep_alive 属性已弃用
        self.cookies = cookies
        
        # 初始化会话cookies
        if cookies:
            for key, value in cookies.items():
                self.sess.cookies.set(key, value)

    def get_school_url(self, url_type: str, fallback_path: Optional[str] = None, school_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
        """
        获取学校功能URL，支持多种方式：
        1. 优先使用传入的 school_name 从配置中获取
        2. 其次使用传入的 base_url 拼接
        3. 最后使用实例的配置
        """
        # 如果传入了学校名称，从配置中获取
        if school_name and school_config_manager:
            config_url = school_config_manager.get_school_url(school_name, url_type)
            if config_url:
                print(f"从配置获取URL: {config_url}")
                return config_url
        
        # 优先使用传入的base_url参数
        target_base_url = base_url or self.base_url
        if not target_base_url:
            raise ValueError("base_url 未设置，无法构建 URL")
            
        if not target_base_url.endswith('/'):
            target_base_url += '/'
            
        # 使用当前实例的学校配置
        if not school_name and self.school_urls and url_type in self.school_urls:
            constructed_url = urljoin(target_base_url, self.school_urls[url_type])
            print(f"从实例配置构建URL: {constructed_url}")
            return constructed_url
            
        # 使用默认路径
        if fallback_path:
            constructed_url = urljoin(target_base_url, fallback_path)
            print(f"使用fallback构建URL: {constructed_url}")
            return constructed_url
            
        raise ValueError(f"无法找到功能 {url_type} 的 URL 配置")

    def get_school_base_url(self, school_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
        """获取学校的 base_url"""
        if school_name and school_config_manager:
            config_base_url = school_config_manager.get_base_url(school_name)
            if config_base_url:
                return config_base_url
                
        if base_url:
            return base_url
            
        if self.base_url:
            return self.base_url
            
        raise ValueError("base_url 未设置")
        # 将传入的cookies设置到session中
        if cookies:
            self.sess.cookies.update(cookies)

    def login(self, sid, password):
        """登录教务系统"""
        print(f"开始登录流程:")
        print(f"  学号: {sid}")
        print(f"  密码长度: {len(password)}")
        
        # 验证必需URL配置
        if not self.login_url:
            return {"code": 2333, "msg": "登录URL未设置，请检查base_url配置"}
        if not self.key_url:
            return {"code": 2333, "msg": "公钥URL未设置，请检查base_url配置"}
        if not self.kaptcha_url:
            return {"code": 2333, "msg": "验证码URL未设置，请检查base_url配置"}
        
        need_verify = False
        try:
            # 步骤1: 访问登录页面
            print(f"步骤1: 访问登录页面 {self.login_url}")
            req_csrf = self.sess.get(self.login_url, timeout=self.timeout, verify=False)
            
            if req_csrf.status_code != 200:
                print(f"登录页面访问失败，状态码: {req_csrf.status_code}")
                return {"code": 2333, "msg": f"登录页面访问失败，状态码: {req_csrf.status_code}"}
            
            print(f"登录页面访问成功，内容长度: {len(req_csrf.text)}")
            
            # 解析CSRF令牌
            print("步骤2: 解析CSRF token")
            doc = pq(req_csrf.text)
            csrf_token = doc("#csrftoken").attr("value")
            
            if not csrf_token:
                print("CSRF token解析失败")
                return {"code": 2333, "msg": "无法获取CSRF token"}
            
            print(f"CSRF token: {csrf_token}")
            
            # 缓存当前会话cookies
            pre_cookies = self.sess.cookies.get_dict()
            print(f"当前cookies: {pre_cookies}")
            
            # 获取公钥并加密密码
            print(f"步骤3: 获取公钥 {self.key_url}")
            req_pubkey = self.sess.get(self.key_url, timeout=self.timeout, verify=False)
            
            if req_pubkey.status_code != 200:
                print(f"公钥获取失败，状态码: {req_pubkey.status_code}")
                return {"code": 2333, "msg": f"公钥获取失败，状态码: {req_pubkey.status_code}"}
            
            try:
                pubkey_data = req_pubkey.json()
                print(f"公钥数据: {pubkey_data}")
            except Exception as e:
                print(f"公钥解析失败: {str(e)}")
                return {"code": 2333, "msg": f"公钥解析失败: {str(e)}"}
            
            modulus = pubkey_data.get("modulus")
            exponent = pubkey_data.get("exponent")
            
            if not modulus or not exponent:
                return {"code": 2333, "msg": "公钥数据不完整"}
            
            # 步骤4: 检查是否需要验证码
            print("步骤4: 检查验证码需求")
            yzm_input = doc("input#yzm")
            needs_captcha = str(yzm_input) != ""
            print(f"需要验证码: {needs_captcha}")
            
            if needs_captcha:
                print("需要验证码，获取验证码图片")
                need_verify = True
                
                req_kaptcha = self.sess.get(self.kaptcha_url, timeout=self.timeout, verify=False)
                
                if req_kaptcha.status_code != 200:
                    print(f"验证码获取失败，状态码: {req_kaptcha.status_code}")
                    return {"code": 2333, "msg": f"验证码获取失败，状态码: {req_kaptcha.status_code}"}
                
                kaptcha_pic = base64.b64encode(req_kaptcha.content).decode()
                print(f"验证码获取成功，大小: {len(req_kaptcha.content)} bytes")
                
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
                        "kaptcha_pic": kaptcha_pic,
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
            
            if str(tips) != "":
                tip_text = tips.text()
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
                    "has_tips": str(tips) != "",
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
        print(f"开始验证码登录流程:")
        print(f"  学号: {sid}")
        print(f"  验证码: {kaptcha}")
        print(f"  CSRF token: {csrf_token}")
        print(f"  Cookies: {cookies}")
        
        # 验证登录URL配置
        if not self.login_url:
            return {"code": 2333, "msg": "登录URL未设置，请检查base_url配置"}
        
        try:
            # 加密密码
            encrypt_password_result = self.encrypt_password(password, modulus, exponent)
            print(f"密码加密成功，长度: {len(encrypt_password_result)}")
            
            login_data = {
                "csrftoken": csrf_token,
                "yhm": sid,
                "mm": encrypt_password_result.decode('utf-8'),
                "yzm": kaptcha,
            }
            print(f"验证码登录数据: {login_data}")
            
            # 执行登录
            req_login = self.sess.post(
                self.login_url,
                data=login_data,
                cookies=cookies,
                timeout=self.timeout,
                verify=False
            )
            
            print(f"验证码登录响应状态码: {req_login.status_code}")
            print(f"验证码登录后cookies: {self.sess.cookies.get_dict()}")
            
            if req_login.status_code != 200:
                return {"code": 2333, "msg": f"验证码登录请求失败，状态码: {req_login.status_code}"}
            
            # 分析登录响应
            doc = pq(req_login.text)
            tips = doc("p#tips")
            
            if str(tips) != "":
                tip_text = tips.text()
                print(f"验证码登录错误提示: {tip_text}")
                
                if "验证码" in tip_text:
                    return {"code": 1004, "msg": "验证码输入错误"}
                if "用户名或密码" in tip_text:
                    return {"code": 1002, "msg": "用户名或密码不正确"}
                return {"code": 998, "msg": tip_text}
            
            # 检查是否登录成功
            if "退出登录" in req_login.text or "个人信息" in req_login.text or "main" in req_login.text:
                print("✅ 验证码登录成功！")
                self.cookies = self.sess.cookies.get_dict()
                
                # 不同学校系统兼容差异
                if not self.cookies.get("route") and cookies.get("route"):
                    route_cookies = {
                        "JSESSIONID": self.cookies.get("JSESSIONID", cookies.get("JSESSIONID")),
                        "route": cookies["route"],
                    }
                    self.cookies = route_cookies
                
                return {"code": 1000, "msg": "登录成功", "data": {"cookies": self.cookies}}
            
            return {
                "code": 999,
                "msg": "验证码登录状态未知",
                "debug": {
                    "content_length": len(req_login.text),
                    "has_tips": str(tips) != "",
                    "cookies": self.sess.cookies.get_dict(),
                    "original_cookies": cookies
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

    def get_info(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取个人信息"""
        try:
            url = self.get_school_url('info', 'xsxxxggl/xsxxwh_cxCkDgxsxx.html?gnmkdm=N100801', school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        try:
            req_info = self.sess.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                verify=False,
            )
            if req_info.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_info.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}              # 检查是否返回了错误页面（比如"无功能权限"）
            if "无功能权限" in req_info.text or "错误提示" in req_info.text:
                print("主要个人信息接口返回权限错误，尝试使用备选接口")
                return self._get_info(school_name, base_url)
              # 解析JSON响应
            try:
                info = req_info.json()
                if info is None:
                    return self._get_info(school_name, base_url)
                result = {
                    "sid": info.get("xh"),
                    "name": info.get("xm"),
                    "college_name": info.get("zsjg_id", info.get("jg_id")),
                    "major_name": info.get("zszyh_id", info.get("zyh_id")),
                    "class_name": info.get("bh_id", info.get("xjztdm")),
                    "status": info.get("xjztdm"),
                    "enrollment_date": info.get("rxrq"),
                    "candidate_number": info.get("ksh"),
                    "graduation_school": info.get("byzx"),
                    "domicile": info.get("jg"),
                    "postal_code": info.get("yzbm"),
                    "politics_status": info.get("zzmmm"),
                    "nationality": info.get("mzm"),
                    "education": info.get("pyccdm"),
                    "phone_number": info.get("sjhm"),
                    "parents_number": info.get("gddh"),
                    "email": info.get("dzyx"),
                    "birthday": info.get("csrq"),
                    "id_number": info.get("zjhm"),                }
                return {"code": 1000, "msg": "获取个人信息成功", "data": result}
            except json.decoder.JSONDecodeError:
                # JSON解析失败，可能返回的是HTML页面，使用备选方法
                print("主要个人信息接口JSON解析失败，尝试使用备选接口")
                return self._get_info(school_name, base_url)
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取个人信息超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取个人信息时未记录的错误：" + str(e)}

    def _get_info(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取个人信息"""
        try:
            url = self.get_school_url("info", "xsxxxggl/xsgrxxwh_cxXsgrxx.html?gnmkdm=N100801", school_name, base_url)
        except ValueError:
            # 使用备用base_url
            fallback_base = base_url or self.base_url or ""
            url = urljoin(fallback_base, "xsxxxggl/xsgrxxwh_cxXsgrxx.html?gnmkdm=N100801")
        try:
            req_info = self.sess.get(
                url, headers=self.headers, timeout=self.timeout, verify=False
            )
            if req_info.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_info.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            pending_result = {}
            # 学生基本信息
            for ul_item in doc.find("div.col-sm-6").items():
                content = pq(ul_item).find("div.form-group")
                # key = re.findall(r'^[\u4E00-\u9FA5A-Za-z0-9]+', pq(content).find('label.col-sm-4.control-label').text())[0]
                key = pq(content).find("label.col-sm-4.control-label").text()
                value = pq(content).find("div.col-sm-8 p.form-control-static").text()
                # 到这一步，解析到的数据基本就是一个键值对形式的html数据了，比如"[学号：]:123456"
                pending_result[key] = value
            # 学生学籍信息，其他信息，联系方式
            for ul_item in doc.find("div.col-sm-4").items():
                content = pq(ul_item).find("div.form-group")
                key = pq(content).find("label.col-sm-4.control-label").text()
                value = pq(content).find("div.col-sm-8 p.form-control-static").text()                # 到这一步，解析到的数据基本就是一个键值对形式的html数据了，比如"[学号：]:123456"
                pending_result[key] = value
            
            if pending_result.get("学号：") == "":
                return {
                    "code": 1014,
                    "msg": "当前学年学期无学生时盒数据，您可能已经毕业了。\n\n如果是专升本同学，请使用专升本后的新学号登录～",
                }
            
            # 输出详细信息
            print(f"解析到的字段数量: {len(pending_result)}")
            print(f"解析到的前10个字段: {list(pending_result.keys())[:10]}")
              # 检查是否有必需的字段
            if not pending_result.get("学号："):
                print("错误: 未找到学号字段或学号为空")
                print(f"所有字段: {list(pending_result.keys())}")
                return {"code": 2333, "msg": "解析个人信息失败：未找到学号字段"}
            
            # 使用.get()方法安全获取字段，避免KeyError
            result = {
                "sid": pending_result.get("学号：", ""),
                "name": pending_result.get("姓名：", "无"),
                # "birthday": "无" if pending_result.get("出生日期：") == '' else pending_result.get("出生日期：", "无"),
                # "id_number": "无" if pending_result.get("证件号码：") == '' else pending_result.get("证件号码：", "无"),
                # "candidate_number": "无" if pending_result.get("考生号：") == '' else pending_result.get("考生号：", "无"),
                # "status": "无" if pending_result.get("学籍状态：") == '' else pending_result.get("学籍状态：", "无"),
                # "entry_date": "无" if pending_result.get("入学日期：") == '' else pending_result.get("入学日期：", "无"),
                # "graduation_school": "无" if pending_result.get("毕业中学：") == '' else pending_result.get("毕业中学：", "无"),
                "domicile": "无"
                if pending_result.get("籍贯：", "") == ""
                else pending_result.get("籍贯：", "无"),
                "phone_number": "无"
                if pending_result.get("手机号码：", "") == ""
                else pending_result.get("手机号码：", "无"),
                "parents_number": "无",
                "email": "无"
                if pending_result.get("电子邮箱：", "") == ""
                else pending_result.get("电子邮箱：", "无"),
                "political_status": "无"
                if pending_result.get("政治面貌：", "") == ""
                else pending_result.get("政治面貌：", "无"),
                "national": "无"
                if pending_result.get("民族：", "") == ""
                else pending_result.get("民族：", "无"),
                # "education": "无" if pending_result.get("培养层次：") == '' else pending_result.get("培养层次：", "无"),
                # "postal_code": "无" if pending_result.get("邮政编码：") == '' else pending_result.get("邮政编码：", "无"),                # "grade": int(pending_result.get("学号：", "0000")[0:4]) if pending_result.get("学号：") else 0,
            }
            if pending_result.get("学院名称：") is not None:
                # 如果在个人信息页面获取到了学院班级
                result.update(
                    {
                        "college_name": "无"
                        if not pending_result.get("学院名称：")
                        else pending_result.get("学院名称：", "无"),
                        "major_name": "无"
                        if not pending_result.get("专业名称：")
                        else pending_result.get("专业名称：", "无"),
                        "class_name": "无"
                        if not pending_result.get("班级名称：")
                        else pending_result.get("班级名称：", "无"),
                    }
                )
            else:
                # 如果个人信息页面获取不到学院班级，则此处需要请求另外一个地址以获取学院、专业、班级等信息
                _url = urljoin(
                    self.base_url or '',
                    "xszbbgl/xszbbgl_cxXszbbsqIndex.html?doType=details&gnmkdm=N106005",
                )
                _req_info = self.sess.post(
                    _url,
                    headers=self.headers,
                    timeout=self.timeout,
                    data={"offDetails": "1", "gnmkdm": "N106005", "czdmKey": "00"},
                    verify=False,
                )
                _doc = pq(_req_info.text)
                if _doc("p.error_title").text() != "无功能权限，":
                    # 通过学生证补办申请入口，来补全部分信息
                    for ul_item in _doc.find("div.col-sm-6").items():
                        content = pq(ul_item).find("div.form-group")
                        key = (
                            pq(content).find("label.col-sm-4.control-label").text()
                            + "："
                        )  # 为了保持格式一致，这里加个冒号
                        value = (
                            pq(content).find("div.col-sm-8 label.control-label").text()
                        )                        # 到这一步，解析到的数据基本就是一个键值对形式的html数据了，比如"[学号：]:123456"
                        pending_result[key] = value
                    result.update(
                        {
                            "college_name": "无"
                            if not pending_result.get("学院：")
                            else pending_result.get("学院：", "无"),
                            "major_name": "无"
                            if not pending_result.get("专业：")
                            else pending_result.get("专业：", "无"),
                            "class_name": "无"
                            if not pending_result.get("班级：")
                            else pending_result.get("班级：", "无"),
                        }
                    )
            return {"code": 1000, "msg": "获取个人信息成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取个人信息超时"}
        except (            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取个人信息时未记录的错误：" + str(e)}

    def get_grade(self, year, term = 0, use_personal_info: bool = False, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """
        获取成绩
        use_personal_info: 是否使用获取个人信息接口获取成绩
        year: 学年，如果为空或NaN则查询全部学年
        term: 学期，如果为空或NaN则查询全部学期
        """
        # 处理空值或NaN参数
        import math
        
        # 处理year参数
        if year is None or year == '' or (isinstance(year, (int, float)) and math.isnan(year)):
            # 如果year为空或NaN，设置为空字符串表示查询全部学年
            year = ''
        else:
            try:
                year = int(year)
            except (ValueError, TypeError):
                # 如果转换失败，设置为空字符串表示查询全部学年
                year = ''
        
        # 处理term参数
        if term is None or term == '' or (isinstance(term, (int, float)) and math.isnan(term)):
            term = 0  # 0表示全部学期
        else:
            try:
                term = int(term)
            except (ValueError, TypeError):
                term = 0  # 默认为全部学期
        
        # 根据学校配置获取成绩查询URL
        try:
            # 首先尝试从配置获取grade URL
            url = self.get_school_url('grade', None, school_name, base_url)
            # 如果配置的URL不包含doType=query，则添加
            if 'doType=query' not in url:
                # 添加doType=query参数
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}doType=query"
        except ValueError:
            # 如果配置获取失败，使用默认URL
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N305005"
            
        temp_term = term
        # 根据真实请求：第一学期为空或3，第二学期为12
        if term == 1:
            term_param = ""  # 第一学期可以为空
        elif term == 2:
            term_param = "12"  # 第二学期为12
        else:
            term_param = ""  # 全学年查询时参数为空
        
        # 构建符合接口规范的请求数据
        data = {
            "xnm": str(year) if year != '' else '',  # 学年数，如2024，空字符串表示全部学年
            "xqm": term_param,  # 学期数，第一学期为空或3，第二学期为12
            "sfzgcj": "",  # 是否重考成绩
            "kcbj": "",    # 课程标记
            "_search": "false",
            "nd": int(time.time() * 1000),  # 当前时间戳
            "queryModel.showCount": "15",  # 每页最多条数
            "queryModel.currentPage": "1",
            "queryModel.sortName": " ",  # 注意这里是空格
            "queryModel.sortOrder": "asc",
            "time": "0",  # 查询次数
        }        # 构建标准HTTP请求头
        grade_headers = self.headers.copy()
          # 构建正确的base_url和Referer，确保使用正确的学校配置
        try:
            target_base_url = self.get_school_base_url(school_name, base_url)
            # 构建成绩查询页面的Referer URL
            referer_url = self.get_school_url('grade', None, school_name, base_url)
            # 设置页面布局参数作为Referer
            if '?doType=query' in referer_url:
                referer_url = referer_url.replace('?doType=query', '?layout=default')
            elif '&doType=query' in referer_url:
                referer_url = referer_url.replace('&doType=query', '&layout=default')
            elif '?' not in referer_url:
                referer_url = f"{referer_url}?layout=default"
        except ValueError:
            # 使用备用base_url
            target_base_url = self.base_url.rstrip('/') if self.base_url else ''
            referer_url = f'{target_base_url}/cjcx/cjcx_cxXsgrcj.html?gnmkdm=N305005&layout=default'
        
        base_origin = target_base_url.rstrip('/')
        
        grade_headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': base_origin,
            'Pragma': 'no-cache',
            'Referer': referer_url,
            'Sec-CH-UA': '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        try:
            print(f"成绩查询 - URL: {url}")
            print(f"成绩查询 - 数据: {data}")
            print(f"成绩查询 - Headers: {grade_headers}")
            
            req_grade = self.sess.post(
                url,
                headers=grade_headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            print(f"成绩查询 - 响应状态码: {req_grade.status_code}")
            print(f"成绩查询 - 响应头: {dict(req_grade.headers)}")
            print(f"成绩查询 - 响应内容前500字符: {req_grade.text[:500]}")
            
            if req_grade.status_code != 200:
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req_grade.status_code}"}
            
            doc = pq(req_grade.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                grade = req_grade.json()
                print(f"成绩查询 - JSON解析成功: {grade}")
            except json.JSONDecodeError as json_err:
                print(f"成绩查询 - JSON解析失败: {json_err}")
                print(f"成绩查询 - 原始响应: {req_grade.text}")
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
            grade_items = grade.get("items")
            if not grade_items:
                print(f"成绩查询 - 响应数据中缺少items字段，原始响应: {grade}")
                return {"code": 1005, "msg": "获取内容为空"}
            
            result = {
                "sid": grade_items[0]["xh"],
                "name": grade_items[0]["xm"],
                "year": year,
                "term": temp_term,
                "count": len(grade_items),
                "courses": [
                    {
                        "course_id": i.get("kch_id"),
                        "title": i.get("kcmc"),
                        "teacher": i.get("jsxm"),
                        "class_name": i.get("jxbmc"),
                        "credit": self.align_floats(i.get("xf")),
                        "category": i.get("kclbmc"),
                        "nature": i.get("kcxzmc"),
                        "grade": self.parse_int(i.get("cj")),
                        "grade_point": self.align_floats(i.get("jd")),
                        "grade_nature": i.get("ksxz"),
                        "start_college": i.get("kkbmmc"),
                        "mark": i.get("kcbj"),
                    }
                    for i in grade_items
                ],
            }
            return {"code": 1000, "msg": "获取成绩成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取成绩超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取成绩时未记录的错误：" + str(e)}

    def get_grade_detail(self, year: int, term: int = 0, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """
        获取详细成绩（含平时分、期末分等细节）
        参数:
            year: 学年，如2024
            term: 学期，1-第一学期，2-第二学期，0-全学年
            school_name: 学校名称（可选）
            base_url: 基础URL（可选）
        """
        try:
            # 从配置获取详细成绩查询URL
            url = self.get_school_url('grade_detail', None, school_name, base_url)
            # 如果配置的URL不包含doType=query，则添加
            if 'doType=query' not in url:
                # 设置查询类型参数
                if 'layout=default' in url:
                    url = url.replace('layout=default', 'doType=query')
                else:
                    separator = '&' if '?' in url else '?'
                    url = f"{url}{separator}doType=query"
        except ValueError:
            # 如果配置获取失败，使用默认URL
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/cjcx/cjcx_cxXsKccjList.html?doType=query&gnmkdm=N305007"
        
        # 学期参数转换
        if term == 1:
            term_param = "3"    # 第一学期为3
        elif term == 2:
            term_param = "12"   # 第二学期为12
        else:
            term_param = ""     # 全学年查询时参数为空
        
        # 构建请求数据
        data = {
            "xnm": str(year),  # 学年数
            "xqm": term_param,  # 学期数，第一学期为3，第二学期为12, 全学年为空''
            "_search": "false",
            "nd": int(time.time() * 1000),
            "queryModel.showCount": "100",  # 每页最多条数
            "queryModel.currentPage": "1",
            "queryModel.sortName": "",
            "queryModel.sortOrder": "asc",
            "time": "0",  # 查询次数
        }
        
        # 构建请求头
        detail_headers = self.headers.copy()
        try:
            target_base_url = self.get_school_base_url(school_name, base_url)
            # 构建Referer URL
            referer_url = self.get_school_url('grade_detail', None, school_name, base_url)
            if 'doType=query' in referer_url:
                referer_url = referer_url.replace('doType=query', 'layout=default')
        except ValueError:
            target_base_url = self.base_url.rstrip('/') if self.base_url else ''
            referer_url = f'{target_base_url}/cjcx/cjcx_cxXsKccjList.html?gnmkdm=N305007&layout=default'
        
        base_origin = target_base_url.rstrip('/')
        
        detail_headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': base_origin,
            'Pragma': 'no-cache',
            'Referer': referer_url,
            'Sec-CH-UA': '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        try:
            print(f"详细成绩查询 - URL: {url}")
            print(f"详细成绩查询 - 数据: {data}")
            
            req_grade = self.sess.post(
                url,
                headers=detail_headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            print(f"详细成绩查询 - 响应状态码: {req_grade.status_code}")
            
            if req_grade.status_code != 200:
                return {"code": 2333, "msg": f"教务系统响应异常，状态码: {req_grade.status_code}"}
            
            # 检查是否被重定向到登录页面
            doc = pq(req_grade.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1013, "msg": "登录过期，请重新登录"}
            
            # 解析JSON响应
            try:
                grade_response = req_grade.json()
                print(f"详细成绩查询 - JSON解析成功")
            except json.JSONDecodeError as json_err:
                print(f"详细成绩查询 - JSON解析失败: {json_err}")
                print(f"详细成绩查询 - 原始响应前500字符: {req_grade.text[:500]}")
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
            # 检查是否有数据
            if not grade_response.get("items"):
                return {"code": 1005, "msg": "获取内容为空"}
            
            # 返回原始响应数据
            return {"code": 1000, "msg": "获取详细成绩成功", "data": grade_response}
            
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取详细成绩超时"}
        except exceptions.RequestException:
            traceback.print_exc()
            return {"code": 2333, "msg": "请重试或教务系统维护中"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取详细成绩时未记录的错误：" + str(e)}

    def get_exam_schedule(self, year: int, term: int = 0, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取考试信息"""
        try:
            # 首先尝试从配置获取exam URL
            url = self.get_school_url('exam', None, school_name, base_url)
            # 如果配置的URL不包含doType=query，则添加
            if 'doType=query' not in url:
                # 添加doType=query参数
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}doType=query"
        except ValueError:
            # 如果配置获取失败，使用默认URL
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/kwgl/kscx_cxXsksxxIndex.html?doType=query&gnmkdm=N358105"
        temp_term = term
        term = term**2 * 3
        term = 0 if term == 0 else term
        data = {
            "xnm": str(year),  # 学年数
            "xqm": str(term),  # 学期数，第一学期为3，第二学期为12, 全学年为空''
            "_search": "false",
            "nd": int(time.time() * 1000),
            "queryModel.showCount": "100",  # 每页最多条数
            "queryModel.currentPage": "1",
            "queryModel.sortName": "",
            "queryModel.sortOrder": "asc",            "time": "0",  # 查询次数
        }
        try:
            print(f"考试查询 - URL: {url}")
            print(f"考试查询 - 数据: {data}")
            
            req_grade = self.sess.post(
                url,
                headers=self.headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            print(f"考试查询 - 响应状态码: {req_grade.status_code}")
            print(f"考试查询 - 响应内容前500字符: {req_grade.text[:500]}")
            
            if req_grade.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_grade.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                grade = req_grade.json()
                print(f"考试查询 - JSON解析成功: {grade}")
            except json.JSONDecodeError as json_err:
                print(f"考试查询 - JSON解析失败: {json_err}")
                print(f"考试查询 - 原始响应: {req_grade.text}")
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
                
            grade = req_grade.json()
            grade_items = grade.get("items")
            if not grade_items:
                return {"code": 1005, "msg": "获取内容为空"}
            result = {
                "sid": grade_items[0]["xh"],
                "name": grade_items[0]["xm"],
                "year": year,
                "term": temp_term,
                "count": len(grade_items),
                "courses": [
                    {
                        "course_id": i.get("kch"), # 课程代码
                        "title": i.get("kcmc"), # 课程名称
                        "time": i.get("kssj"), # 考试时间信息
                        "location": i.get("cdmc"), # 考试地点
                        "xq": i.get("cdxqmc"), # 考试校区
                        "zwh": i.get("zwh"), # 考试座号
                        "cxbj": i.get("cxbj", ""), # 重修标记
                        "exam_name": i.get("ksmc"), # 考试批次名
                        "teacher": i.get("jsxx"), # 任课教师(含教师id)
                        "class_name": i.get("jxbmc"), # 教学班名称
                        "kkxy": i.get("kkxy"), # 开课学院
                        "credit": self.align_floats(i.get("xf")), # 课程学分数
                        "ksfs": i.get("ksfs"), # 考试方式, ep: 笔试 & 开卷 & 机考
                        "sjbh": i.get("sjbh"), # 试卷编号
                        "bz": i.get("bz1", ""), # 备注, ep: 免监考班级
                    }
                    for i in grade_items
                ],
            }
            return {"code": 1000, "msg": "获取考试信息成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取考试信息超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取考试信息时未记录的错误：" + str(e)}

    def get_schedule(self, year: int, term: int, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取课程表信息"""
        try:
            # 获取基础 URL
            target_base_url = self.get_school_base_url(school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        # 第一步：访问课表首页 (这是必须的步骤)
        try:
            index_url = self.get_school_url("schedule_index", "kbcx/xskbcx_cxXskbcxIndex.html?gnmkdm=N2151&layout=default", school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
        
        try:
            # 先访问课表首页以建立正确的session状态
            index_headers = self.headers.copy()
            index_headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Upgrade-Insecure-Requests': '1'
            })
            
            index_response = self.sess.get(index_url, headers=index_headers, timeout=self.timeout, verify=False)
            if index_response.status_code != 200:
                return {"code": 2333, "msg": f"无法访问课表首页，状态码: {index_response.status_code}"}
                  
            # 第二步：获取课表数据
            try:
                url = self.get_school_url("schedule", "kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N2151", school_name, base_url)
            except ValueError as e:
                return {"code": 2333, "msg": str(e)}
            temp_term = term
            term = term**2 * 3
            data = {"xnm": str(year), "xqm": str(term)}
            
            # 计算正确的 Origin（去掉路径部分，只保留协议+域名+端口）
            from urllib.parse import urlparse
            parsed_base = urlparse(target_base_url)
            origin_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            # 设置正确的请求头（使用刚访问的首页作为Referer）
            headers = self.headers.copy()
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': index_url,
                'Accept': '*/*',
                'Origin': origin_url,
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            req_schedule = self.sess.post(
                url,
                headers=headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            if req_schedule.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_schedule.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            schedule = req_schedule.json()
            if not schedule.get("kbList"):
                return {"code": 1005, "msg": "获取内容为空"}
            result = {
                "sid": schedule["xsxx"].get("XH"),
                "name": schedule["xsxx"].get("XM"),
                "year": year,
                "term": temp_term,
                "count": len(schedule["kbList"]),
                "courses": [
                    {
                        "course_id": i.get("kch_id"),
                        "title": i.get("kcmc"),
                        "teacher": i.get("xm"),
                        "class_name": i.get("jxbmc"),
                        "credit": self.align_floats(i.get("xf")),
                        "weekday": self.parse_int(i.get("xqj")),
                        "time": self.display_course_time(i.get("jc")),
                        "sessions": i.get("jc"),
                        "list_sessions": self.list_sessions(i.get("jc")),
                        "weeks": i.get("zcd"),
                        "list_weeks": self.list_weeks(i.get("zcd")),
                        "evaluation_mode": i.get("khfsmc"),
                        "campus": i.get("xqmc"),
                        "place": i.get("cdmc"),
                        "hours_composition": i.get("kcxszc"),
                        "weekly_hours": self.parse_int(i.get("zhxs")),
                        "total_hours": self.parse_int(i.get("zxs")),
                    }
                    for i in schedule["kbList"]
                ],
                "extra_courses": [i.get("qtkcgs") for i in schedule.get("sjkList")],
            }
            result = self.split_merge_display(result)
            return {"code": 1000, "msg": "获取课表成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取课表超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取课表时未记录的错误：" + str(e)}

    #def get_academia(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取学业生涯情况"""
        try:
            url_main = self.get_school_url("academia", "xsxy/xsxyqk_cxXsxyqkIndex.html?gnmkdm=N105515&layout=default", school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
        try:
            url_info = self.get_school_url("academia_info", "xsxy/xsxyqk_cxJxzxjhxfyqKcxx.html?gnmkdm=N105515", school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
        try:
            req_main = self.sess.get(
                url_main,
                headers=self.headers,
                timeout=self.timeout,
                stream=True,
                verify=False,
            )
            if req_main.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc_main = pq(req_main.text)
            if doc_main("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            if str(doc_main("div.alert-danger")) != "":
                return {"code": 998, "msg": doc_main("div.alert-danger").text()}
            sid = doc_main("form#form input#xh_id").attr("value")
            display_statistics = (
                doc_main("div#alertBox").text().replace(" ", "").replace("\n", "")
            )
            sid = doc_main("input#xh_id").attr("value")
            statistics = self.get_academia_statistics(display_statistics)
            type_statistics = self.get_academia_type_statistics(req_main.text)
            details = {}
            for type in type_statistics.keys():
                details[type] = self.sess.post(
                    url_info,
                    headers=self.headers,
                    data={"xfyqjd_id": type_statistics[type]["id"]},
                    timeout=self.timeout,
                    verify=False,
                    stream=True,
                ).json()
            result = {
                "sid": sid,
                "statistics": statistics,
                "details": [
                    {
                        "type": type,
                        "credits": type_statistics[type]["credits"],
                        "courses": [
                            {
                                "course_id": i.get("KCH"),
                                "title": i.get("KCMC"),
                                "situation": self.parse_int(i.get("XDZT")),
                                "display_term": self.get_display_term(
                                    sid, i.get("JYXDXNM"), i.get("JYXDXQMC")
                                ),
                                "credit": self.align_floats(i.get("XF")),
                                "category": self.get_course_category(type, i),
                                "nature": i.get("KCXZMC"),
                                "max_grade": self.parse_int(i.get("MAXCJ")),
                                "grade_point": self.align_floats(i.get("JD")),
                            }
                            for i in details[type]
                        ],
                    }
                    for type in type_statistics.keys()
                    if len(details[type]) > 0
                ],
            }
            return {"code": 1000, "msg": "获取学业情况成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取学业情况超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取学业情况时未记录的错误：" + str(e)}

    #def get_academia_pdf(self):
        """获取学业生涯（学生成绩总表）pdf"""
        url_view = urljoin(self.base_url, "bysxxcx/xscjzbdy_dyXscjzbView.html")
        url_window = urljoin(self.base_url, "bysxxcx/xscjzbdy_dyCjdyszxView.html")
        url_policy = urljoin(self.base_url, "xtgl/bysxxcx/xscjzbdy_cxXsCount.html")
        url_filetype = urljoin(self.base_url, "bysxxcx/xscjzbdy_cxGswjlx.html")
        url_common = urljoin(self.base_url, "common/common_cxJwxtxx.html")
        url_file = urljoin(self.base_url, "bysxxcx/xscjzbdy_dyList.html")
        url_progress = urljoin(self.base_url, "xtgl/progress_cxProgressStatus.html")
        data = {
            "gsdygx": "10628-zw-mrgs",
            "ids": "",
            "bdykcxzDms": "",
            "cytjkcxzDms": "",
            "cytjkclbDms": "",
            "cytjkcgsDms": "",
            "bjgbdykcxzDms": "",
            "bjgbdyxxkcxzDms": "",
            "djksxmDms": "",
            "cjbzmcDms": "",
            "cjdySzxs": "",
            "wjlx": "pdf",
        }

        try:
            data_view = {"time": str(round(time.time() * 1000)), "gnmkdm": "N558020"}
            data_params = data_view
            del data_params["time"]
            # View接口
            req_view = self.sess.post(
                url_view,
                headers=self.headers,
                data=data_view,
                params=data_view,
                timeout=self.timeout,
                verify=False,
            )
            if req_view.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_view.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            # Window接口
            data_window = {"xh": ""}
            self.sess.post(
                url_window,
                headers=self.headers,
                data=data_window,
                params=data_params,
                timeout=self.timeout,
                verify=False,
            )
            # 许可接口
            data_policy = data
            del data_policy["wjlx"]
            self.sess.post(
                url_policy,
                headers=self.headers,
                data=data_policy,
                params=data_params,
                timeout=self.timeout,
                verify=False,
            )
            # 文件类型接口
            data_filetype = data_policy
            self.sess.post(
                url_filetype,
                headers=self.headers,
                data=data_filetype,
                params=data_params,
                timeout=self.timeout,
            )
            # Common接口
            self.sess.post(
                url_common,
                headers=self.headers,
                data=data_params,
                params=data_params,
                timeout=self.timeout,
            )
            # 获取PDF文件URL
            req_file = self.sess.post(
                url_file,
                headers=self.headers,
                data=data,
                params=data_params,
                timeout=self.timeout,
                verify=False,
            )
            doc = pq(req_file.text)
            if "错误" in doc("title").text():
                error = doc("p.error_title").text()
                return {"code": 998, "msg": error}
            # 调用进度查询接口
            data_progress = {
                "key": "score_print_processed",
                "gnmkdm": "N558020",
            }
            self.sess.post(
                url_progress,
                headers=self.headers,
                data=data_progress,
                params=data_progress,
                timeout=self.timeout,
                verify=False,
            )
            # 生成PDF文件URL
            pdf = (
                req_file.text.replace("#成功", "")
                .replace('"', "")
                .replace("/", "\\")
                .replace("\\\\", "/")
            )
            # 下载PDF文件
            req_pdf = self.sess.get(
                urljoin(self.base_url, pdf),
                headers=self.headers,
                timeout=self.timeout + 2,
            )
            result = req_pdf.content  # PDF文件二进制数据
            return {"code": 1000, "msg": "获取学生成绩总表pdf成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取成绩总表pdf超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取成绩总表pdf时未记录的错误：" + str(e)}

    #def get_schedule_pdf(self, year: int, term: int, name: str = "导出", student_id: str = "", school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取课表PDF"""
        try:
            # 使用配置获取schedule_pdf URL，这就是你提供的 kbdy/bjkbdy_cxXnxqsfkz.html 地址
            url = self.get_school_url("schedule_pdf", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        origin_term = term
        term = term**2 * 3
        
        # 构建课表查询表单数据
        data = {
            "xnm": str(year),
            "xqm": str(term),
            "xnmc": f"{year}-{year + 1}",
            "xqmmc": str(origin_term),
            "xm": name,  # 学生姓名
            "xxdm": "",
            "xszd.sj": "true",       # 时间显示配置
            "xszd.cd": "true",       # 显示场地
            "xszd.js": "true",       # 显示教师
            "xszd.jszc": "false",    # 教师职称
            "xszd.jxb": "false",     # 教学班
            "xszd.jxbzc": "true",    # 教学班组成
            "xszd.xkbz": "false",    # 选课备注
            "xszd.kcxszc": "false",  # 课程学时组成显示配置
            "xszd.zhxs": "false",    # 总学时显示配置
            "xszd.zxs": "false",     # 周学时
            "xszd.khfs": "false",    # 考核方式
            "xszd.ksfs": "false",    # 考试方式
            "xszd.xf": "false",      # 学分
            "xszd.skfsmc": "false",  # 上课方式名称
            "xszd.zfj": "false",     # 主副教师
            "xszd.cxbj": "false",    # 重修班级
            "xszd.kcxz": "false",    # 课程性质
            "xszd.kcbj": "false",    # 课程备注
            "xszd.kczxs": "false",   # 课程总学时
            "xsdm": "",              # 学生代码
            "kclbdm": "",            # 课程类别代码
            "kzlx": "dy"             # 控制类型：打印
        }
        
        # 如果提供了学生ID，添加modelList数据（根据你的示例）
        if student_id:
            data.update({
                f"modelList[0].xnm": str(year),
                f"modelList[0].xqm": str(term),
                f"modelList[0].xnmc": f"{year}-{year + 1}",
                f"modelList[0].xqmmc": str(origin_term),
                f"modelList[0].xh_id": student_id,
                f"modelList[0].xh": student_id,
                f"modelList[0].xm": name,
                f"modelList[0].bjmc": "",        # 班级名称，可以从其他接口获取或留空
                f"modelList[0].xsdm": "",        # 学生代码
                f"modelList[0].kclbdm": "",      # 课程类别代码
            })

        try:
            # 构建请求头
            headers = self.headers.copy()
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            })
            
            # 发送请求
            response = self.sess.post(
                url,
                headers=headers,
                data=data,
                timeout=self.timeout,
            )
            
            if response.status_code != 200:
                return {"code": 2333, "msg": f"请求失败，状态码: {response.status_code}"}
            
            # 检查是否被重定向到登录页
            doc = pq(response.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
              # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            
            # 根据真实请求分析，响应是JSON格式
            if 'json' in content_type.lower():
                try:
                    json_response = response.json()
                    print(f"PDF导出JSON响应: {json_response}")
                    
                    # 检查JSON响应结构，可能包含PDF下载链接或状态
                    if isinstance(json_response, dict):
                        # 如果有错误信息
                        if 'error' in json_response or 'msg' in json_response:
                            error_msg = json_response.get('msg') or json_response.get('error') or "PDF生成失败"
                            return {"code": 998, "msg": f"服务器错误: {error_msg}"}
                        
                        # 如果有PDF链接
                        if 'url' in json_response or 'link' in json_response or 'data' in json_response:
                            pdf_link = json_response.get('url') or json_response.get('link') or json_response.get('data')
                            if pdf_link:
                                # 构建PDF下载链接
                                if pdf_link.startswith('http'):
                                    full_pdf_url = pdf_link
                                else:
                                    # 相对链接，需要拼接base_url
                                    base_domain = url.split('/')[0] + '//' + url.split('/')[2]
                                    full_pdf_url = urljoin(base_domain, pdf_link)
                                
                                print(f"PDF下载链接: {full_pdf_url}")
                                
                                # 下载实际的PDF文件
                                try:
                                    pdf_response = self.sess.get(full_pdf_url, headers=self.headers, timeout=self.timeout, verify=False)
                                    if pdf_response.status_code == 200:
                                        if pdf_response.content.startswith(b'%PDF') or 'pdf' in pdf_response.headers.get('Content-Type', '').lower():
                                            return {
                                                "code": 1000,
                                                "msg": "获取课程表PDF成功",
                                                "data": pdf_response.content,
                                                "content_type": "application/pdf",
                                                "pdf_url": full_pdf_url
                                            }
                                        else:
                                            return {"code": 998, "msg": "PDF链接返回的不是有效的PDF文件"}
                                    else:
                                        return {"code": 998, "msg": f"PDF下载失败，状态码: {pdf_response.status_code}"}
                                except Exception as pdf_e:
                                    return {"code": 998, "msg": f"PDF下载异常: {str(pdf_e)}"}
                        
                        # JSON响应不包含明确的链接时，返回原始响应
                        return {
                            "code": 998,
                            "msg": "JSON响应格式未知，请检查服务器返回",
                            "debug_response": json_response
                        }
                    else:
                        # 非字典格式的JSON，可能是字符串或其他格式
                        return {
                            "code": 998,
                            "msg": f"意外的JSON响应格式: {type(json_response)}",
                            "debug_response": json_response
                        }
                        
                except json.decoder.JSONDecodeError:
                    # JSON解析失败，按文本处理
                    return {"code": 998, "msg": f"JSON解析失败，响应内容: {response.text[:200]}"}
            
            elif 'pdf' in content_type.lower():
                # 直接返回PDF内容（如果真的是PDF）
                return {
                    "code": 1000, 
                    "msg": "获取课程表PDF成功", 
                    "data": response.content, 
                    "content_type": "application/pdf"
                }
            elif 'html' in content_type.lower():
                # HTML页面，检查是否有错误信息
                if "错误" in response.text or "error" in response.text.lower():
                    error_msg = doc("p.error_title").text() or doc(".alert").text() or "PDF生成失败"
                    return {"code": 998, "msg": error_msg}
                else:
                    return {"code": 998, "msg": "服务器返回HTML内容，请检查参数或登录状态"}
            else:
                # 其他格式，尝试作为PDF处理
                if len(response.content) > 100 and response.content.startswith(b'%PDF'):
                    return {
                        "code": 1000, 
                        "msg": "获取课程表PDF成功", 
                        "data": response.content, 
                        "content_type": "application/pdf"
                    }
                else:
                    return {
                        "code": 998, 
                        "msg": f"未知的响应格式，Content-Type: {content_type}，响应长度: {len(response.content)}",
                        "debug_response": response.text[:200] if response.text else "无文本内容"
                    }
                
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取课程表PDF超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"获取课程表PDF时未记录的错误：{str(e)}"}

    def get_notifications(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取通知消息"""
        try:
            # 首先尝试从配置获取notifications URL
            url = self.get_school_url('notifications', None, school_name, base_url)
            # 如果配置的URL不包含doType=query，则添加
            if 'doType=query' not in url:
                # 添加doType=query参数
                separator = '&' if '?' in url else '?'
                url = f"{url}{separator}doType=query"
        except ValueError:
            # 如果配置获取失败，使用默认URL
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/xtgl/index_cxDbsy.html?doType=query"
        
        # 根据真实请求示例构建数据，完全按照用户提供的格式
        data = {
            "flag": "1",           # 标记
            "sfyy": "1",          # 是否已阅，根据示例使用1
            "_search": "false",    # 搜索标记
            "nd": int(time.time() * 1000),  # 当前时间戳
            "queryModel.showCount": "15",   # 每页最多条数
            "queryModel.currentPage": "1",  # 当前页数
            "queryModel.sortName": "cjsj ",  # 排序字段，注意有空格
            "queryModel.sortOrder": "desc",  # 时间倒序
            "time": "0",          # 查询次数
        }
          # 构建标准HTTP请求头
        notification_headers = self.headers.copy()
        
        # 构建正确的base_url，使用传入的参数或配置
        try:
            target_base_url = self.get_school_base_url(school_name, base_url)
        except ValueError:
            target_base_url = self.base_url.rstrip('/') if self.base_url else ''
        
        base_origin = target_base_url.rstrip('/')
        
        notification_headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': base_origin,
            'Pragma': 'no-cache',
            'Referer': f'{base_origin}/xtgl/index_cxDbsy.html?flag=1',
            'Sec-CH-UA': '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        try:
            print(f"通知消息查询 - URL: {url}")
            print(f"通知消息查询 - 数据: {data}")
            print(f"通知消息查询 - Headers: {notification_headers}")
            
            req_notification = self.sess.post(
                url,
                headers=notification_headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            print(f"通知消息查询 - 响应状态码: {req_notification.status_code}")
            print(f"通知消息查询 - 响应头: {dict(req_notification.headers)}")
            print(f"通知消息查询 - 响应内容前500字符: {req_notification.text[:500]}")
            
            if req_notification.status_code != 200:
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req_notification.status_code}"}
            
            doc = pq(req_notification.text)
            if doc("h5").text() == "用户登录" or "错误" in doc("title").text():
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                notifications = req_notification.json()
                print(f"通知消息查询 - JSON解析成功: {notifications}")
            except json.JSONDecodeError as json_err:
                print(f"通知消息查询 - JSON解析失败: {json_err}")
                print(f"通知消息查询 - 原始响应: {req_notification.text}")
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
            notification_items = notifications.get("items")
            if notification_items is None:
                print(f"通知消息查询 - 响应数据中缺少items字段，原始响应: {notifications}")
                return {"code": 1005, "msg": "获取内容为空"}
            
            result = [
                {**self.split_notifications(i), "create_time": i.get("cjsj")}
                for i in notification_items
            ]
            return {"code": 1000, "msg": "获取消息成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取消息超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取消息时未记录的错误：" + str(e)}

    def get_selected_courses(self, year: int, term: int, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取已选课程信息"""
        try:
            url = self.get_school_url("selected_courses", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        temp_term = term
        term = term**2 * 3
        
        try:
            # 构建标准请求参数
            data = {
                "jg_id": "14",
                "zyh_id": "1401", 
                "njdm_id": str(year),
                "zyfx_id": "wfx",
                "bh_id": "124140102",
                "xz": "4",
                "ccdm": "w",
                "xqh_id": "1",
                "xkxnm": str(year),
                "xkxqm": str(term),
                "xkly": "0"
            }
            
            req_selected = self.sess.post(
                url,
                data=data,
                headers=self.headers,
                timeout=self.timeout,
                verify=False,
            )
            if req_selected.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_selected.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            selected = req_selected.json()
            result = {
                "year": year,
                "term": temp_term,
                "count": len(selected),
                "courses": [
                    {
                        "course_id": i.get("kch"),
                        "class_id": i.get("jxb_id"),
                        "do_id": i.get("do_jxb_id"),
                        "title": i.get("kcmc"),
                        "teacher_id": (re.findall(r"(.*?\d+)/", i.get("jsxx")))[0],
                        "teacher": (re.findall(r"/(.*?)/", i.get("jsxx")))[0],
                        "credit": float(i.get("xf", 0)),
                        "category": i.get("kklxmc"),
                        "capacity": int(i.get("jxbrs", 0)),
                        "selected_number": int(i.get("yxzrs", 0)),
                        "place": self.get_place(i.get("jxdd")),
                        "time": self.get_course_time(i.get("sksj")),
                        "optional": int(i.get("zixf", 0)),
                        "waiting": i.get("sxbj"),
                    }
                    for i in selected
                ],
            }
            return {"code": 1000, "msg": "获取已选课程成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取已选课程超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"获取已选课程时未记录的错误：{str(e)}"}

    def get_selected_courses2(self, year: int = 0, term: int = 0, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取已选课程信息2"""
        try:
            url = self.get_school_url("info", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        try:
            temp_term = term  # 保存原始term值
            if (year == 0 or term == 0):
                year_param = ""
                term_param = ""
            else:
                year_param = str(year)
                term_param = str(term**2 * 3)
                
            data = {
                "xnm": year_param,
                "xqm": term_param,
                "_search": "false",
                "queryModel.showCount": 5000,
                "queryModel.currentPage": 1,
                "queryModel.sortName": "",
                "queryModel.sortOrder": "asc",
                "time": 1,
            }
            req_selected = self.sess.post(
                url,
                data=data,
                headers=self.headers,
                timeout=self.timeout,
            )
            if req_selected.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_selected.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            selected = req_selected.json()
            result = {
                "year": year,
                "term": temp_term,
                "count": len(selected["items"]),
                "courses": [
                    {
                        "course_id": i.get("kch"),
                        "class_id": i.get("jxb_id"),
                        "title": i.get("kcmc"),
                        "credit": float(i.get("xf", 0)),
                        "teacher": i.get("jsxm"),
                        "category": i.get("kclbmc"),
                        "place": i.get("jxdd"),
                    }
                    for i in selected["items"]
                ],
            }
            return {"code": 1000, "msg": "获取已选课程2成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取已选课程2超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {
                "code": 2333,
                "msg": "服务请求失败，可能是系统维护或接口异常",
            }
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"获取已选课程2时未记录的错误：{str(e)}"}

    def get_block_courses(self, year: int, term: int, block: int, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取板块课选课列表（支持分页）"""
        try:
            url_head = self.get_school_url("block_courses_index", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        try:
            # 第一步：访问选课首页获取基础数据
            req_head_data = self.sess.get(
                url_head,
                headers=self.headers,
                timeout=self.timeout,
                verify=False,
            )
            if req_head_data.status_code != 200:
                print(f"[block_courses] 选课首页请求失败，状态码: {req_head_data.status_code}")
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_head_data.text)
            if doc("h5").text() == "用户登录":
                print("[block_courses] 选课首页被重定向到登录页，cookies 可能失效")
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
              # 第二步：分页获取可选课程列表
            try:
                url_part = self.get_school_url("block_courses", None, school_name, base_url)
            except ValueError as e:
                return {"code": 2333, "msg": str(e)}
            
            term_param = term ** 2 * 3  # 转换学期参数
            grade_year = year - 1  # 年级通常是学年-1，如2025学年对应2024年级
            
            # 基础表单数据
            base_form_data = {
                "rwlx": "2",
                "xklc": "2", 
                "xkly": "0",
                "bklx_id": "0",
                "sfkkjyxdxnxq": "0",
                "kzkcgs": "0",
                "xqh_id": "1",
                "jg_id": "14",
                "zyh_id": "1401",
                "zyfx_id": "wfx",
                "njdm_id": str(grade_year),  # 年级参数，使用grade_year
                "bh_id": "124140102",
                "bjgkczxbbjwcx": "0",
                "xbm": "1",
                "xslbdm": "wlb",
                "mzm": "01",
                "xz": "4",
                "ccdm": "w",
                "xsbj": "0",
                "sfkknj": "0",
                "sfkkzy": "0",
                "kzybkxy": "0",
                "sfznkx": "0",
                "zdkxms": "0",
                "sfkxq": "1",
                "njdm_id_xs": str(grade_year),  # 年级参数，使用grade_year
                "zyh_id_xs": "1401",
                "rlkz": "0",
                "cdrlkz": "0",
                "rlzlkz": "1",
                "kklxdm": "10",
                "xkxnm": str(year),  # 学年参数，使用year
                "xkxqm": str(term_param),
                "xkxskcgskg": "1",
                "jxbzcxskg": "0",
                "xklc": "2",
                "xkkz_id": "376AC1914F6D7A4EE0630AECC1DAD910",
                "cxbj": "0",
                "fxbj": "0"
            }
            
            # 分页获取所有课程
            all_courses = []
            page_size = 10
            current_page = 1
            max_pages = 50  # 最大页数限制，防止无限循环
            
            while current_page <= max_pages:
                # 设置分页参数
                form_data = base_form_data.copy()
                form_data["kspage"] = str((current_page - 1) * page_size + 1)
                form_data["jspage"] = str(current_page * page_size)
                
                print(f"[block_courses] 获取第{current_page}页: kspage={form_data['kspage']}, jspage={form_data['jspage']}")
                
                part_response = self.sess.post(
                    url_part,
                    headers=self.headers,
                    data=form_data,
                    timeout=self.timeout,
                    verify=False,
                )
                
                if part_response.status_code != 200:
                    print(f"[block_courses] 第{current_page}页请求失败，状态码: {part_response.status_code}")
                    break
                
                # 先检查响应内容
                response_text = part_response.text.strip()
                print(f"[block_courses] 第{current_page}页响应: {response_text[:200]}")
                
                # 特殊处理返回值 "0"
                if response_text == '"0"' or response_text == '0':
                    print(f"[block_courses] 第{current_page}页返回0，停止分页")
                    break
                
                content_type = part_response.headers.get('Content-Type', '')
                if 'json' not in content_type.lower():
                    print(f"[block_courses] 第{current_page}页非JSON响应: {content_type}")
                    break
                
                try:
                    course_data = part_response.json()
                    
                    # 检查是否为字符串类型（如 "0"）
                    if isinstance(course_data, str):
                        if course_data == "0":
                            print(f"[block_courses] 第{current_page}页返回字符串0，停止分页")
                            break
                        else:
                            print(f"[block_courses] 第{current_page}页返回未知字符串: {course_data}")
                            break
                    
                    # 检查是否为正常的对象格式
                    if not isinstance(course_data, dict):
                        print(f"[block_courses] 第{current_page}页数据类型错误: {type(course_data)}")
                        break
                    
                    # 检查是否有课程列表
                    if not course_data.get("tmpList"):
                        print(f"[block_courses] 第{current_page}页无课程列表，停止分页")
                        break
                    
                    # 获取当前页课程
                    page_courses = course_data["tmpList"]
                    print(f"[block_courses] 第{current_page}页获取到 {len(page_courses)} 门课程")
                    
                    # 添加到总列表
                    all_courses.extend(page_courses)
                    
                    # 如果当前页课程数少于页面大小，说明已到最后一页
                    if len(page_courses) < page_size:
                        print(f"[block_courses] 第{current_page}页课程数({len(page_courses)})少于页面大小({page_size})，停止分页")
                        break
                    
                    current_page += 1
                    
                except Exception as e:
                    print(f"[block_courses] 第{current_page}页JSON解析异常: {str(e)}")
                    break
            
            # 检查是否获取到课程
            if not all_courses:
                return {
                    "code": 1005,
                    "msg": "该板块暂无可选课程，可能是选课时间未到、已结束或参数错误",
                    "debug_info": {
                        "year": year,
                        "term": term,
                        "block": block,
                        "xkxqm": term_param,
                        "pages_checked": current_page - 1
                    }
                }
            
            # 处理所有课程数据
            result = {
                "year": year,
                "term": term,
                "block": block,
                "count": len(all_courses),
                "pages": current_page - 1,
                "courses": [
                    {
                        "course_id": course.get("kch_id"),
                        "class_id": course.get("jxb_id"), 
                        "do_id": course.get("do_jxb_id"),
                        "title": course.get("kcmc"),
                        "teacher": course.get("jsxx", "").split("/")[1] if "/" in course.get("jsxx", "") else "",
                        "teacher_id": course.get("jsxx", "").split("/")[0] if "/" in course.get("jsxx", "") else "",
                        "credit": float(course.get("xf", 0)),
                        "category": course.get("kklxmc"),
                        "capacity": int(course.get("jxbrl", 0)),
                        "selected_number": int(course.get("yxzrs", 0)),
                        "available": int(course.get("jxbrl", 0)) - int(course.get("yxzrs", 0)),
                        "place": course.get("jxdd"),
                        "time": course.get("sksj"),
                        "weeks": course.get("zcsm"),
                        "campus": course.get("xqmc"),
                        "optional": course.get("sfkx") == "1",
                    }
                    for course in all_courses
                ],
            }
            
            print(f"[block_courses] 总共获取到 {len(all_courses)} 门课程，共 {current_page - 1} 页")
            return {"code": 1000, "msg": "获取板块课程成功", "data": result}
            
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取板块课程超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {
                "code": 2333,
                "msg": "服务请求失败，可能是系统维护或接口异常",
            }
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"获取板块课程时未记录的错误：{str(e)}"}

    def get_course_classes(self, year: int, term: int, course_id: str, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取指定课程的教学班列表"""
        try:
            url_classes = self.get_school_url("course_classes", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        try:
            # 访问教学班查询接口
            term_param = term ** 2 * 3  # 转换学期参数
            grade_year = year - 1  # 年级通常是学年-1，如2025学年对应2024年级
            
            # 根据真实请求构建表单数据
            form_data = {
                "rwlx": "2",
                "xkly": "0",
                "bklx_id": "0",
                "sfkkjyxdxnxq": "0",
                "kzkcgs": "0",
                "xqh_id": "1",
                "jg_id": "14",
                "zyh_id": "1401",
                "zyfx_id": "wfx",
                "txbsfrl": "0",
                "njdm_id": str(grade_year),
                "bh_id": "124140102",
                "xbm": "1",
                "xslbdm": "wlb",
                "mzm": "01",
                "xz": "4",
                "ccdm": "w",
                "xsbj": "0",
                "sfkknj": "0",
                "gnjkxdnj": "0",
                "sfkkzy": "0",
                "kzybkxy": "0",
                "sfznkx": "0",
                "zdkxms": "0",
                "sfkxq": "1",
                "sfkcfx": "0",
                "bbhzxjxb": "0",
                "kkbk": "0",
                "kkbkdj": "0",
                "xkxnm": str(year),
                "xkxqm": str(term_param),
                "xkxskcgskg": "1",
                "njdm_id_xs": str(grade_year),
                "zyh_id_xs": "1401",
                "rlkz": "0",
                "cdrlkz": "0",
                "rlzlkz": "1",
                "kklxdm": "10",
                "kch_id": course_id,  # 课程ID
                "jxbzcxskg": "0",
                "xklc": "2",
                "xkkz_id": "376AC1914F6D7A4EE0630AECC1DAD910",
                "cxbj": "0",
                "fxbj": "0"
            }
            
            print(f"[course_classes] 查询课程 {course_id} 的教学班")
            print(f"[course_classes] POST {url_classes}")
            print(f"[course_classes] 表单数据: {form_data}")
            
            classes_response = self.sess.post(
                url_classes,
                headers=self.headers,
                data=form_data,
                timeout=self.timeout,
            )
            
            if classes_response.status_code != 200:
                print(f"[course_classes] 请求失败，状态码: {classes_response.status_code}")
                return {"code": 2333, "msg": f"获取教学班失败，状态码: {classes_response.status_code}"}
            
            # 检查响应内容
            response_text = classes_response.text.strip()
            content_type = classes_response.headers.get('Content-Type', '')
            print(f"[course_classes] 响应Content-Type: {content_type}")
            print(f"[course_classes] 响应内容前500: {response_text[:500]}")
            
            # 检查是否为登录页面
            if "用户登录" in response_text:
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 特殊处理返回值 "0"
            if response_text == '"0"' or response_text == '0':
                return {
                    "code": 1005,
                    "msg": "该课程暂无教学班，可能课程ID错误或选课时间未到",
                    "debug_info": {
                        "course_id": course_id,
                        "year": year,
                        "term": term,
                        "response": response_text
                    }
                }
            
            # 判断是否为 JSON
            if 'json' not in content_type.lower():
                return {
                    "code": 2333,
                    "msg": "返回内容非JSON，可能被重定向或参数错误",
                    "content_type": content_type,
                    "text": response_text[:500],
                    "headers": dict(classes_response.headers)
                }
            
            try:
                # 尝试解析 JSON
                classes_data = classes_response.json()
                
                # 检查是否为字符串类型（如 "0"）
                if isinstance(classes_data, str):
                    if classes_data == "0":
                        return {
                            "code": 1005,
                            "msg": "该课程暂无教学班，可能课程ID错误或选课时间未到",
                            "debug_info": {
                                "course_id": course_id,
                                "response": classes_data
                            }
                        }
                    else:
                        return {
                            "code": 2333,
                            "msg": f"服务器返回未知字符串: {classes_data}",
                            "debug_info": {"response": classes_data}
                        }
                  # 检查是否为正常的对象格式或列表格式
                if isinstance(classes_data, list):
                    # 如果直接返回列表，说明这就是教学班列表
                    if not classes_data:
                        return {
                            "code": 1005,
                            "msg": "该课程暂无教学班",
                            "debug_info": {
                                "course_id": course_id,
                                "response": "空列表"
                            }
                        }
                    
                    # 直接处理列表格式的教学班数据
                    result = {
                        "year": year,
                        "term": term,
                        "course_id": course_id,
                        "count": len(classes_data),
                        "classes": [
                            {
                                "class_id": jxb.get("jxb_id"),
                                "do_id": jxb.get("do_jxb_id"),
                                "class_name": jxb.get("jxbmc"),
                                "teacher": jxb.get("jsxx", "").split("/")[1] if "/" in jxb.get("jsxx", "") else jxb.get("jsxx", ""),
                                "teacher_id": jxb.get("jsxx", "").split("/")[0] if "/" in jxb.get("jsxx", "") else "",
                                "capacity": int(jxb.get("jxbrl", 0)),
                                "selected_number": int(jxb.get("yxzrs", 0)),
                                "available": int(jxb.get("jxbrl", 0)) - int(jxb.get("yxzrs", 0)),
                                "time": jxb.get("sksj"),
                                "weeks": jxb.get("zcsm"),
                                "place": jxb.get("jxdd"),
                                "campus": jxb.get("xqmc"),
                                "optional": jxb.get("sfkx") == "1",
                                "note": jxb.get("xkbz", ""),  # 选课备注
                                "credit": float(jxb.get("xf", 0)),
                            }
                            for jxb in classes_data
                        ],
                    }
                    
                    print(f"[course_classes] 课程 {course_id} 查询到 {len(result['classes'])} 个教学班（列表格式）")
                    return {"code": 1000, "msg": "获取教学班成功", "data": result}
                
                elif not isinstance(classes_data, dict):
                    return {
                        "code": 2333,
                        "msg": f"返回数据类型错误，期望dict或list得到{type(classes_data)}",
                        "debug_info": {"response": str(classes_data)[:500]}
                    }
                
                # 检查是否有教学班列表
                if not classes_data.get("jxbList"):
                    return {
                        "code": 1005,
                        "msg": "该课程暂无教学班",
                        "debug_info": {
                            "course_id": course_id,
                            "keys": list(classes_data.keys()) if isinstance(classes_data, dict) else [],
                            "response": str(classes_data)[:500]
                        }
                    }
                
                # 处理教学班数据
                result = {
                    "year": year,
                    "term": term,
                    "course_id": course_id,
                    "count": len(classes_data["jxbList"]),
                    "classes": [
                        {
                            "class_id": jxb.get("jxb_id"),
                            "do_id": jxb.get("do_jxb_id"),
                            "class_name": jxb.get("jxbmc"),
                            "teacher": jxb.get("jsxx", "").split("/")[1] if "/" in jxb.get("jsxx", "") else jxb.get("jsxx", ""),
                            "teacher_id": jxb.get("jsxx", "").split("/")[0] if "/" in jxb.get("jsxx", "") else "",
                            "capacity": int(jxb.get("jxbrl", 0)),
                            "selected_number": int(jxb.get("yxzrs", 0)),
                            "available": int(jxb.get("jxbrl", 0)) - int(jxb.get("yxzrs", 0)),
                            "time": jxb.get("sksj"),
                            "weeks": jxb.get("zcsm"),
                            "place": jxb.get("jxdd"),
                            "campus": jxb.get("xqmc"),
                            "optional": jxb.get("sfkx") == "1",
                            "note": jxb.get("xkbz"),  # 选课备注
                            "credit": float(jxb.get("xf", 0)),
                        }
                        for jxb in classes_data["jxbList"]
                    ],
                }
                
                print(f"[course_classes] 课程 {course_id} 查询到 {len(result['classes'])} 个教学班")
                return {"code": 1000, "msg": "获取教学班成功", "data": result}
                
            except Exception as e:
                print(f"[course_classes] JSON解析异常: {str(e)}")
                return {
                    "code": 2333,
                    "msg": f"教学班数据格式错误: {str(e)}",
                    "debug_info": {
                        "text": response_text[:500],
                        "content_type": content_type,
                        "error": str(e)
                    }
                }
                
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取教学班超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {
                "code": 2333,
                "msg": "服务请求失败，可能是系统维护或接口异常",
            }
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"获取教学班时未记录的错误：{str(e)}"}

    def select_course(self, sid: str, course_id: str, do_id: str, kklxdm: str, year: int, term: int, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """选课"""
        try:
            url_select = self.get_school_url("select_course", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        try:
            term = term**2 * 3
            select_data = {
                "jxb_ids": do_id,
                "kch_id": course_id,
                # 'rwlx': '3',
                # 'rlkz': '0',
                # 'rlzlkz': '1',
                # 'sxbj': '1',
                # 'xxkbj': '0',
                # 'cxbj': '0',
                "qz": "0",
                # 'xkkz_id': '9B247F4EFD6291B9E055000000000001',
                "xkxnm": str(year),
                "xkxqm": str(term),
                "njdm_id": str(sid[0:2]),
                "zyh_id": str(sid[2:6]),
                "kklxdm": str(kklxdm),
                # 'xklc': '1',
            }
            req_select = self.sess.post(
                url_select,
                headers=self.headers,
                data=select_data,
                timeout=self.timeout,
                verify=False,
            )
            if req_select.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_select.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            result = req_select.json()
            return {"code": 1000, "msg": "选课成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "选课超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"选课时未记录的错误：{str(e)}"}

    def cancel_course(self, do_id: str, course_id: str, year: int, term: int, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """取消选课"""
        try:
            url_cancel = self.get_school_url("drop_course", None, school_name, base_url)
        except ValueError as e:
            return {"code": 2333, "msg": str(e)}
            
        try:
            term = term**2 * 3
            cancel_data = {
                "jxb_ids": do_id,
                "kch_id": course_id,
                "xkxnm": str(year),
                "xkxqm": str(term),
            }
            req_cancel = self.sess.post(
                url_cancel,
                headers=self.headers,
                data=cancel_data,
                timeout=self.timeout,
                verify=False,
            )
            if req_cancel.status_code != 200:
                return {"code": 2333, "msg": "教务系统服务异常"}
            doc = pq(req_cancel.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            result = {"status": re.findall(r"(\d+)", req_cancel.text)[0]}
            return {"code": 1000, "msg": "退课成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "选课超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": f"选课时未记录的错误：{str(e)}"}

    # ============= utils =================
    
    def get_gpa(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取GPA"""
        try:
            url = self.get_school_url("gpa", "xsxy/xsxyqk_cxXsxyqkIndex.html?gnmkdm=N105515&layout=default", school_name, base_url)
        except ValueError:
            return "init"
            
        req_gpa = self.sess.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )
        doc = pq(req_gpa.text)
        if doc("h5").text() == "用户登录":
            return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
        allc_str = [allc.text() for allc in doc("font[size='2px']").items()]
        try:
            # Ensure we have enough elements and the element is a string
            if len(allc_str) > 2 and isinstance(allc_str[2], str):
                gpa = float(allc_str[2])
                return gpa
            else:
                return "init"
        except Exception:
            return "init"

    def get_course_category(self, type, item, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """根据课程号获取类别"""
        if type not in self.detail_category_type:
            return item.get("KCLBMC")
        if not item.get("KCH"):
            return None
        
        try:
            url = self.get_school_url("course_category", f"jxjhgl/common_cxKcJbxx.html?id={item['KCH']}", school_name, base_url)
        except ValueError:
            return item.get("KCLBMC")
            
        req_category = self.sess.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )
        doc = pq(req_category.text)
        ths = doc("th")
        try:
            data_list = [(th.text).strip() for th in ths]
            return data_list[6]
        except:
            return None

    @classmethod
    def encrypt_password(cls, pwd, n, e):
        """对密码base64编码"""
        message = str(pwd).encode()
        rsa_n = binascii.b2a_hex(binascii.a2b_base64(n))
        rsa_e = binascii.b2a_hex(binascii.a2b_base64(e))
        key = rsa.PublicKey(int(rsa_n, 16), int(rsa_e, 16))
        encropy_pwd = rsa.encrypt(message, key)
        result = binascii.b2a_base64(encropy_pwd)
        return result

    @classmethod
    def parse_int(cls, digits):
        if not digits:
            return None
        if not digits.isdigit():
            return digits
        return int(digits)

    @classmethod
    def align_floats(cls, floats):
        if not floats:
            return None
        if floats == "无":
            return "0.0"
        return format(float(floats), ".1f")

    @classmethod
    def display_course_time(cls, sessions):
        if not sessions:
            return None
        args = re.findall(r"(\d+)", sessions)
        start_time = cls.raspisanie[int(args[0]) + 1][0]
        end_time = cls.raspisanie[int(args[0]) + 1][1]
        return f"{start_time}~{end_time}"

    @classmethod
    def list_sessions(cls, sessions):
        if not sessions:
            return None
        args = re.findall(r"(\d+)", sessions)
        return [n for n in range(int(args[0]), int(args[1]) + 1)]

    @classmethod
    def list_weeks(cls, weeks):
        """返回课程所含周列表"""
        if not weeks:
            return None
        args = re.findall(r"[^,]+", weeks)
        week_list = []
        for item in args:
            if "-" in item:
                weeks_pair = re.findall(r"(\d+)", item)
                if len(weeks_pair) != 2:
                    continue
                if "单" in item:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        if i % 2 == 1:
                            week_list.append(i)
                elif "双" in item:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        if i % 2 == 0:
                            week_list.append(i)
                else:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        week_list.append(i)
            else:
                week_num = re.findall(r"(\d+)", item)
                if len(week_num) == 1:
                    week_list.append(int(week_num[0]))
        return week_list

    @classmethod
    def get_academia_statistics(cls, display_statistics):
        display_statistics = "".join(display_statistics.split())
        gpa_list = re.findall(r"([0-9]{1,}[.][0-9]*)", display_statistics)
        if len(gpa_list) == 0 or not cls.is_number(gpa_list[0]):
            gpa = None
        else:
            gpa = float(gpa_list[0])
        plan_list = re.findall(
            r"计划总课程(\d+)门通过(\d+)门?.*未通过(\d+)门?.*未修(\d+)?.*在读(\d+)门?.*计划外?.*通过(\d+)门?.*未通过(\d+)门",
            display_statistics,
        )
        if len(plan_list) == 0 or len(plan_list[0]) < 7:
            return {"gpa": gpa}
        plan_list = plan_list[0]
        return {
            "gpa": gpa,  # 平均学分绩点GPA
            "planed_courses": {
                "total": int(plan_list[0]),  # 计划内总课程数
                "passed": int(plan_list[1]),  # 计划内已过课程数
                "failed": int(plan_list[2]),  # 计划内未过课程数
                "missed": int(plan_list[3]),  # 计划内未修课程数
                "in": int(plan_list[4]),  # 计划内在读课程数
            },
            "unplaned_courses": {
                "passed": int(plan_list[5]),  # 计划外已过课程数
                "failed": int(plan_list[6]),  # 计划外未过课程数
            },
        }

    @classmethod
    def get_academia_type_statistics(cls, content: str):
        finder = re.findall(
            r"\"(.*)&nbsp.*要求学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;).*获得学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;).*未获得学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;)[\s\S]*?<span id='showKc(.*)'></span>",
            content,
        )
        finder_list = list({}.fromkeys(finder).keys())
        academia_list = [
            list(i)
            for i in finder_list
            if i[0] != ""  # 类型名称不为空
            and len(i[0]) <= 20  # 避免正则到首部过长类型名称
            and "span" not in i[-1]  # 避免正则到尾部过长类型名称
            and i[0] not in cls.ignore_type  # 忽略的类型名称
        ]
        result = {
            i[0]: {
                "id": i[-1],
                "credits": {
                    "required": i[1] if cls.is_number(i[1]) and i[1] != "0" else None,
                    "earned": i[2] if cls.is_number(i[2]) and i[2] != "0" else None,
                    "missed": i[3] if cls.is_number(i[3]) and i[3] != "0" else None,
                },
            }
            for i in academia_list
        }
        return result

    @classmethod
    def get_display_term(cls, sid, year, term):
        """
        计算培养方案具体学期转化成中文
        note: 留级和当兵等情况会不准确
        """
        if (sid and year and term) is None:
            return None
        grade = int(sid[0:2])
        year = int(year[2:4])
        term = int(term)
        dict = {
            grade: "大一上" if term == 1 else "大一下",
            grade + 1: "大二上" if term == 1 else "大二下",
            grade + 2: "大三上" if term == 1 else "大三下",
            grade + 3: "大四上" if term == 1 else "大四下",
        }
        return dict.get(year)

    @classmethod
    def split_merge_display(cls, schedule):
        """
        拆分同周同天同课程不同时段数据合并的问题
        """
        repetIndex = []
        count = 0
        for items in schedule["courses"]:
            for index in range(len(schedule["courses"])):
                if (schedule["courses"]).index(items) == count:  # 如果对比到自己就忽略
                    continue
                elif (
                    items["course_id"]
                    == schedule["courses"][index]["course_id"]  # 同周同天同课程
                    and items["weekday"] == schedule["courses"][index]["weekday"]
                    and items["weeks"] == schedule["courses"][index]["weeks"]
                ):
                    repetIndex.append(index)  # 满足条件记录索引
            count += 1  # 记录当前对比课程的索引
        if len(repetIndex) % 2 != 0:  # 检测到同一课程在一天内存在多个时段，当前逻辑不处理此情况
            return schedule
        for r in range(0, len(repetIndex), 2):  # 索引数组两两成对，故步进2循环
            fir = repetIndex[r]
            sec = repetIndex[r + 1]
            if len(re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])) == 4:
                schedule["courses"][fir]["sessions"] = (
                    re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])[0]
                    + "-"
                    + re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])[1]
                    + "节"
                )
                schedule["courses"][fir]["list_sessions"] = cls.list_sessions(
                    schedule["courses"][fir]["sessions"]
                )
                schedule["courses"][fir]["time"] = cls.display_course_time(
                    schedule["courses"][fir]["sessions"]
                )

                schedule["courses"][sec]["sessions"] = (
                    re.findall(r"(\d+)", schedule["courses"][sec]["sessions"])[2]
                    + "-"
                    + re.findall(r"(\d+)", schedule["courses"][sec]["sessions"])[3]
                    + "节"
                )
                schedule["courses"][sec]["list_sessions"] = cls.list_sessions(
                    schedule["courses"][sec]["sessions"]
                )
                schedule["courses"][sec]["time"] = cls.display_course_time(
                    schedule["courses"][sec]["sessions"]
                )
        return schedule

    @classmethod
    def split_notifications(cls, item):
        if not item.get("xxnr"):
            return {"type": None, "content": None}
        content_list = re.findall(r"(.*):(.*)", item["xxnr"])
        if len(content_list) == 0:
            return {"type": None, "content": item["xxnr"]}
        return {"type": content_list[0][0], "content": content_list[0][1]}

    @classmethod
    def get_place(cls, place):
        return place.split("<br/>")[0] if "<br/>" in place else place

    @classmethod
    def get_course_time(cls, time):
        return "、".join(time.split("<br/>")) if "<br/>" in time else time

    @classmethod
    def is_number(cls, s):
        if s == "":
            return False
        try:
            float(s)
            return True
        except ValueError:
            pass
        try:
            for i in s:
                unicodedata.numeric(i)
            return True
        except (TypeError, ValueError):
            pass
        return False

    def get_evaluate_menu(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取教学评价菜单（可评价课程列表）"""
        try:
            url = self.get_school_url('evaluate', None, school_name, base_url)
        except ValueError:
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/xspjgl/xspj_cxXspjIndex.html?doType=query&gnmkdm=N401605"
        
        # 构建POST请求数据
        data = {
            "_search": "false",
            "nd": int(time.time() * 1000),
            "queryModel.showCount": "15",
            "queryModel.currentPage": "1",
            "queryModel.sortName": "kcmc,jzgmc ",
            "queryModel.sortOrder": "asc",
            "time": "0"
        }
        
        resp = self.sess.post(url, headers=self.headers, data=data, timeout=self.timeout, verify=False)
        if resp.status_code != 200:
            return {"code": 2333, "msg": f"获取评价菜单失败，状态码: {resp.status_code}"}
        
        try:
            result = resp.json()
        except json.JSONDecodeError:
            return {"code": 2333, "msg": "响应格式错误，无法解析JSON"}
        
        if not result.get("items"):
            return {"code": 1005, "msg": "暂无需要评价的课程"}
        
        # 解析课程列表
        courses = []
        for item in result["items"]:
            courses.append({
                "course_id": item.get("kch_id"),
                "course_name": item.get("kcmc"),
                "teacher": item.get("jzgmc"),
                "class_name": item.get("jxbmc"),
                "classroom": item.get("jxdd"),
                "time": item.get("sksj"),
                "college": item.get("jgmc"),
                "status": item.get("tjztmc"),  # 评价状态：未评、已评等
                "jxb_id": item.get("jxb_id"),  # 教学班ID，用于后续评价
                "jgh_id": item.get("jgh_id"),  # 教职工ID，用于评价详情
                "xsdm": item.get("xsdm"),  # 学生代码
                "evaluate_url": f"{self.base_url.rstrip('/')}/jwglxt/xspjgl/xspj_cxXspjIndex.html?doType=details&gnmkdm=N401605&layout=default&jxb_id={item.get('jxb_id')}"
            })
        
        return {
            "code": 1000, 
            "msg": "获取评价菜单成功", 
            "data": {
                "courses": courses,
                "total": result.get("totalResult", 0),
                "current_page": result.get("currentPage", 1),
                "total_pages": result.get("totalPage", 1)
            }
        }

    def get_evaluate_detail(self, jxb_id: str, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取某门课程的评价详情"""
        try:
            url = self.get_school_url('evaluate_detail', None, school_name, base_url)
        except ValueError:
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/xspjgl/xspj_cxXspjDisplay.html?gnmkdm=N401605"
        
        # 从课程列表中获取课程信息（需要先调用get_evaluate_menu）
        menu_result = self.get_evaluate_menu(school_name, base_url)
        if menu_result.get("code") != 1000:
            return menu_result
        
        # 找到对应的课程信息
        course_info = None
        for course in menu_result["data"]["courses"]:
            if course["jxb_id"] == jxb_id:
                course_info = course
                break
        
        if not course_info:
            return {"code": 2333, "msg": "未找到对应的课程信息"}
        
        print(f"课程信息: {course_info}")
        
        # 构建POST请求数据 - 使用课程列表中的原始数据
        # 从课程列表中获取原始数据
        original_course_data = None
        for item in menu_result["data"]["courses"]:
            if item["jxb_id"] == jxb_id:
                original_course_data = item
                break
        
        if not original_course_data:
            return {"code": 2333, "msg": "未找到原始课程数据"}
        
        # 使用原始数据构建请求参数
        data = {
            "jxb_id": jxb_id,
            "kch_id": course_info["course_id"],
            "xsdm": course_info.get("xsdm", "01"),  # 自动取课程信息里的xsdm
            "jgh_id": original_course_data.get("jgh_id", ""),  # 使用原始数据中的jgh_id
            "tjzt": "-1",
            "pjmbmcb_id": "",
            "sfcjlrjs": "1"
        }
        
        # 如果jgh_id仍然为空，尝试从其他字段获取
        if not data["jgh_id"]:
            # 尝试从课程信息中获取教师ID
            teacher_info = course_info.get("teacher_id", "")
            if teacher_info:
                data["jgh_id"] = teacher_info
        
        print(f"POST请求数据: {data}")
        
        resp = self.sess.post(url, headers=self.headers, data=data, timeout=self.timeout, verify=False)
        if resp.status_code != 200:
            return {"code": 2333, "msg": f"获取评价详情失败，状态码: {resp.status_code}"}
        
        html = resp.text
        print(f"HTML响应长度: {len(html)}")
        print(f"HTML前1000字符: {html[:1000]}")
        print(f"HTML中间部分(6000-8000字符): {html[6000:8000]}")
        print(f"HTML后1000字符: {html[-1000:]}")
        
        # 检查是否被重定向到登录页面
        if '用户登录' in html or 'login' in html.lower():
            return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
        
        # 检查参数错误
        if '课程号ID,教学班ID,教职工ID参数异常' in html:
            return {"code": 2333, "msg": "参数错误：课程号ID,教学班ID,教职工ID参数异常，请检查课程信息"}
        
        if '目前未对你放开教学质量评价' in html:
            return {"code": 1005, "msg": "目前未对你放开教学质量评价"}
        
        soup = BeautifulSoup(html, 'html.parser')
        # 获取panel（评价对象）参数
        panel = soup.find('div', class_='panel-pjdx')
        panel_params = {}
        if panel:
            panel_params['pjmbmcb_id'] = panel.get('data-pjmbmcb_id', '')
            panel_params['pjdxdm'] = panel.get('data-pjdxdm', '')
            panel_params['xspfb_id'] = panel.get('data-xspfb_id', '')
            panel_params['fxzgf'] = panel.get('data-fxzgf', '')
        # 获取表单action
        form = soup.find('form', {'id': 'ajaxForm1'})
        action = form.get('action') if form else ''
        if action and not action.startswith('http'):
            action = urljoin(self.base_url, action)
        # 获取课程信息
        course_name = course_info["course_name"]
        teacher_name = course_info["teacher"]
        # 获取评价项目
        evaluation_items = []
        is_evaluated = False  # 标记是否已评价
        tr_elements = soup.find_all('tr', {'class': 'tr-xspj'})
        for i, tr in enumerate(tr_elements):
            content_td = tr.find('td', style=lambda x: x and 'width: 400px' in x)
            if not content_td:
                continue
            content = content_td.get_text(strip=True).replace('*', '').strip()
            value_td = tr.find_all('td')
            if len(value_td) >= 2:
                value_content = value_td[1].get_text(strip=True)
                input_elem = tr.find('input')
                has_input = input_elem is not None
                if not has_input:
                    is_evaluated = True
                # 解析tr的所有data属性
                pjzbxm_id = tr.get('data-pjzbxm_id', '')
                zsmbmcb_id = tr.get('data-zsmbmcb_id', '')
                pfdjdmb_id = tr.get('data-pfdjdmb_id', '')
                if has_input:
                    input_name = input_elem.get('name', '')
                    if not input_name and pjzbxm_id:
                        input_name = pjzbxm_id
                    min_score = input_elem.get('data-zxfz', '30')
                    max_score = input_elem.get('data-zdfz', '100')
                    placeholder = input_elem.get('placeholder', '')
                    current_value = input_elem.get('value', '')
                    weight = tr.get('data-qzz', '0.2')
                    evaluation_items.append({
                        "content": content,
                        "input_name": input_name,
                        "min_score": int(min_score),
                        "max_score": int(max_score),
                        "placeholder": placeholder,
                        "current_value": current_value,
                        "weight": float(weight),
                        "pjzbxm_id": pjzbxm_id,
                        "zsmbmcb_id": zsmbmcb_id,
                        "pfdjdmb_id": pfdjdmb_id,
                        "has_input": True
                    })
                else:
                    evaluation_items.append({
                        "content": content,
                        "score": value_content,
                        "pjzbxm_id": pjzbxm_id,
                        "zsmbmcb_id": zsmbmcb_id,
                        "pfdjdmb_id": pfdjdmb_id,
                        "has_input": False
                    })
        comment_textarea = soup.find('textarea', {'id': lambda x: x and x.endswith('_py')})
        comment_name = comment_textarea.get('name', 'py') if comment_textarea else 'py'
        # 获取评语内容（已评价或未评价）
        comment_value = ""
        py_div = soup.find('div', id='pyDiv')
        if py_div:
            comment_box = py_div.find('div', class_='input-xspj')
            if comment_box:
                comment_value = comment_box.get_text(strip=True)
        # 返回panel参数和每个评价项的所有ID
        return {"code": 1000, "msg": "获取评价详情成功", "data": {
            'action': action,
            'course_name': course_name,
            'teacher_name': teacher_name,
            'jxb_id': jxb_id,
            'kch_id': course_info["course_id"],
            'evaluation_items': evaluation_items,
            'comment_name': comment_name,
            'comment_max_length': 500,
            'is_evaluated': is_evaluated,
            'comment': comment_value,
            'jgh_id': course_info.get('jgh_id', ''),  # 新增，确保后续POST参数不为空
            **panel_params
        }}

    def save_evaluate(self, action_url: str, jxb_id: str, kch_id: str, evaluation_data: dict, comment: str = ""):
        """保存评价内容（严格官方嵌套结构，与提交一致，仅url不同）"""
        # 先获取评价详情，拿到所有嵌套参数
        detail_result = self.get_evaluate_detail(jxb_id)
        if detail_result.get('code') != 1000:
            return detail_result
        detail_data = detail_result['data']
        evaluation_items = detail_data['evaluation_items']
        # 组装分数字典
        frontend_items = {item['input_name']: item['score'] for item in evaluation_data.get('items', []) if 'input_name' in item}
        # 组装嵌套结构
        data = {}
        # 顶层参数
        data['ztpjbl'] = '100'
        data['jszdpjbl'] = '0'
        data['xykzpjbl'] = '0'
        data['jxb_id'] = jxb_id
        data['kch_id'] = kch_id
        # 统一jgh_id取值
        data['jgh_id'] = detail_data.get('jgh_id') or detail_data.get('teacher_id') or ''
        data['xsdm'] = detail_data.get('xsdm', '01')
        data['tjzt'] = '-1'  # 保存时为-1
        # panel参数
        data['modelList[0].pjmbmcb_id'] = detail_data.get('pjmbmcb_id', '')
        data['modelList[0].pjdxdm'] = detail_data.get('pjdxdm', '01')
        data['modelList[0].xspfb_id'] = detail_data.get('xspfb_id', '')
        data['modelList[0].fxzgf'] = detail_data.get('fxzgf', '')
        # 评语为空时自动填充
        if not comment or str(comment).strip() == "":
            comment = "无评语!"
        data['modelList[0].py'] = comment
        # 评价项目
        for idx, item in enumerate(evaluation_items):
            if not item.get('has_input'):
                continue
            score = frontend_items.get(item['input_name'])
            if score is None:
                continue
            prefix = f"modelList[0].xspjList[0].childXspjList[{idx}]"
            data[f"{prefix}.pjf"] = str(score)
            data[f"{prefix}.pjzbxm_id"] = item.get('pjzbxm_id', '')
            data[f"{prefix}.pfdjdmb_id"] = item.get('pfdjdmb_id', '')
            data[f"{prefix}.zsmbmcb_id"] = item.get('zsmbmcb_id', '')
        # 评价项目ID
        data['modelList[0].xspjList[0].pjzbxm_id'] = evaluation_items[0]['pjzbxm_id'] if evaluation_items else ''
        data['modelList[0].pjzt'] = '1'
        # 构造完整headers
        referer_url = f"{self.base_url.rstrip('/')}/jwglxt/xspjgl/xspj_cxXspjIndex.html?doType=details&gnmkdm=N401605&layout=default&jxb_id={jxb_id}"
        origin_url = self.base_url.rstrip('/')
        headers = self.headers.copy()
        headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': origin_url,
            'Pragma': 'no-cache',
            'Referer': referer_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        print('最终POST数据:', data)
        resp = self.sess.post(action_url, data=data, headers=headers, timeout=self.timeout, verify=False)
        print('正方系统保存响应:', resp.text[:500])
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('code') == 200 or '保存' in result.get('msg', '') or '成功' in result.get('msg', ''):
                    return {"code": 1000, "msg": "保存成功"}
                else:
                    return {"code": 2333, "msg": result.get('msg', '保存失败，请检查评价内容')}
            except Exception:
                html = resp.text
                if '保存成功' in html or '评价已保存' in html:
                    return {"code": 1000, "msg": "保存成功"}
                elif '评价分数不能为空' in html:
                    return {"code": 2333, "msg": "评价分数不能为空"}
                elif '评语不能超过500字' in html:
                    return {"code": 2333, "msg": "评语不能超过500字"}
                else:
                    return {"code": 2333, "msg": "保存失败，请检查评价内容"}
        return {"code": 2333, "msg": "保存失败"}

    def submit_evaluate(self, action_url: str, jxb_id: str, kch_id: str, evaluation_data: dict, comment: str = ""):
        """提交评价（严格官方嵌套结构）"""
        # 先获取评价详情，拿到所有嵌套参数
        detail_result = self.get_evaluate_detail(jxb_id)
        if detail_result.get('code') != 1000:
            return detail_result
        detail_data = detail_result['data']
        evaluation_items = detail_data['evaluation_items']
        # 组装分数字典
        frontend_items = {item['input_name']: item['score'] for item in evaluation_data.get('items', []) if 'input_name' in item}
        # 组装嵌套结构
        data = {}
        # 顶层参数
        data['ztpjbl'] = '100'
        data['jszdpjbl'] = '0'
        data['xykzpjbl'] = '0'
        data['jxb_id'] = jxb_id
        data['kch_id'] = kch_id
        # 统一jgh_id取值
        data['jgh_id'] = detail_data.get('jgh_id') or detail_data.get('teacher_id') or ''
        data['xsdm'] = detail_data.get('xsdm', '01')
        data['tjzt'] = '1'
        # panel参数
        data['modelList[0].pjmbmcb_id'] = detail_data.get('pjmbmcb_id', '')
        data['modelList[0].pjdxdm'] = detail_data.get('pjdxdm', '01')
        data['modelList[0].xspfb_id'] = detail_data.get('xspfb_id', '')
        data['modelList[0].fxzgf'] = detail_data.get('fxzgf', '')
        # 评语为空时自动填充
        if not comment or str(comment).strip() == "":
            comment = "无评语!"
        data['modelList[0].py'] = comment
        # 评价项目
        for idx, item in enumerate(evaluation_items):
            if not item.get('has_input'):
                continue
            score = frontend_items.get(item['input_name'])
            if score is None:
                continue
            prefix = f"modelList[0].xspjList[0].childXspjList[{idx}]"
            data[f"{prefix}.pjf"] = str(score)
            data[f"{prefix}.pjzbxm_id"] = item.get('pjzbxm_id', '')
            data[f"{prefix}.pfdjdmb_id"] = item.get('pfdjdmb_id', '')
            data[f"{prefix}.zsmbmcb_id"] = item.get('zsmbmcb_id', '')
        # 评价项目ID
        data['modelList[0].xspjList[0].pjzbxm_id'] = evaluation_items[0]['pjzbxm_id'] if evaluation_items else ''
        data['modelList[0].pjzt'] = '1'
        # 构造完整headers
        referer_url = f"{self.base_url.rstrip('/')}/jwglxt/xspjgl/xspj_cxXspjIndex.html?doType=details&gnmkdm=N401605&layout=default&jxb_id={jxb_id}"
        origin_url = self.base_url.rstrip('/')
        headers = self.headers.copy()
        headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': origin_url,
            'Pragma': 'no-cache',
            'Referer': referer_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        print('最终POST数据:', data)
        resp = self.sess.post(action_url, data=data, headers=headers, timeout=self.timeout, verify=False)
        print('正方系统响应:', resp.text[:500])
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('code') == 200 or '成功' in result.get('msg', ''):
                    return {"code": 1000, "msg": "提交成功"}
                else:
                    return {"code": 2333, "msg": result.get('msg', '提交失败，请检查评价内容')}
            except Exception:
                html = resp.text
                if '提交成功' in html or '评价已提交' in html:
                    return {"code": 1000, "msg": "提交成功"}
                elif '评价分数不能为空' in html:
                    return {"code": 2333, "msg": "评价分数不能为空"}
                elif '评语不能超过500字' in html:
                    return {"code": 2333, "msg": "评语不能超过500字"}
                else:
                    return {"code": 2333, "msg": "提交失败，请检查评价内容"}
        return {"code": 2333, "msg": "提交失败"}

if __name__ == "__main__":
    from pprint import pprint
    import json
    import base64
    import sys
    import os

    base_url = "https://xxxx.xxx.edu.cn"  # 教务系统URL
    sid = "123456"  # 学号
    password = "abc654321"  # 密码
    lgn_cookies = (
        {
            # "insert_cookie": "",
            # "route": "",
            "JSESSIONID": ""
        }
        if False
        else None
    )  # cookies登录，调整成True使用cookies登录，反之使用密码登录
    test_year = 2022  # 查询学年
    test_term = 2  # 查询学期（1-上|2-下）

    # 初始化
    lgn = Client(lgn_cookies if lgn_cookies is not None else {}, base_url=base_url)
    # 判断是否需要使用cookies登录
    if lgn_cookies is None:
        # 登录
        pre_login = lgn.login(sid, password)
        # 判断登录结果
        if pre_login["code"] == 1001:
            # 需要验证码
            pre_dict = pre_login["data"]
            with open(os.path.abspath("temp.json"), mode="w", encoding="utf-8") as f:
                f.write(json.dumps(pre_dict))
            with open(os.path.abspath("kaptcha.png"), "wb") as pic:
                pic.write(base64.b64decode(pre_dict["kaptcha_pic"]))
            kaptcha = input("输入验证码：")
            result = lgn.login_with_kaptcha(
                pre_dict["sid"],
                pre_dict["csrf_token"],
                pre_dict["cookies"],
                pre_dict["password"],
                pre_dict["modulus"],
                pre_dict["exponent"],
                kaptcha,
            )
            if result["code"] != 1000:
                pprint(result)
                sys.exit()
            lgn_cookies = lgn.cookies
        elif pre_login["code"] == 1000:
            # 不需要验证码，直接登录
            lgn_cookies = lgn.cookies
        else:
            # 出错
            pprint(pre_login)
            sys.exit()

    # 下面是各个函数调用，想调用哪个，取消注释即可
    """ 获取个人信息 """
    result = lgn.get_info()

    """ 获取成绩单PDF """
    # result = lgn.get_academia_pdf()
    # if result["code"] == 1000:
    #     with open(os.path.abspath("grade.pdf"), "wb") as pdf:
    #         pdf.write(result["data"])
    #         result = "已保存到本地"

    """ 获取学业情况 """
    # result = lgn.get_academia()

    """ 获取GPA """
    # result = lgn.get_gpa()

    """ 获取课程表 """
    # result = lgn.get_schedule(test_year, test_term)

    """ 获取成绩 """
    # result = lgn.get_grade(test_year, test_term)

    # 输出结果
    pprint(result)
