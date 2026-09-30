"""学校配置 接口。"""
from flask import Blueprint
from flask import jsonify

from zfjw.routes.common import handle_errors
from zfjw.school_config import school_config_manager


bp = Blueprint("school", __name__)


@bp.route('/schools', methods=['GET'])
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

@bp.route('/school/<school_name>', methods=['GET'])
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

@bp.route('/school/<school_name>/captcha-required', methods=['GET'])
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
