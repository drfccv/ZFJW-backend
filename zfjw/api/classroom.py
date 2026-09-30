"""校区 / 教学楼 / 空教室。"""
import json
import time
import traceback
from typing import Optional
from pyquery import PyQuery as pq
from requests import exceptions


class ClassroomMixin:
    def get_campus_list(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """
        获取校区列表
        返回学校的所有校区及其ID
        """
        try:
            # 从配置获取空教室查询首页URL
            try:
                url = self.get_school_url('classroom_index', None, school_name, base_url)
                # 确保URL包含layout=default
                if 'layout=default' not in url:
                    separator = '&' if '?' in url else '?'
                    url = f"{url}{separator}layout=default"
            except ValueError:
                # 使用默认URL
                fallback_base = base_url or self.base_url or ""
                url = f"{fallback_base.rstrip('/')}/cdjy/cdjy_cxKxcdlb.html?gnmkdm=N2155&layout=default"
            
            print(f"获取校区列表 - URL: {url}")
            
            req = self.sess.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                verify=False,
            )
            
            print(f"获取校区列表 - 响应状态码: {req.status_code}")
            
            if req.status_code != 200:
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req.status_code}"}
            
            # 检查是否登录
            doc = pq(req.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析校区列表
            campus_list = []
            campus_select = doc("select[name='xqh_id'] option")
            
            for option in campus_select.items():
                campus_id = option.attr("value")
                campus_name_text = option.text()
                # PyQuery的text()返回str，但类型检查可能不正确，显式处理
                campus_name = str(campus_name_text).strip() if campus_name_text else ""
                if campus_id and campus_name:
                    campus_list.append({
                        "campus_id": campus_id,
                        "campus_name": campus_name,
                        "is_default": option.attr("selected") == "selected"
                    })
            
            if not campus_list:
                return {"code": 1005, "msg": "未找到校区信息"}
            
            print(f"获取校区列表 - 找到 {len(campus_list)} 个校区")
            
            return {
                "code": 1000,
                "msg": "获取校区列表成功",
                "data": {
                    "count": len(campus_list),
                    "campuses": campus_list
                }
            }
            
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取校区列表超时"}
        except exceptions.RequestException:
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取校区列表时未记录的错误：" + str(e)}

    def get_building_list(self, year: int, term: int, campus_id: str = "1", school_name: Optional[str] = None, base_url: Optional[str] = None):
        """
        获取教学楼列表和节次信息
        参数:
            year: 学年，如2025
            term: 学期，1-第一学期，2-第二学期
            campus_id: 校区ID（可通过get_campus_list获取）
            school_name: 学校名称（可选）
            base_url: 基础URL（可选）
        
        返回：
        - buildings: 教学楼列表
        - time_slots: 节次时间表
        """
        try:
            # 从配置获取楼号查询URL
            try:
                url = self.get_school_url('building_list', None, school_name, base_url)
            except ValueError:
                # 使用默认URL
                fallback_base = base_url or self.base_url or ""
                url = f"{fallback_base.rstrip('/')}/cdjy/cdjy_cxXqjc.html"
            
            # 转换学期参数
            term_param = term ** 2 * 3 if term != 0 else ""
            
            # 构建请求参数
            params = {
                "xqh_id": str(campus_id),
                "xnm": str(year),
                "xqm": str(term_param),
                "gnmkdm": "N2155"
            }
            
            print(f"获取教学楼列表 - URL: {url}")
            print(f"获取教学楼列表 - 参数: {params}")
            
            req = self.sess.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
                verify=False,
            )
            
            print(f"获取教学楼列表 - 响应状态码: {req.status_code}")
            print(f"获取教学楼列表 - 响应内容前500字符: {req.text[:500]}")
            
            if req.status_code != 200:
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req.status_code}"}
            
            # 检查是否登录
            doc = pq(req.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                response = req.json()
                print("获取教学楼列表 - JSON解析成功")
            except json.JSONDecodeError as json_err:
                print(f"获取教学楼列表 - JSON解析失败: {json_err}")
                print(f"获取教学楼列表 - 原始响应: {req.text}")
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
            # 解析楼号列表
            buildings = []
            lh_list = response.get("lhList", [])
            for building in lh_list:
                buildings.append({
                    "building_code": building.get("JXLDM"),
                    "building_name": building.get("JXLMC"),
                    "campus_id": building.get("XQH_ID", campus_id)
                })
            
            # 解析节次信息
            time_slots = []
            jc_list = response.get("jcList", [])
            for slot in jc_list:
                time_slots.append({
                    "period": slot.get("RSDMC"),  # 时段名称：上午/下午/晚上
                    "time": slot.get("SJD"),  # 时间段
                    "slot_number": slot.get("JCMC"),  # 节次编号
                    "total_slots": slot.get("RSDZJS")  # 该时段总节数
                })
            
            if not buildings:
                return {"code": 1005, "msg": "未找到教学楼信息"}
            
            print(f"获取教学楼列表 - 找到 {len(buildings)} 个教学楼，{len(time_slots)} 个节次")
            
            return {
                "code": 1000,
                "msg": "获取教学楼列表成功",
                "data": {
                    "year": year,
                    "term": term,
                    "campus_id": campus_id,
                    "building_count": len(buildings),
                    "buildings": buildings,
                    "time_slots": time_slots
                }
            }
            
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取教学楼列表超时"}
        except exceptions.RequestException:
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取教学楼列表时未记录的错误：" + str(e)}

    def get_empty_classroom(self, year: int, term: int, weeks, day_of_weeks, time_slots, campus_id: str = "1", school_name: Optional[str] = None, base_url: Optional[str] = None, building: Optional[str] = None):
        """
        查询空闲教室
        参数:
            year: 学年，如2025
            term: 学期，1-第一学期，2-第二学期
            weeks: 周次，可以是单个数字(如1)、列表(如[1,2])或逗号分隔字符串(如"1,2")
            day_of_weeks: 星期几，可以是单个数字(如1)、列表(如[1,3])或逗号分隔字符串(如"1,3")，1=周一，7=周日
            time_slots: 节次，可以是单个数字(如1)、列表(如[2,3])或范围字符串(如"2-3")，表示第几节课
            campus_id: 校区ID，默认"1"（可通过get_campus_list获取）
            school_name: 学校名称（可选）
            base_url: 基础URL（可选）
            building: 教学楼（可选）
        
        编码说明：
        - 周次(zcd)使用位掩码: 第1周=1, 第2周=2, 第1和2周=3, 第3周=4
        - 节次(jcd)使用位掩码: 第1节=1, 第2节=2, 第2和3节=6, 第4节=8
        """
        try:
            # 从配置获取空教室查询URL
            try:
                url = self.get_school_url('classroom', None, school_name, base_url)
                if 'doType=query' not in url:
                    separator = '&' if '?' in url else '?'
                    url = f"{url}{separator}doType=query"
            except ValueError:
                # 使用默认URL
                fallback_base = base_url or self.base_url or ""
                url = f"{fallback_base.rstrip('/')}/cdjy/cdjy_cxKxcdlb.html?doType=query&gnmkdm=N2155"
            
            # 转换学期参数
            term_param = term ** 2 * 3 if term != 0 else ""
            
            # 处理周次参数 - 转换为位掩码
            if isinstance(weeks, str):
                week_list = [int(w.strip()) for w in weeks.split(',') if w.strip()]
            elif isinstance(weeks, list):
                week_list = weeks
            else:
                week_list = [weeks]
            # 计算周次位掩码: 第n周对应2^(n-1)
            zcd = sum(2 ** (w - 1) for w in week_list)
            
            # 处理星期参数 - 可以是多个星期，用逗号分隔
            if isinstance(day_of_weeks, str):
                day_list = [d.strip() for d in day_of_weeks.split(',') if d.strip()]
                xqj = ','.join(day_list)
            elif isinstance(day_of_weeks, list):
                xqj = ','.join(str(d) for d in day_of_weeks)
            else:
                xqj = str(day_of_weeks)
            
            # 处理节次参数 - 转换为位掩码
            if isinstance(time_slots, str):
                # 支持范围格式 "2-3" 或逗号分隔 "2,3"
                if '-' in time_slots:
                    start, end = time_slots.split('-')
                    slot_list = list(range(int(start), int(end) + 1))
                else:
                    slot_list = [int(s.strip()) for s in time_slots.split(',') if s.strip()]
            elif isinstance(time_slots, list):
                slot_list = time_slots
            else:
                slot_list = [time_slots]
            # 计算节次位掩码: 第n节对应2^(n-1)
            jcd = sum(2 ** (s - 1) for s in slot_list)
            
            # 构建请求数据
            data = {
                "xqh_id": str(campus_id),  # 校区ID（动态获取）
                "xnm": str(year),  # 学年
                "xqm": str(term_param),  # 学期
                "cdlb_id": "",  # 场地类别ID
                "cdejlb_id": "",  # 场地二级类别ID
                "qszws": "",  # 起始座位数
                "jszws": "",  # 结束座位数
                "cdmc": "",  # 场地名称
                "lh": "",  # 楼号
                "jyfs": "0",  # 借用方式
                "cdjylx": "",  # 场地借用类型
                "sfbhkc": "",  # 是否包含课程
                "zcd": str(zcd),  # 周次(位掩码)
                "xqj": xqj,  # 星期几(可以是多个，逗号分隔)
                "jcd": str(jcd),  # 节次(位掩码)
                "_search": "false",
                "nd": int(time.time() * 1000),
                "queryModel.showCount": "5000",  # 每页最多条数
                "queryModel.currentPage": "1",
                "queryModel.sortName": "cdbh ",  # 注意有空格
                "queryModel.sortOrder": "asc",
                "time": "1",
            }
            
            # 如果指定了教学楼，添加到请求参数
            if building:
                data["cdmc"] = building
            
            print(f"空教室查询 - URL: {url}")
            print(f"空教室查询 - 数据: {data}")
            print(f"空教室查询 - 周次位掩码: weeks={week_list} -> zcd={zcd}")
            req = self.sess.post(
                url,
                headers=self.headers,
                data=data,
                timeout=self.timeout,
                verify=False,
            )
            
            if req.status_code != 200:
                return {"code": 2333, "msg": f"教务系统服务异常，状态码: {req.status_code}"}
            
            # 检查是否登录
            doc = pq(req.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            
            # 解析JSON响应
            try:
                response = req.json()
            except json.JSONDecodeError as json_err:
                return {"code": 2333, "msg": f"响应格式错误: {str(json_err)}"}
            
            
            items = response.get("items")
            if not items:
                return {"code": 1005, "msg": "该时间段无空闲教室"}
            
            # 构建返回结果
            classrooms = []
            for item in items:
                classroom_info = {
                    "code": item.get("cdbh"),  # 场地编号
                    "name": item.get("cdmc"),  # 场地名称（如"文友楼101"）
                    "campus": item.get("xqmc"),  # 校区
                    "type": item.get("cdlbmc"),  # 场地类别
                    "capacity": int(item.get("zws", 0) or 0),  # 座位数
                    "exam_capacity": int(item.get("kszws1", 0) or 0),  # 考试座位数
                    "building_code": item.get("lh"),  # 楼号
                    "floor": item.get("lch"),  # 楼层号
                    "borrow_type": item.get("cdjylx"),  # 场地借用类型
                    "remark": item.get("bz"),  # 场地备注信息
                    "manager": item.get("cdgly"),  # 场地管理员
                    "department": item.get("sydxmc"),  # 使用部门
                    "class_name": item.get("sybj"),  # 使用班级
                    "sub_type": item.get("cdejlbmc"),  # 场地二级类别名称
                    "area": item.get("jzmj"),  # 建筑面积
                    "custody_dept": item.get("tgbm"),  # 托管部门
                }
                classrooms.append(classroom_info)
            
            result = {
                "year": year,
                "term": term,
                "weeks": week_list,
                "day_of_weeks": xqj,
                "time_slots": slot_list,
                "building": building or "全部",
                "count": len(classrooms),
                "classrooms": classrooms,
            }
            
            return {"code": 1000, "msg": "获取空教室信息成功", "data": result}
            
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取空教室信息超时"}
        except exceptions.RequestException:
            traceback.print_exc()
            return {"code": 2333, "msg": "服务请求失败，可能是系统维护或接口异常"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取空教室信息时未记录的错误：" + str(e)}
