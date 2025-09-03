import json
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

class SchoolConfigManager:
    """学校配置管理器"""
    
    def __init__(self, config_file: str = "schools_config.json"):
        self.config_file = config_file
        self.schools_config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载学校配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"配置文件 {self.config_file} 不存在，返回空配置")
                return {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    def save_config(self) -> bool:
        """保存学校配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.schools_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_schools_list(self) -> List[Dict[str, str]]:
        """获取所有学校列表"""
        schools = []
        for school_name, config in self.schools_config.items():
            schools.append({
                "school_name": school_name,
                "school_code": config.get("school_code", ""),
                "base_url": config.get("base_url", ""),
                "requires_captcha": config.get("requires_captcha", True),
                "description": config.get("description", "")
            })
        return schools
    
    def get_school_config(self, school_name: str) -> Optional[Dict]:
        """根据学校名称获取配置"""
        return self.schools_config.get(school_name)
    
    def get_school_config_by_code(self, school_code: str) -> Optional[Dict]:
        """根据学校代码获取配置"""
        for school_name, config in self.schools_config.items():
            if config.get("school_code") == school_code:
                return config
        return None
    
    def add_school(self, school_name: str, config: Dict) -> bool:
        """添加新学校配置"""
        try:
            self.schools_config[school_name] = config
            return self.save_config()
        except Exception as e:
            print(f"添加学校配置失败: {e}")
            return False
    
    def update_school(self, school_name: str, config: Dict) -> bool:
        """设置学校配置"""
        try:
            if school_name in self.schools_config:
                self.schools_config[school_name].update(config)
                return self.save_config()
            return False
        except Exception as e:
            print(f"设置学校配置失败: {e}")
            return False
    
    def delete_school(self, school_name: str) -> bool:
        """删除学校配置"""
        try:
            if school_name in self.schools_config:
                del self.schools_config[school_name]
                return self.save_config()
            return False
        except Exception as e:
            print(f"删除学校配置失败: {e}")
            return False
    
    def get_school_url(self, school_name: str, url_type: str) -> Optional[str]:
        """获取学校特定功能的URL"""
        config = self.get_school_config(school_name)
        if not config:
            return None
        
        base_url = config.get("base_url", "")
        if not base_url.endswith('/'):
            base_url += '/'
        
        url_path = config.get("urls", {}).get(url_type)
        if url_path:
            return urljoin(base_url, url_path)
        return None
    
    def get_school_params(self, school_name: str) -> Dict:
        """获取学校的默认参数"""
        config = self.get_school_config(school_name)
        if not config:
            return {}
        return config.get("parameters", {}).get("default_params", {})
    
    def requires_captcha(self, school_name: str) -> bool:
        """检查学校是否需要验证码"""
        config = self.get_school_config(school_name)
        if not config:
            return True  # 默认需要验证码
        return config.get("requires_captcha", True)
    
    def get_term_mapping(self, school_name: str, term: int) -> str:
        """获取学校的学期参数映射"""
        config = self.get_school_config(school_name)
        if not config:
            return str(term)
        
        term_mapping = config.get("parameters", {}).get("term_mapping", {})
        return term_mapping.get(str(term), str(term))
    
    def calculate_grade_year(self, school_name: str, year: int) -> int:
        """计算年级参数"""
        config = self.get_school_config(school_name)
        if not config:
            return year - 1  # 默认偏移
        
        offset = config.get("parameters", {}).get("grade_year_offset", -1)
        return year + offset
    
    def get_base_url(self, school_name: str) -> str:
        """获取学校的base_url"""
        config = self.get_school_config(school_name)
        if not config:
            return ""
        
        return config.get("base_url", "")

# 全局配置管理器实例
school_config_manager = SchoolConfigManager()
