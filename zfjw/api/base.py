"""会话、请求头与 URL 构建。"""
from typing import Optional
from urllib.parse import urljoin
import requests

from zfjw.school_config import school_config_manager
from zfjw.settings import RASPISANIE


class BaseMixin:
    raspisanie = []
    ignore_type = []

    def __init__(self, cookies=None, **kwargs):
        # 基础配置
        self.school_name = kwargs.get("school_name", "九江学院")  # 默认使用九江学院
        self.base_url = kwargs.get("base_url")
        self.raspisanie = kwargs.get("raspisanie", RASPISANIE)
        self.ignore_type = kwargs.get("ignore_type", [])
        self.detail_category_type = kwargs.get("detail_category_type", [])
        self.timeout = kwargs.get("timeout", 30)  # 设置默认超时时间
        # 同步到实际实例类，供 helpers 中的 classmethod 通过 cls 读取
        type(self).raspisanie = self.raspisanie
        type(self).ignore_type = self.ignore_type

        # 从学校配置获取base_url
        if school_config_manager and not self.base_url:
            school_config = school_config_manager.get_school_config(self.school_name)
            if school_config:
                self.base_url = school_config.get("base_url", "")
                print(f"从配置中获取 {self.school_name} 的 base_url: {self.base_url}")

        # 加载学校URL配置
        self.school_urls = None
        if school_config_manager:
            school_config = school_config_manager.get_school_config(self.school_name)
            if school_config:
                self.school_urls = school_config.get('urls', {})

        # 根据配置构造URL
        if self.base_url:
            if not self.base_url.endswith('/'):
                self.base_url = self.base_url + '/'
            def url_from_config(key, default_path):
                if self.school_urls and key in self.school_urls:
                    # 验证base_url有效性
                    if self.base_url:
                        return urljoin(self.base_url, self.school_urls[key])
                if self.base_url:
                    return urljoin(self.base_url, default_path)
                return None
            self.key_url = url_from_config('key', 'xtgl/login_getPublicKey.html')
            self.login_url = url_from_config('login', 'xtgl/login_slogin.html')
            self.kaptcha_url = url_from_config('kaptcha', 'kaptcha')
        else:
            # base_url未配置时的处理
            self.key_url = None
            self.login_url = None
            self.kaptcha_url = None
            print("警告: 未设置 base_url，某些功能可能无法正常工作")
          # 配置HTTP请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.login_url
        }
        
        # 创建会话
        self.sess = requests.Session()
        self.sess.headers.update(self.headers)
        self.cookies = cookies or {}

        # 初始化会话cookies
        for key, value in self.cookies.items():
            self.sess.cookies.set(key, value)

    def get_school_url(self, url_type: str, fallback_path: Optional[str] = None, school_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
        """
        获取学校功能URL，支持多种方式：
        1. 优先使用传入的 school_name 从配置中获取
        2. 其次使用传入的 base_url 拼接
        3. 最后使用实例的配置
        """
        # 如果传入了学校名称，从配置中获取
        if school_name and school_config_manager:
            config_url = school_config_manager.get_school_url(school_name, url_type)
            if config_url:
                return config_url
        
        # 优先使用传入的base_url参数
        target_base_url = base_url or self.base_url
        if not target_base_url:
            raise ValueError("base_url 未设置，无法构建 URL")
            
        if not target_base_url.endswith('/'):
            target_base_url += '/'
            
        # 使用当前实例的学校配置
        if not school_name and self.school_urls and url_type in self.school_urls:
            constructed_url = urljoin(target_base_url, self.school_urls[url_type])
            print(f"从实例配置构建URL: {constructed_url}")
            return constructed_url
            
        # 使用默认路径
        if fallback_path:
            constructed_url = urljoin(target_base_url, fallback_path)
            print(f"使用fallback构建URL: {constructed_url}")
            return constructed_url
            
        raise ValueError(f"无法找到功能 {url_type} 的 URL 配置")

    def get_school_base_url(self, school_name: Optional[str] = None, base_url: Optional[str] = None) -> str:
        """获取学校的 base_url"""
        if school_name and school_config_manager:
            config_base_url = school_config_manager.get_base_url(school_name)
            if config_base_url:
                return config_base_url
                
        if base_url:
            return base_url
            
        if self.base_url:
            return self.base_url

        raise ValueError("base_url 未设置")
