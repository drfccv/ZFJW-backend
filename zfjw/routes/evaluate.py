"""教学评价 接口。"""
from flask import Blueprint
from flask import jsonify
from flask import request

from urllib.parse import urljoin
from zfjw.routes.common import build_client
from zfjw.routes.common import get_base_url_from_params
from zfjw.routes.common import handle_errors
from zfjw.school_config import school_config_manager


bp = Blueprint("evaluate", __name__)


@bp.route('/evaluate_menu', methods=['POST'])
@handle_errors
def evaluate_menu():
    """获取教学评价列表"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    if not cookies:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies 和 (base_url 或 school_name)"})
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_evaluate_menu(school_name=school_name, base_url=base_url)
    return jsonify(result)

@bp.route('/evaluate_detail', methods=['POST'])
@handle_errors
def evaluate_detail():
    """获取单个教学班的评价详情（含评价项与 input_name）"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    cookies = data.get('cookies')
    jxb_id = data.get('jxb_id')
    school_name = data.get('school_name')
    base_url, error_response = get_base_url_from_params(data)
    if error_response:
        return error_response
    if not cookies or not jxb_id:
        return jsonify({"code": 400, "msg": "参数不完整，需要 cookies, jxb_id 和 (base_url 或 school_name)"})
    stu = build_client(cookies, base_url, school_name)
    result = stu.get_evaluate_detail(jxb_id, school_name=school_name, base_url=base_url)
    return jsonify(result)

def _prepare_evaluation(data, action_key):
    """评价保存/提交的公共前置处理。

    解析学校配置得到 action_url、拉取评价详情，并把前端分数与 input_name
    对齐组装成提交数据。

    返回 (payload, error)：payload 为 dict，error 为可直接返回的响应对象。
    """
    cookies = data.get('cookies')
    school_name = data.get('school_name')
    jxb_id = data.get('jxb_id')
    kch_id = data.get('kch_id')
    evaluation_data = data.get('evaluation_data')
    comment = data.get('comment', '')

    # 校验参数（action_url 不再要求前端传）
    if not (cookies and school_name and jxb_id and kch_id and evaluation_data):
        return None, jsonify({"code": 400, "msg": "参数不完整，需要 cookies, school_name, jxb_id, kch_id, evaluation_data"})

    # 后端自动查找 action_url
    school_config = school_config_manager.get_school_config(school_name)
    if not school_config:
        return None, jsonify({"code": 400, "msg": f"未找到学校 '{school_name}' 的配置"})
    base_url = school_config.get('base_url')
    action_path = school_config.get('urls', {}).get(action_key)
    if not (base_url and action_path):
        return None, jsonify({"code": 400, "msg": f"学校配置缺少 base_url 或 {action_key} 路径"})
    action_url = urljoin(base_url, action_path)

    stu = build_client(cookies, base_url, school_name)

    # 先获取评价详情，拿到所有 input_name，保证与前端分数一一对应
    detail_result = stu.get_evaluate_detail(jxb_id, school_name=school_name, base_url=base_url)
    if detail_result.get('code') != 1000:
        return None, jsonify(detail_result)
    detail_data = detail_result['data']

    frontend_items = {
        item['input_name']: item['score']
        for item in evaluation_data.get('items', [])
        if 'input_name' in item
    }
    items = []
    for item in detail_data['evaluation_items']:
        if item.get('has_input'):
            input_name = item.get('input_name')
            score = frontend_items.get(input_name)
            if score is not None:
                items.append({"input_name": input_name, "score": score})

    return {
        "stu": stu,
        "action_url": action_url,
        "jxb_id": jxb_id,
        "kch_id": kch_id,
        "evaluation_data": {"items": items},
        "comment": comment,
    }, None


@bp.route('/evaluate_save', methods=['POST'])
@handle_errors
def evaluate_save():
    """保存教学评价（暂存，不提交）"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})

    payload, error = _prepare_evaluation(data, 'evaluate_save')
    if error:
        return error

    result = payload["stu"].save_evaluate(
        payload["action_url"], payload["jxb_id"], payload["kch_id"],
        payload["evaluation_data"], payload["comment"])
    return jsonify(result)

@bp.route('/evaluate_submit', methods=['POST'])
@handle_errors
def evaluate_submit():
    """提交教学评价"""
    data = request.json
    if not data:
        return jsonify({"code": 400, "msg": "请求数据为空"})
    print(f"收到教学评价提交请求: {data}")

    payload, error = _prepare_evaluation(data, 'evaluate_submit')
    if error:
        return error

    result = payload["stu"].submit_evaluate(
        payload["action_url"], payload["jxb_id"], payload["kch_id"],
        payload["evaluation_data"], payload["comment"])
    return jsonify(result)
