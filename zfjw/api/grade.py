"""成绩查询。"""
import json
import time
import traceback
from typing import Optional
from pyquery import PyQuery as pq
from requests import exceptions


class GradeMixin:
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
        # 根据真实请求：第一学期为3，第二学期为12
        if term == 1:
            term_param = "3"  # 第一学期为3
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
            "queryModel.showCount": "5000",  # 每页最多条数
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
            req_grade = self.sess.post(
                url,
                headers=grade_headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            if req_grade.status_code != 200:
                # 非 200 状态码：先检查是否被重定向到了登录页面（session 过期）
                if req_grade.status_code in (901, 302, 401):
                    # 尝试从跳转后页面或响应体判断是否登录过期
                    try:
                        login_doc = pq(req_grade.text)
                        if login_doc("h5").text() == "用户登录":
                            return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
                    except Exception:
                        pass
                    # 如果响应 URL 变成了登录页地址，也判定为过期
                    if "login" in req_grade.url.lower():
                        return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req_grade.status_code}"}
            
            doc = pq(req_grade.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                grade = req_grade.json()
            except json.JSONDecodeError as json_err:
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
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
            
            if req_grade.status_code != 200:
                # 非 200 状态码：先检查是否被重定向到了登录页面（session 过期）
                if req_grade.status_code in (901, 302, 401):
                    try:
                        login_doc = pq(req_grade.text)
                        if login_doc("h5").text() == "用户登录":
                            return {"code": 1013, "msg": "登录过期，请重新登录"}
                    except Exception:
                        pass
                    if "login" in req_grade.url.lower():
                        return {"code": 1013, "msg": "登录过期，请重新登录"}
                return {"code": 2333, "msg": f"教务系统响应异常，状态码: {req_grade.status_code}"}
            
            # 检查是否被重定向到登录页面
            doc = pq(req_grade.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1013, "msg": "登录过期，请重新登录"}
            
            # 解析JSON响应
            try:
                grade_response = req_grade.json()
            except json.JSONDecodeError as json_err:
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
