"""个人信息 / 成绩 / 考试 / 课表 接口。"""
from flask import Blueprint
from flask import jsonify
from flask import request

import json
import traceback
from urllib.parse import urlparse
import requests
from zfjw.routes.common import build_client
from zfjw.routes.common import get_base_url_from_params
from zfjw.routes.common import handle_errors
from zfjw.school_config import school_config_manager


bp = Blueprint("academic", __name__)


@bp.route('/info', methods=['POST'])
@handle_errors
def get_info():
    """获取个人信息与学籍"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"个人信息查询 - 使用URL: {base_url}")
    
    # 获取school_name参数
    school_name = data.get('school_name')
    
    stu = build_client(cookies, base_url)
    result = stu.get_info(school_name=school_name, base_url=base_url)
    return jsonify(result)

@bp.route('/grade', methods=['POST'])
@handle_errors
def get_grade():
    """查询成绩

    不传 year / term 时由服务端按当前学年学期推断。
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year')
    term = data.get('term')
      # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"成绩查询 - 使用URL: {base_url}")
    
    # 获取school_name参数
    school_name = data.get('school_name')
    
    stu = build_client(cookies, base_url)
    result = stu.get_grade(year, term, school_name=school_name, base_url=base_url)
    return jsonify(result)

@bp.route('/exam', methods=['POST'])
@handle_errors
def get_exam():
    """查询考试安排"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year')
    term = data.get('term')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    if not all([cookies, year, term]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, year, term 和 (base_url 或 school_name)"})
    
    print(f"考试信息查询 - 使用URL: {base_url}")
    
    # 获取school_name参数
    school_name = data.get('school_name')
    
    stu = build_client(cookies, base_url)
    result = stu.get_exam_schedule(year, term, school_name=school_name, base_url=base_url)
    return jsonify(result)

@bp.route('/grade_detail', methods=['POST'])
@handle_errors
def get_grade_detail():
    """
    详细成绩查询接口，用于查询期末成绩（含平时分）
    请求参数:
        cookies: 登录后的cookies
        year: 学年，如2024
        term: 学期，1-第一学期，2-第二学期，0-整个学年
        school_name: 学校名称（可选，用于自动获取base_url）
        base_url: 学校教务系统地址（可选，如果提供school_name则自动获取）
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year')
    term = data.get('term', 0)  # 默认为整个学年
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not all([cookies, year]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, year 和 (base_url 或 school_name)"})
    
    print(f"详细成绩查询 - 使用URL: {base_url}")
    
    # 获取school_name参数
    school_name = data.get('school_name')
    
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_grade_detail(year, term, school_name=school_name, base_url=base_url)
    return jsonify(result)

def _fetch_schedule_direct(data, cookies, year, term, base_url):
    """课表直连实现（旧版兼容路径）。

    旧版 app.py 在路由内内联了这套请求逻辑，其返回结构为扁平化的 courses[]，
    与 Client.get_schedule 的展示结构不同；为不改变对外响应结构，这里保留为
    独立实现。直连失败时回退到 Client.get_schedule。

    返回 jsonify 包装后的响应，调用方可直接 return。
    """
    # 获取school_name参数用于URL配置
    school_name = data.get('school_name')
    
    # 调用课表查询接口
    try:
        sess = requests.Session()
        sess.verify = False
        
        # 设置cookies
        for k, v in cookies.items():
            sess.cookies.set(k, v)
        
        # 第一步：使用配置的课表首页URL
        if school_name:
            school_config = school_config_manager.get_school_config(school_name)
            if school_config and school_config.get('urls', {}).get('schedule_index'):
                index_url = f"{base_url}/{school_config['urls']['schedule_index']}"
            else:
                index_url = f"{base_url}/jwglxt/kbcx/xskbcx_cxXskbcxIndex.html?gnmkdm=N2151&layout=default"
        else:
            # 默认URL（兼容性）
            index_url = f"{base_url}/jwglxt/kbcx/xskbcx_cxXskbcxIndex.html?gnmkdm=N2151&layout=default"
        
        print(f"课表首页URL: {index_url}")
        
        # 动态设置Host头
        parsed_base = urlparse(base_url)
        host_name = parsed_base.netloc
        
        index_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Host': host_name,
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0'
        }
        
        index_response = sess.get(index_url, headers=index_headers, timeout=30)
        
        if index_response.status_code != 200:
            return jsonify({"code": 2333, "msg": f"无法访问课表首页，状态码: {index_response.status_code}"})
        
        if "用户登录" in index_response.text:
            return jsonify({"code": 1006, "msg": "访问首页时被重定向到登录页面，cookies可能已过期"})
          # 第二步：使用配置的课表查询URL
        if school_name:
            school_config = school_config_manager.get_school_config(school_name)
            if school_config and school_config.get('urls', {}).get('schedule'):
                schedule_url = f"{base_url}/{school_config['urls']['schedule']}"
            else:
                schedule_url = f"{base_url}/jwglxt/kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N2151"
        else:
            # 默认URL（兼容性）
            schedule_url = f"{base_url}/jwglxt/kbcx/xskbcx_cxXsgrkb.html?gnmkdm=N2151"
        
        print(f"课表查询URL: {schedule_url}")
        
        # 计算Origin
        parsed_base = urlparse(base_url)
        origin_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        # 根据用户提供的负载格式：gnmkdm=N2151&xnm=2025&xqm=3&kzlx=ck&xsdm=&kclbdm=
        # 计算 xqm 参数：term ** 2 * 3 
        term_param = term ** 2 * 3
        data = f"gnmkdm=N2151&xnm={year}&xqm={term_param}&kzlx=ck&xsdm=&kclbdm="
          # 完全匹配浏览器的请求头
        schedule_headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Host': host_name,
            'Origin': origin_url,
            'Pragma': 'no-cache',
            'Referer': index_url,
            'Sec-CH-UA': '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        schedule_response = sess.post(
            schedule_url,
            headers=schedule_headers,
            data=data,
            timeout=30
        )
        
        if schedule_response.status_code != 200:
            return jsonify({"code": 2333, "msg": f"课表查询失败，状态码: {schedule_response.status_code}"})
        
        if "用户登录" in schedule_response.text:
            return jsonify({"code": 1006, "msg": "课表查询时被重定向到登录页面，cookies可能已过期"})
        
        # 解析JSON响应
        try:
            schedule_data = schedule_response.json()
            
            if not schedule_data.get("kbList"):
                return jsonify({"code": 1005, "msg": "获取课表内容为空"})
            
            # 简化的课表数据格式化
            result = {
                "sid": schedule_data["xsxx"].get("XH") if "xsxx" in schedule_data else None,
                "name": schedule_data["xsxx"].get("XM") if "xsxx" in schedule_data else None,
                "year": year,
                "term": term,
                "count": len(schedule_data["kbList"]),
                "courses": [
                    {
                        "course_id": i.get("kch_id"),
                        "title": i.get("kcmc"),
                        "teacher": i.get("xm"),
                        "class_name": i.get("jxbmc"),
                        "credit": float(i.get("xf", 0)) if i.get("xf") else 0,
                        "weekday": int(i.get("xqj", 0)) if i.get("xqj") else 0,
                        "time": i.get("jc"),
                        "weeks": i.get("zcd"),
                        "campus": i.get("xqmc"),
                        "place": i.get("cdmc"),
                        "total_hours": int(i.get("zxs", 0)) if i.get("zxs") else 0,
                    }
                    for i in schedule_data["kbList"]
                ]
            }
            
            print(f"课表查询成功，返回 {len(result['courses'])} 门课程")
            return jsonify({"code": 1000, "msg": "获取课表成功", "data": result})
            
        except json.JSONDecodeError:
            print(f"课表响应不是JSON格式: {schedule_response.text[:500]}")
            return jsonify({"code": 2333, "msg": f"课表响应格式错误，内容: {schedule_response.text[:200]}"})
    
    except Exception as e:
        print(f"课表查询服务异常: {str(e)}")
        traceback.print_exc()
        # 直连失败时的异常处理：回退到 Client.get_schedule
        try:
            stu = build_client(cookies, base_url)
            
            # 获取school_name参数
            school_name = data.get('school_name') if isinstance(data, dict) else None
            
            result = stu.get_schedule(year, term, school_name=school_name, base_url=base_url)
            return jsonify(result)
        except Exception as fallback_e:
            print(f"原版本也失败: {str(fallback_e)}")
            return jsonify({"code": 999, "msg": f"课表查询完全失败: {str(e)}, 回退失败: {str(fallback_e)}"})

@bp.route('/schedule', methods=['POST'])
@handle_errors
def get_schedule():
    """获取课表（优先直连实现，失败时回退到 Client.get_schedule）。

    响应结构与旧版完全一致，未做任何字段调整。
    """
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year')
    term = data.get('term')

    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response

    if not all([cookies, year, term]):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, year, term 和 (base_url 或 school_name)"})
    print(f"课表查询 - 使用URL: {base_url}")

    return _fetch_schedule_direct(data, cookies, year, term, base_url)


@bp.route('/notifications', methods=['POST'])
@handle_errors
def get_notifications():
    """查询通知消息（停补换课等）"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})    
    print(f"通知消息查询 - 使用URL: {base_url}")
    
    # 获取school_name参数
    school_name = data.get('school_name')
    
    try:
        stu = build_client(cookies, base_url)
        result = stu.get_notifications(school_name=school_name, base_url=base_url)
        return jsonify(result)
    except Exception as e:
        print(f"通知消息查询出错: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 999, "msg": f"通知消息查询失败: {str(e)}"})

@bp.route('/academia', methods=['POST'])
@handle_errors
def get_academia():
    """查询学业生涯情况（当前不可用）"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"学业生涯查询 - 使用URL: {base_url}")
    
    # 注意：get_academia 方法已被注释掉，返回不支持
    return jsonify({"code": 400, "msg": "get_academia 方法当前不可用。该功能在开发中。"})

@bp.route('/schedule_pdf', methods=['POST'])
@handle_errors
def schedule_pdf():
    """导出课程表PDF"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    year = data.get('year', 2025)
    term = data.get('term', 1)
    name = data.get('name', '导出')  # 学生姓名
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"课程表PDF导出 - 学校: {school_name}, 使用URL: {base_url}, 年份: {year}, 学期: {term}, 姓名: {name}")
    
    # 注意：get_schedule_pdf 方法已被注释掉，返回不支持
    return jsonify({"code": 400, "msg": "get_schedule_pdf 方法当前不可用。该功能在开发中。"})
