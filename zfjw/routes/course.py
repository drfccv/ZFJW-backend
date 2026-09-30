"""选课 / 退课 接口。"""
from flask import Blueprint
from flask import jsonify
from flask import request

from zfjw.routes.common import build_client
from zfjw.routes.common import get_base_url_from_params
from zfjw.routes.common import handle_errors


bp = Blueprint("course", __name__)


@bp.route('/selected_courses', methods=['POST'])
@handle_errors
def selected_courses():
    """获取已选课程列表"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year', 2024)
    term = data.get('term', 1)
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"已选课程查询 - 学校: {school_name}, 使用URL: {base_url}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_selected_courses(year, term, school_name, base_url)
    return jsonify(result)

@bp.route('/block_courses', methods=['POST'])
@handle_errors
def block_courses():
    """获取板块课程列表"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year', 2025)  # 默认查询年份为2025
    term = data.get('term', 1)
    # 支持两种参数名：block 和 block_id
    block = data.get('block') or data.get('block_id', 1)
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"板块课程查询 - 学校: {school_name}, 使用URL: {base_url}, 年份: {year}, 学期: {term}, 板块: {block}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_block_courses(year, term, block, school_name, base_url)
    return jsonify(result)

@bp.route('/course_classes', methods=['POST'])
@handle_errors
def course_classes():
    """获取指定课程的教学班列表"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year', 2025)
    term = data.get('term', 1)
    course_id = data.get('course_id')
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not all([cookies, course_id]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, course_id 和 (base_url 或 school_name)"})
    
    print(f"教学班查询 - 学校: {school_name}, 使用URL: {base_url}, 年份: {year}, 学期: {term}, 课程ID: {course_id}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_course_classes(year, term, course_id, school_name, base_url)
    return jsonify(result)

@bp.route('/select_course', methods=['POST'])
@handle_errors
def select_course():
    """选课接口"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    sid = data.get('sid')
    course_id = data.get('course_id')
    do_id = data.get('do_id')
    kklxdm = data.get('kklxdm', '1')
    year = data.get('year', 2024)
    term = data.get('term', 1)
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not all([cookies, sid, course_id, do_id]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, sid, course_id, do_id 和 (base_url 或 school_name)"})
    
    print(f"选课操作 - 学校: {school_name}, 使用URL: {base_url}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.select_course(sid, course_id, do_id, kklxdm, year, term, school_name, base_url)
    return jsonify(result)

@bp.route('/drop_course', methods=['POST'])
@handle_errors
def drop_course():
    """退课接口"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    do_id = data.get('do_id')
    course_id = data.get('course_id')
    year = data.get('year', 2025)
    term = data.get('term', 1)
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not all([cookies, do_id, course_id]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, do_id, course_id 和 (base_url 或 school_name)"})
    
    print(f"退课操作 - 学校: {school_name}, 使用URL: {base_url}, 年份: {year}, 学期: {term}, 课程ID: {course_id}")
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.cancel_course(do_id, course_id, year, term, school_name, base_url)
    return jsonify(result)
