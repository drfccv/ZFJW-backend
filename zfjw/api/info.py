"""个人信息与学籍。"""
import json
import time
import traceback
from typing import Optional
from urllib.parse import urljoin
from pyquery import PyQuery as pq
from requests import exceptions


class InfoMixin:
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
            req_notification = self.sess.post(
                url,
                headers=notification_headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            if req_notification.status_code != 200:
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req_notification.status_code}"}
            
            doc = pq(req_notification.text)
            if doc("h5").text() == "用户登录" or "错误" in doc("title").text():
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                notifications = req_notification.json()
            except json.JSONDecodeError as json_err:
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
            notification_items = notifications.get("items")
            if notification_items is None:
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
