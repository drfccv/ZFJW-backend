"""课表。"""
import json
import traceback
from typing import Optional
from pyquery import PyQuery as pq
from requests import exceptions


class ScheduleMixin:
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
