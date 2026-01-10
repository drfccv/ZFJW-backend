from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import base64
import traceback
import requests
import json
import urllib3
from urllib.parse import urlparse

# 导入核心 API
from zfn_api import Client
from school_config import school_config_manager

app = Flask(__name__)
CORS(app)

# 配置参数
RASPISANIE = []
IGNORE_TYPE = []
DETAIL_CATEGORY_TYPE = []
TIMEOUT = 30

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# 错误处理装饰器
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"接口 {func.__name__} 发生错误: {str(e)}")
            traceback.print_exc()
            return jsonify({"code": 999, "msg": f"服务器内部错误: {str(e)}"})
    wrapper.__name__ = func.__name__
    return wrapper

# 统一的参数校验和base_url获取函数
def get_base_url_from_params(data):
    """
    从请求参数中获取base_url，支持通过school_name自动查找
    参数:
        data: 请求的JSON数据
    返回:
        tuple: (base_url, error_response)
        如果成功，error_response为None
        如果失败，base_url为None，error_response为错误响应对象
    """
    base_url = data.get('base_url')
    school_name = data.get('school_name')
    
    # 校验参数：base_url 或 school_name 至少一个
    if not base_url and not school_name:
        return None, jsonify({"code": 400, "msg": "缺少 base_url 或 school_name 参数"})
    
    # 通过学校名称获取base_url
    if not base_url and school_name:
        school_config = school_config_manager.get_school_config(school_name)
        if school_config:
            base_url = school_config.get('base_url')
            print(f"通过学校名称 '{school_name}' 获取到 base_url: {base_url}")
        else:
            return None, jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})
    
    # 最终校验 base_url
    if not base_url:
        return None, jsonify({"code": 400, "msg": "未能获取到 base_url，请检查 school_name 是否正确或补充 base_url 参数"})
    
    return base_url, None

# 登录接口（自动识别验证码）
@app.route('/api/login', methods=['POST'])
@handle_errors
def login():
    data = request.json
    print(f"收到登录请求: {data}")
    
    sid = data.get('sid')
    password = data.get('password')
    base_url = data.get('base_url')
    school_name = data.get('school_name', '九江学院')  # 新增学校名称参数
    
    # 校验参数：sid、password 必须有，base_url 或 school_name 至少一个
    if not sid or not password or (not base_url and not school_name):
        return jsonify({"code": 400, "msg": "参数不完整，需要 sid, password 和 (base_url 或 school_name)"})

    # 通过学校名称获取base_url
    if not base_url and school_name:
        school_config = school_config_manager.get_school_config(school_name)
        if school_config:
            base_url = school_config.get('base_url')
            print(f"通过学校名称 '{school_name}' 获取到 base_url: {base_url}")
        else:
            return jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})

    # 再次校验 base_url
    if not base_url:
        return jsonify({"code": 400, "msg": "未能获取到 base_url，请检查 school_name 是否正确或补充 base_url 参数"})
    
    # 检查学校是否需要验证码
    requires_captcha = school_config_manager.requires_captcha(school_name)
    if requires_captcha:
        print(f"学校 '{school_name}' 需要验证码，直接返回验证码获取提示")
        # 获取验证码进行登录验证
        try:
            stu = Client(cookies={}, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
            lgn = stu.login(sid, password)
            return jsonify(lgn)
        except Exception as e:
            print(f"验证码登录过程中发生异常: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "code": 999,
                "msg": f"登录过程发生异常: {str(e)}"
            })
      # 创建Client实例
    try:
        stu = Client(cookies={}, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
        
        # 执行登录操作
        lgn = stu.login(sid, password)
        print(f"登录结果: {lgn}")
        
        return jsonify(lgn)
        
    except Exception as e:
        print(f"登录过程中发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 999,
            "msg": f"登录过程发生异常: {str(e)}"
        })

# 登录验证码提交
@app.route('/api/login_with_kaptcha', methods=['POST'])
@handle_errors
def login_with_kaptcha():
    data = request.json
    print(f"收到验证码登录请求: {data}")
    
    base_url = data.get('base_url')
    school_name = data.get('school_name')
    # 校验参数：base_url 或 school_name 至少一个
    if not base_url and not school_name:
        return jsonify({"code": 400, "msg": "缺少 base_url 或 school_name 参数"})
    if not base_url and school_name:
        school_config = school_config_manager.get_school_config(school_name)
        if school_config:
            base_url = school_config.get('base_url')
            print(f"通过学校名称 '{school_name}' 获取到 base_url: {base_url}")
        else:
            return jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})
    if not base_url:
        return jsonify({"code": 400, "msg": "未能获取到 base_url，请检查 school_name 是否正确或补充 base_url 参数"})
    
    try:
        stu = Client(cookies={}, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
        
        # 准备验证码登录参数，排除base_url
        login_params = {k: v for k, v in data.items() if k != 'base_url'}
        
        ret = stu.login_with_kaptcha(**login_params)
        
        print(f"验证码登录结果: {ret}")
        return jsonify(ret)
        
    except Exception as e:
        print(f"验证码登录过程中发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 999,
            "msg": f"验证码登录过程发生异常: {str(e)}"
        })

# 个人信息
@app.route('/api/info', methods=['POST'])
@handle_errors
def get_info():
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_info(school_name=school_name, base_url=base_url)
    return jsonify(result)

# 成绩查询
@app.route('/api/grade', methods=['POST'])
@handle_errors
def get_grade():
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_grade(year, term, school_name=school_name, base_url=base_url)
    return jsonify(result)

# 考试信息
@app.route('/api/exam', methods=['POST'])
@handle_errors
def get_exam():
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_exam_schedule(year, term, school_name=school_name, base_url=base_url)
    return jsonify(result)

# 详细成绩查询（含平时分）
@app.route('/api/grade_detail', methods=['POST'])
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_grade_detail(year, term, school_name=school_name, base_url=base_url)
    return jsonify(result)

# 课表
@app.route('/api/schedule', methods=['POST'])
@handle_errors
def get_schedule():
    data = request.json
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
        traceback.print_exc()        # 当前查询方法失败时的异常处理
        try:
            stu = Client(cookies=cookies, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
            
            # 获取school_name参数
            school_name = data.get('school_name') if isinstance(data, dict) else None
            
            result = stu.get_schedule(year, term, school_name=school_name, base_url=base_url)
            return jsonify(result)
        except Exception as fallback_e:
            print(f"原版本也失败: {str(fallback_e)}")
            return jsonify({"code": 999, "msg": f"课表查询完全失败: {str(e)}, 回退失败: {str(fallback_e)}"})

# 通知消息
@app.route('/api/notifications', methods=['POST'])
@handle_errors
def get_notifications():
    data = request.json
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
        stu = Client(cookies=cookies, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
        result = stu.get_notifications(school_name=school_name, base_url=base_url)
        return jsonify(result)
    except Exception as e:
        print(f"通知消息查询出错: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 999, "msg": f"通知消息查询失败: {str(e)}"})

# 学业生涯
@app.route('/api/academia', methods=['POST'])
@handle_errors
def get_academia():
    data = request.json
    cookies = data.get('cookies')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"学业生涯查询 - 使用URL: {base_url}")
    
    try:
        stu = Client(cookies=cookies, base_url=base_url, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
        result = stu.get_academia()
        return jsonify(result)
    except Exception as e:
        print(f"学业生涯查询出错: {str(e)}")
        traceback.print_exc()
        return jsonify({"code": 999, "msg": f"学业生涯查询失败: {str(e)}"})

# 获取验证码接口
@app.route('/api/get_captcha', methods=['POST'])
@handle_errors
def get_captcha():
    data = request.json
    print(f"收到获取验证码请求: {data}")
    
    base_url = data.get('base_url')
    school_name = data.get('school_name')
    # 校验参数：base_url 或 school_name 至少一个
    if not base_url and not school_name:
        return jsonify({"code": 400, "msg": "缺少 base_url 或 school_name 参数"})
    if not base_url and school_name:
        school_config = school_config_manager.get_school_config(school_name)
        if school_config:
            base_url = school_config.get('base_url')
            print(f"通过学校名称 '{school_name}' 获取到 base_url: {base_url}")
        else:
            return jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})
    if not base_url:
        return jsonify({"code": 400, "msg": "未能获取到 base_url，请检查 school_name 是否正确或补充 base_url 参数"})
    
    try:
        stu = Client(cookies={}, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
        
        # 使用Client配置的正确URL路径
        if not stu.login_url or not stu.kaptcha_url:
            return jsonify({"code": 2333, "msg": "学校配置不完整，无法获取登录或验证码URL"})
        
        # 访问登录页面
        resp = stu.sess.get(stu.login_url, timeout=stu.timeout, verify=False)
        
        if resp.status_code != 200:
            return jsonify({"code": 2333, "msg": f"无法访问登录页面，状态码: {resp.status_code}"})
        
        # 解析页面获取CSRF token
        from pyquery import PyQuery as pq
        doc = pq(resp.text)
        csrf_token = doc("#csrftoken").attr("value")
        
        if not csrf_token:
            return jsonify({"code": 2333, "msg": "无法获取CSRF token"})
        
        # 获取公钥
        if not stu.key_url:
            return jsonify({"code": 2333, "msg": "学校配置不完整，无法获取公钥URL"})
            
        req_pubkey = stu.sess.get(stu.key_url, timeout=stu.timeout, verify=False)
        
        if req_pubkey.status_code != 200:
            return jsonify({"code": 2333, "msg": f"公钥获取失败，状态码: {req_pubkey.status_code}"})
        
        try:
            pubkey_data = req_pubkey.json()
        except Exception as e:
            return jsonify({"code": 2333, "msg": f"公钥解析失败: {str(e)}"})
        
        modulus = pubkey_data.get("modulus")
        exponent = pubkey_data.get("exponent")
        
        if not modulus or not exponent:
            return jsonify({"code": 2333, "msg": "公钥数据不完整"})
        
        # 获取验证码
        req_kaptcha = stu.sess.get(stu.kaptcha_url, timeout=stu.timeout, verify=False)
        
        if req_kaptcha.status_code != 200:
            return jsonify({"code": 2333, "msg": f"验证码获取失败，状态码: {req_kaptcha.status_code}"})
        
        kaptcha_pic = base64.b64encode(req_kaptcha.content).decode()
        
        result = {
            "code": 1001,
            "msg": "获取验证码成功",
            "data": {
                "kaptcha": kaptcha_pic,
                "cookies": dict(stu.sess.cookies),
                "csrf_token": csrf_token,
                "modulus": modulus,
                "exponent": exponent
            }
        }
        
        print(f"获取验证码结果: 验证码大小 {len(req_kaptcha.content)} bytes")
        return jsonify(result)
        
    except Exception as e:
        print(f"获取验证码过程中发生异常: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "code": 999,
            "msg": f"获取验证码过程发生异常: {str(e)}"
        })

# 选课相关接口
@app.route('/api/selected_courses', methods=['POST'])
@handle_errors
def selected_courses():
    """获取已选课程列表"""
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_selected_courses(year, term, school_name, base_url)
    return jsonify(result)

@app.route('/api/block_courses', methods=['POST'])
@handle_errors
def block_courses():
    """获取板块课程列表"""
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_block_courses(year, term, block, school_name, base_url)
    return jsonify(result)

@app.route('/api/course_classes', methods=['POST'])
@handle_errors
def course_classes():
    """获取指定课程的教学班列表"""
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_course_classes(year, term, course_id, school_name, base_url)
    return jsonify(result)

@app.route('/api/select_course', methods=['POST'])
@handle_errors
def select_course():
    """选课接口"""
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.select_course(sid, course_id, do_id, kklxdm, year, term, school_name, base_url)
    return jsonify(result)

@app.route('/api/drop_course', methods=['POST'])
@handle_errors
def drop_course():
    """退课接口"""
    data = request.json
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.cancel_course(do_id, course_id, year, term, school_name, base_url)
    return jsonify(result)

@app.route('/api/schedule_pdf', methods=['POST'])
@handle_errors
def schedule_pdf():
    """导出课程表PDF"""
    data = request.json
    cookies = data.get('cookies')
    year = data.get('year', 2025)
    term = data.get('term', 1)
    name = data.get('name', '导出')  # 学生姓名
    student_id = data.get('student_id', '')  # 学生学号
    school_name = data.get('school_name')  # 获取学校名称
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"课程表PDF导出 - 学校: {school_name}, 使用URL: {base_url}, 年份: {year}, 学期: {term}, 姓名: {name}")
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_schedule_pdf(year, term, name, student_id, school_name, base_url)
      # 如果返回PDF数据，设置正确的响应头
    if result.get('code') == 1000 and 'data' in result:
        return Response(
            result['data'],
            mimetype='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename=schedule_{year}_{term}.pdf",
                "Content-Type": "application/pdf"
            }
        )
    else:
        return jsonify(result)

# 健康检查接口
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "ZFJW Backend API is running"})

# 学校相关接口
@app.route('/api/schools', methods=['GET'])
@handle_errors
def get_schools():
    """获取所有支持的学校列表"""
    try:
        schools = school_config_manager.get_schools_list()
        return jsonify({
            "code": 1000,
            "msg": "获取学校列表成功",
            "data": {
                "count": len(schools),
                "schools": schools
            }
        })
    except Exception as e:
        return jsonify({
            "code": 999,
            "msg": f"获取学校列表失败: {str(e)}"
        })

@app.route('/api/school/<school_name>', methods=['GET'])
@handle_errors
def get_school_config(school_name):
    """获取指定学校的配置信息"""
    try:
        config = school_config_manager.get_school_config(school_name)
        if not config:
            return jsonify({
                "code": 404,
                "msg": f"未找到学校 '{school_name}' 的配置"
            })
        
        return jsonify({
            "code": 1000,
            "msg": "获取学校配置成功",
            "data": config
        })
    except Exception as e:
        return jsonify({
            "code": 999,
            "msg": f"获取学校配置失败: {str(e)}"
        })

@app.route('/api/school/<school_name>/captcha-required', methods=['GET'])
@handle_errors
def check_captcha_required(school_name):
    """检查指定学校是否需要验证码"""
    try:
        requires_captcha = school_config_manager.requires_captcha(school_name)
        return jsonify({
            "code": 1000,
            "msg": "检查验证码需求成功",
            "data": {
                "school_name": school_name,
                "requires_captcha": requires_captcha
            }
        })
    except Exception as e:
        return jsonify({
            "code": 999,
            "msg": f"检查验证码需求失败: {str(e)}"
        })

# 教学评价相关接口
@app.route('/api/evaluate_menu', methods=['POST'])
@handle_errors
def evaluate_menu():
    data = request.json
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_evaluate_menu(school_name=school_name, base_url=base_url)
    return jsonify(result)

@app.route('/api/evaluate_detail', methods=['POST'])
@handle_errors
def evaluate_detail():
    data = request.json
    cookies = data.get('cookies')
    jxb_id = data.get('jxb_id')
    school_name = data.get('school_name')
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    if not cookies or not jxb_id:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, jxb_id 和 (base_url 或 school_name)"})
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_evaluate_detail(jxb_id, school_name=school_name, base_url=base_url)
    return jsonify(result)

@app.route('/api/evaluate_save', methods=['POST'])
@handle_errors
def evaluate_save():
    data = request.json
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    jxb_id = data.get('jxb_id')
    kch_id = data.get('kch_id')
    evaluation_data = data.get('evaluation_data')
    comment = data.get('comment', '')
    comment_name = data.get('comment_name', 'py')

    # 校验参数（action_url 不再要求前端传）
    if not (cookies and school_name and jxb_id and kch_id and evaluation_data):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, school_name, jxb_id, kch_id, evaluation_data"})

    # 后端自动查找 action_url（保存接口用 evaluate_save 配置）
    school_config = school_config_manager.get_school_config(school_name)
    if not school_config:
        return jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})
    base_url = school_config.get('base_url')
    evaluate_save_path = school_config.get('urls', {}).get('evaluate_save')
    if not (base_url and evaluate_save_path):
        return jsonify({"code": 400, "msg": "学校配置缺少 base_url 或 evaluate_save 路径"})
    action_url = urljoin(base_url, evaluate_save_path)

    # 自动组装表单参数
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)

    # 兼容前端只传分数、评语，后端自动补全所有必填参数
    # 先获取评价详情，拿到所有input_name、pjzbxm_id等
    detail_result = stu.get_evaluate_detail(jxb_id, school_name=school_name, base_url=base_url)
    if detail_result.get('code') != 1000:
        return jsonify(detail_result)
    detail_data = detail_result['data']
    # 组装items，保证input_name和分数一一对应
    items = []
    frontend_items = {item['input_name']: item['score'] for item in evaluation_data.get('items', []) if 'input_name' in item}
    for item in detail_data['evaluation_items']:
        if item.get('has_input'):
            input_name = item.get('input_name')
            score = frontend_items.get(input_name)
            if score is not None:
                items.append({"input_name": input_name, "score": score})
    final_evaluation_data = {"items": items}
    final_comment = comment
    # 执行保存操作
    result = stu.save_evaluate(action_url, jxb_id, kch_id, final_evaluation_data, final_comment)
    return jsonify(result)

@app.route('/api/evaluate_submit', methods=['POST'])
@handle_errors
def evaluate_submit():
    data = request.json
    print(f"收到教学评价提交请求: {data}")
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    jxb_id = data.get('jxb_id')
    kch_id = data.get('kch_id')
    evaluation_data = data.get('evaluation_data')
    comment = data.get('comment', '')
    comment_name = data.get('comment_name', 'py')

    # 校验参数（action_url 不再要求前端传）
    if not (cookies and school_name and jxb_id and kch_id and evaluation_data):
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, school_name, jxb_id, kch_id, evaluation_data"})

    # 后端自动查找 action_url
    school_config = school_config_manager.get_school_config(school_name)
    if not school_config:
        return jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})
    base_url = school_config.get('base_url')
    evaluate_submit_path = school_config.get('urls', {}).get('evaluate_submit')
    if not (base_url and evaluate_submit_path):
        return jsonify({"code": 400, "msg": "学校配置缺少 base_url 或 evaluate_submit 路径"})
    action_url = urljoin(base_url, evaluate_submit_path)

    # 自动组装表单参数
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)

    # 兼容前端只传分数、评语，后端自动补全所有必填参数
    # 先获取评价详情，拿到所有input_name、pjzbxm_id等
    detail_result = stu.get_evaluate_detail(jxb_id, school_name=school_name, base_url=base_url)
    if detail_result.get('code') != 1000:
        return jsonify(detail_result)
    detail_data = detail_result['data']
    # 组装items，保证input_name和分数一一对应
    items = []
    # 前端传的分数结构：{"items": [{"input_name":..., "score":...}, ...]}
    frontend_items = {item['input_name']: item['score'] for item in evaluation_data.get('items', []) if 'input_name' in item}
    for item in detail_data['evaluation_items']:
        if item.get('has_input'):
            input_name = item.get('input_name')
            score = frontend_items.get(input_name)
            if score is not None:
                items.append({"input_name": input_name, "score": score})
    # 组装最终evaluation_data
    final_evaluation_data = {"items": items}
    # 评语字段名兼容
    final_comment = comment
    # 执行提交操作
    result = stu.submit_evaluate(action_url, jxb_id, kch_id, final_evaluation_data, final_comment)
    return jsonify(result)

# 获取校区列表接口
@app.route('/api/campus_list', methods=['POST'])
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
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    
    # 使用统一的参数校验获取base_url
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    
    print(f"获取校区列表 - 学校: {school_name}, 使用URL: {base_url}")
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_campus_list(school_name=school_name, base_url=base_url)
    return jsonify(result)

# 获取教学楼列表接口
@app.route('/api/building_list', methods=['POST'])
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_building_list(year, term, campus_id=campus_id, school_name=school_name, base_url=base_url)
    return jsonify(result)

# 空教室查询接口
@app.route('/api/classroom', methods=['POST'])
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
    
    stu = Client(cookies=cookies, base_url=base_url, school_name=school_name, raspisanie=RASPISANIE, ignore_type=IGNORE_TYPE, detail_category_type=DETAIL_CATEGORY_TYPE, timeout=TIMEOUT)
    result = stu.get_empty_classroom(year, term, weeks, day_of_weeks, time_slots, campus_id=campus_id, school_name=school_name, base_url=base_url, building=building)
    return jsonify(result)

if __name__ == '__main__':
    # 检查是否在生产环境
    is_production = os.environ.get('FLASK_ENV') == 'production'
    debug_mode = not is_production
    
    print("启动 ZFJW Backend API 服务...")
    print(f"运行模式: {'生产环境' if is_production else '开发环境'}")
    print("健康检查: http://localhost:5000/api/health")
    
    if is_production:
        print("生产环境建议使用uWSGI启动:")
    
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
