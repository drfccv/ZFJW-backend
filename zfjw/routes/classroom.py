"""校区 / 教学楼 / 空教室 接口。"""
from flask import Blueprint
from flask import jsonify
from flask import request

from zfjw.routes.common import build_client
from zfjw.routes.common import get_base_url_from_params
from zfjw.routes.common import handle_errors


bp = Blueprint("classroom", __name__)


@bp.route('/campus_list', methods=['POST'])
@handle_errors
def get_campus_list():
    """
    获取校区列表接口
    请求参数：
    - cookies: 登录凭证（必填）
    - school_name: 学校名称（可选，但需与base_url二选一）
    - base_url: 学校教务系统地址（可选，但需与school_name二选一）
    
    返回示例：
    {
        "code": 1000,
        "msg": "获取校区列表成功",
        "data": {
            "count": 5,
            "campuses": [
                {
                    "campus_id": "1",
                    "campus_name": "主校区",
                    "is_default": true
                },
                {
                    "campus_id": "2",
                    "campus_name": "浔东校区",
                    "is_default": false
                }
            ]
        }
    }
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"获取校区列表 - 学校: {school_name}, 使用URL: {base_url}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_campus_list(school_name=school_name, base_url=base_url)
    return jsonify(result)

@bp.route('/building_list', methods=['POST'])
@handle_errors
def get_building_list():
    """
    获取教学楼列表和节次信息接口
    请求参数：
    - cookies: 登录凭证（必填）
    - year: 学年，如2025（必填）
    - term: 学期，1-第一学期，2-第二学期（必填）
    - campus_id: 校区ID，默认"1"，可通过/api/campus_list获取（可选）
    - school_name: 学校名称（可选，但需与base_url二选一）
    - base_url: 学校教务系统地址（可选，但需与school_name二选一）
    
    返回示例：
    {
        "code": 1000,
        "msg": "获取教学楼列表成功",
        "data": {
            "year": 2025,
            "term": 2,
            "campus_id": "1",
            "building_count": 8,
            "buildings": [
                {
                    "building_code": "32",
                    "building_name": "教学楼（一）",
                    "campus_id": "1"
                }
            ],
            "time_slots": [
                {
                    "period": "上午",
                    "time": "08:00-08:45",
                    "slot_number": 1,
                    "total_slots": 4
                }
            ]
        }
    }
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year')
    term = data.get('term')
    campus_id = data.get('campus_id', '1')  # 默认为主校区
    school_name = data.get('school_name')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not all([cookies, year, term]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, year, term 和 (base_url 或 school_name)"})
    
    print(f"获取教学楼列表 - 学校: {school_name}, 使用URL: {base_url}, 学年: {year}, 学期: {term}, 校区: {campus_id}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_building_list(year, term, campus_id=campus_id, school_name=school_name, base_url=base_url)
    return jsonify(result)

@bp.route('/classroom', methods=['POST'])
@handle_errors
def get_classroom():
    """
    空教室查询接口
    请求参数：
    - cookies: 登录凭证（必填）
    - year: 学年，如2025（必填）
    - term: 学期，1-第一学期，2-第二学期（必填）
    - weeks: 周次，可以是单个数字(如3)、列表(如[1,2])或逗号分隔字符串(如"1,2")（必填）
    - day_of_weeks: 星期几，可以是单个数字(如1)、列表(如[1,3])或逗号分隔字符串(如"1,3")，1=周一，7=周日（必填）
    - time_slots: 节次，可以是单个数字(如1)、列表(如[2,3])或范围字符串(如"2-3")（必填）
    - campus_id: 校区ID，默认"1"，可通过/api/campus_list获取（可选）
    - building: 教学楼名称（可选）
    - school_name: 学校名称（可选，但需与base_url二选一）
    - base_url: 学校教务系统地址（可选，但需与school_name二选一）
    
    示例：
    {
        "cookies": "...",
        "school_name": "九江学院",
        "year": 2025,
        "term": 2,
        "weeks": 3,
        "day_of_weeks": "1,3",
        "time_slots": "2-3",
        "campus_id": "1"
    }
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year')
    term = data.get('term')
    weeks = data.get('weeks')
    day_of_weeks = data.get('day_of_weeks')
    time_slots = data.get('time_slots')
    campus_id = data.get('campus_id', '1')  # 默认为主校区
    building = data.get('building')  # 可选参数
    school_name = data.get('school_name')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    # 校验必填参数
    if not all([cookies, year, term, weeks is not None, day_of_weeks is not None, time_slots is not None]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, year, term, weeks, day_of_weeks, time_slots 和 (base_url 或 school_name)"})
    
    print(f"空教室查询 - 学校: {school_name}, 使用URL: {base_url}, 学年: {year}, 学期: {term}, 周次: {weeks}, 星期: {day_of_weeks}, 节次: {time_slots}, 校区: {campus_id}, 教学楼: {building or '全部'}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_empty_classroom(year, term, weeks, day_of_weeks, time_slots, campus_id=campus_id, school_name=school_name, base_url=base_url, building=building)
    return jsonify(result)
