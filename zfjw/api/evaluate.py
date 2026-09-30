"""教学评价。"""
import json
import time
from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup


class EvaluateMixin:
    def get_evaluate_menu(self, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取教学评价菜单（可评价课程列表）"""
        try:
            url = self.get_school_url('evaluate', None, school_name, base_url)
        except ValueError:
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/xspjgl/xspj_cxXspjIndex.html?doType=query&gnmkdm=N401605"
        
        # 构建POST请求数据
        data = {
            "_search": "false",
            "nd": int(time.time() * 1000),
            "queryModel.showCount": "5000",
            "queryModel.currentPage": "1",
            "queryModel.sortName": "kcmc,jzgmc ",
            "queryModel.sortOrder": "asc",
            "time": "0"
        }
        
        resp = self.sess.post(url, headers=self.headers, data=data, timeout=self.timeout, verify=False)
        if resp.status_code != 200:
            return {"code": 2333, "msg": f"获取评价菜单失败，状态码: {resp.status_code}"}
        
        try:
            result = resp.json()
        except json.JSONDecodeError:
            return {"code": 2333, "msg": "响应格式错误，无法解析JSON"}
        
        if not result.get("items"):
            return {"code": 1005, "msg": "暂无需要评价的课程"}
        
        # 解析课程列表
        courses = []
        for item in result["items"]:
            courses.append({
                "course_id": item.get("kch_id"),
                "course_name": item.get("kcmc"),
                "teacher": item.get("jzgmc"),
                "class_name": item.get("jxbmc"),
                "classroom": item.get("jxdd"),
                "time": item.get("sksj"),
                "college": item.get("jgmc"),
                "status": item.get("tjztmc"),  # 评价状态：未评、已评等
                "jxb_id": item.get("jxb_id"),  # 教学班ID，用于后续评价
                "jgh_id": item.get("jgh_id"),  # 教职工ID，用于评价详情
                "xsdm": item.get("xsdm"),  # 学生代码
                "evaluate_url": f"{self.base_url.rstrip('/') if self.base_url else ''}/jwglxt/xspjgl/xspj_cxXspjIndex.html?doType=details&gnmkdm=N401605&layout=default&jxb_id={item.get('jxb_id')}"
            })
        
        return {
            "code": 1000, 
            "msg": "获取评价菜单成功", 
            "data": {
                "courses": courses,
                "total": result.get("totalResult", 0),
                "current_page": result.get("currentPage", 1),
                "total_pages": result.get("totalPage", 1)
            }
        }

    def get_evaluate_detail(self, jxb_id: str, school_name: Optional[str] = None, base_url: Optional[str] = None):
        """获取某门课程的评价详情"""
        try:
            url = self.get_school_url('evaluate_detail', None, school_name, base_url)
        except ValueError:
            fallback_base = base_url or self.base_url or ""
            url = f"{fallback_base.rstrip('/')}/xspjgl/xspj_cxXspjDisplay.html?gnmkdm=N401605"
        
        # 从课程列表中获取课程信息（需要先调用get_evaluate_menu）
        menu_result = self.get_evaluate_menu(school_name, base_url)
        if menu_result.get("code") != 1000:
            return menu_result
        
        # 找到对应的课程信息
        course_info = None
        for course in menu_result["data"]["courses"]:
            if course["jxb_id"] == jxb_id:
                course_info = course
                break
        
        if not course_info:
            return {"code": 2333, "msg": "未找到对应的课程信息"}
        
        print(f"课程信息: {course_info}")
        
        # 构建POST请求数据 - 使用课程列表中的原始数据
        # 从课程列表中获取原始数据
        original_course_data = None
        for item in menu_result["data"]["courses"]:
            if item["jxb_id"] == jxb_id:
                original_course_data = item
                break
        
        if not original_course_data:
            return {"code": 2333, "msg": "未找到原始课程数据"}
        
        # 使用原始数据构建请求参数
        data = {
            "jxb_id": jxb_id,
            "kch_id": course_info["course_id"],
            "xsdm": course_info.get("xsdm", "01"),  # 自动取课程信息里的xsdm
            "jgh_id": original_course_data.get("jgh_id", ""),  # 使用原始数据中的jgh_id
            "tjzt": "-1",
            "pjmbmcb_id": "",
            "sfcjlrjs": "1"
        }
        
        # 如果jgh_id仍然为空，尝试从其他字段获取
        if not data["jgh_id"]:
            # 尝试从课程信息中获取教师ID
            teacher_info = course_info.get("teacher_id", "")
            if teacher_info:
                data["jgh_id"] = teacher_info
        
        print(f"POST请求数据: {data}")
        
        resp = self.sess.post(url, headers=self.headers, data=data, timeout=self.timeout, verify=False)
        if resp.status_code != 200:
            return {"code": 2333, "msg": f"获取评价详情失败，状态码: {resp.status_code}"}
        
        html = resp.text
        print(f"HTML响应长度: {len(html)}")
        print(f"HTML前1000字符: {html[:1000]}")
        print(f"HTML中间部分(6000-8000字符): {html[6000:8000]}")
        print(f"HTML后1000字符: {html[-1000:]}")
        
        # 检查是否被重定向到登录页面
        if '用户登录' in html or 'login' in html.lower():
            return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
        
        # 检查参数错误
        if '课程号ID,教学班ID,教职工ID参数异常' in html:
            return {"code": 2333, "msg": "参数错误：课程号ID,教学班ID,教职工ID参数异常，请检查课程信息"}
        
        if '目前未对你放开教学质量评价' in html:
            return {"code": 1005, "msg": "目前未对你放开教学质量评价"}
        
        soup = BeautifulSoup(html, 'html.parser')
        # 获取panel（评价对象）参数
        panel = soup.find('div', class_='panel-pjdx')
        panel_params = {}
        if panel:
            panel_params['pjmbmcb_id'] = panel.get('data-pjmbmcb_id', '')
            panel_params['pjdxdm'] = panel.get('data-pjdxdm', '')
            panel_params['xspfb_id'] = panel.get('data-xspfb_id', '')
            panel_params['fxzgf'] = panel.get('data-fxzgf', '')
        # 获取表单action
        form = soup.find('form', {'id': 'ajaxForm1'})
        action = str(form.get('action', '')) if form else ''
        if action and not action.startswith('http') and self.base_url:
            action = urljoin(self.base_url, action)
        # 获取课程信息
        course_name = course_info["course_name"]
        teacher_name = course_info["teacher"]
        # 获取评价项目
        evaluation_items = []
        is_evaluated = False  # 标记是否已评价
        tr_elements = soup.find_all('tr', {'class': 'tr-xspj'})
        for i, tr in enumerate(tr_elements):
            # 查找包含指定样式的 td
            content_td = None
            for td in tr.find_all('td'):
                style_attr = td.get('style', '')
                if style_attr and 'width: 400px' in str(style_attr):
                    content_td = td
                    break
            if not content_td:
                continue
            content = content_td.get_text(strip=True).replace('*', '').strip()
            value_td = tr.find_all('td')
            if len(value_td) >= 2:
                value_content = value_td[1].get_text(strip=True)
                input_elem = tr.find('input')
                has_input = input_elem is not None
                if not has_input:
                    is_evaluated = True
                # 解析tr的所有data属性
                pjzbxm_id = tr.get('data-pjzbxm_id', '')
                zsmbmcb_id = tr.get('data-zsmbmcb_id', '')
                pfdjdmb_id = tr.get('data-pfdjdmb_id', '')
                if has_input:
                    input_name = str(input_elem.get('name', ''))
                    if not input_name and pjzbxm_id:
                        input_name = str(pjzbxm_id)
                    min_score = str(input_elem.get('data-zxfz', '30'))
                    max_score = str(input_elem.get('data-zdfz', '100'))
                    placeholder = str(input_elem.get('placeholder', ''))
                    current_value = str(input_elem.get('value', ''))
                    weight = str(tr.get('data-qzz', '0.2'))
                    evaluation_items.append({
                        "content": content,
                        "input_name": input_name,
                        "min_score": int(min_score) if min_score else 30,
                        "max_score": int(max_score) if max_score else 100,
                        "placeholder": placeholder,
                        "current_value": current_value,
                        "weight": float(weight) if weight else 0.2,
                        "pjzbxm_id": pjzbxm_id,
                        "zsmbmcb_id": zsmbmcb_id,
                        "pfdjdmb_id": pfdjdmb_id,
                        "has_input": True
                    })
                else:
                    evaluation_items.append({
                        "content": content,
                        "score": value_content,
                        "pjzbxm_id": pjzbxm_id,
                        "zsmbmcb_id": zsmbmcb_id,
                        "pfdjdmb_id": pfdjdmb_id,
                        "has_input": False
                    })
        # 查找以 _py 结尾的 textarea
        comment_textarea = None
        for textarea in soup.find_all('textarea'):
            textarea_id = textarea.get('id', '')
            if textarea_id and str(textarea_id).endswith('_py'):
                comment_textarea = textarea
                break
        comment_name = str(comment_textarea.get('name', 'py')) if comment_textarea else 'py'
        # 获取评语内容（已评价或未评价）
        comment_value = ""
        py_div = soup.find('div', id='pyDiv')
        if py_div:
            comment_box = py_div.find('div', class_='input-xspj')
            if comment_box:
                comment_value = comment_box.get_text(strip=True)
        # 返回panel参数和每个评价项的所有ID
        return {"code": 1000, "msg": "获取评价详情成功", "data": {
            'action': action,
            'course_name': course_name,
            'teacher_name': teacher_name,
            'jxb_id': jxb_id,
            'kch_id': course_info["course_id"],
            'evaluation_items': evaluation_items,
            'comment_name': comment_name,
            'comment_max_length': 500,
            'is_evaluated': is_evaluated,
            'comment': comment_value,
            'jgh_id': course_info.get('jgh_id', ''),  # 新增，确保后续POST参数不为空
            **panel_params
        }}

    def save_evaluate(self, action_url: str, jxb_id: str, kch_id: str, evaluation_data: dict, comment: str = ""):
        """保存评价内容（严格官方嵌套结构，与提交一致，仅url不同）"""
        # 先获取评价详情，拿到所有嵌套参数
        detail_result = self.get_evaluate_detail(jxb_id)
        if detail_result.get('code') != 1000:
            return detail_result
        detail_data = detail_result['data']
        evaluation_items = detail_data['evaluation_items']
        # 组装分数字典
        frontend_items = {item['input_name']: item['score'] for item in evaluation_data.get('items', []) if 'input_name' in item}
        # 组装嵌套结构
        data = {}
        # 顶层参数
        data['ztpjbl'] = '100'
        data['jszdpjbl'] = '0'
        data['xykzpjbl'] = '0'
        data['jxb_id'] = jxb_id
        data['kch_id'] = kch_id
        # 统一jgh_id取值
        data['jgh_id'] = detail_data.get('jgh_id') or detail_data.get('teacher_id') or ''
        data['xsdm'] = detail_data.get('xsdm', '01')
        data['tjzt'] = '-1'  # 保存时为-1
        # panel参数
        data['modelList[0].pjmbmcb_id'] = detail_data.get('pjmbmcb_id', '')
        data['modelList[0].pjdxdm'] = detail_data.get('pjdxdm', '01')
        data['modelList[0].xspfb_id'] = detail_data.get('xspfb_id', '')
        data['modelList[0].fxzgf'] = detail_data.get('fxzgf', '')
        # 评语为空时自动填充
        if not comment or str(comment).strip() == "":
            comment = "无评语!"
        data['modelList[0].py'] = comment
        # 评价项目
        for idx, item in enumerate(evaluation_items):
            if not item.get('has_input'):
                continue
            score = frontend_items.get(item['input_name'])
            if score is None:
                continue
            prefix = f"modelList[0].xspjList[0].childXspjList[{idx}]"
            data[f"{prefix}.pjf"] = str(score)
            data[f"{prefix}.pjzbxm_id"] = item.get('pjzbxm_id', '')
            data[f"{prefix}.pfdjdmb_id"] = item.get('pfdjdmb_id', '')
            data[f"{prefix}.zsmbmcb_id"] = item.get('zsmbmcb_id', '')
        # 评价项目ID
        data['modelList[0].xspjList[0].pjzbxm_id'] = evaluation_items[0]['pjzbxm_id'] if evaluation_items else ''
        data['modelList[0].pjzt'] = '1'
        # 构造完整headers
        base_url_str = self.base_url if self.base_url else ''
        referer_url = f"{base_url_str.rstrip('/')}/jwglxt/xspjgl/xspj_cxXspjIndex.html?doType=details&gnmkdm=N401605&layout=default&jxb_id={jxb_id}"
        origin_url = base_url_str.rstrip('/')
        headers = self.headers.copy()
        headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': origin_url,
            'Pragma': 'no-cache',
            'Referer': referer_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        print('最终POST数据:', data)
        resp = self.sess.post(action_url, data=data, headers=headers, timeout=self.timeout, verify=False)
        print('正方系统保存响应:', resp.text[:500])
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('code') == 200 or '保存' in result.get('msg', '') or '成功' in result.get('msg', ''):
                    return {"code": 1000, "msg": "保存成功"}
                else:
                    return {"code": 2333, "msg": result.get('msg', '保存失败，请检查评价内容')}
            except Exception:
                html = resp.text
                if '保存成功' in html or '评价已保存' in html:
                    return {"code": 1000, "msg": "保存成功"}
                elif '评价分数不能为空' in html:
                    return {"code": 2333, "msg": "评价分数不能为空"}
                elif '评语不能超过500字' in html:
                    return {"code": 2333, "msg": "评语不能超过500字"}
                else:
                    return {"code": 2333, "msg": "保存失败，请检查评价内容"}
        return {"code": 2333, "msg": "保存失败"}

    def submit_evaluate(self, action_url: str, jxb_id: str, kch_id: str, evaluation_data: dict, comment: str = ""):
        """提交评价（严格官方嵌套结构）"""
        # 先获取评价详情，拿到所有嵌套参数
        detail_result = self.get_evaluate_detail(jxb_id)
        if detail_result.get('code') != 1000:
            return detail_result
        detail_data = detail_result['data']
        evaluation_items = detail_data['evaluation_items']
        # 组装分数字典
        frontend_items = {item['input_name']: item['score'] for item in evaluation_data.get('items', []) if 'input_name' in item}
        # 组装嵌套结构
        data = {}
        # 顶层参数
        data['ztpjbl'] = '100'
        data['jszdpjbl'] = '0'
        data['xykzpjbl'] = '0'
        data['jxb_id'] = jxb_id
        data['kch_id'] = kch_id
        # 统一jgh_id取值
        data['jgh_id'] = detail_data.get('jgh_id') or detail_data.get('teacher_id') or ''
        data['xsdm'] = detail_data.get('xsdm', '01')
        data['tjzt'] = '1'
        # panel参数
        data['modelList[0].pjmbmcb_id'] = detail_data.get('pjmbmcb_id', '')
        data['modelList[0].pjdxdm'] = detail_data.get('pjdxdm', '01')
        data['modelList[0].xspfb_id'] = detail_data.get('xspfb_id', '')
        data['modelList[0].fxzgf'] = detail_data.get('fxzgf', '')
        # 评语为空时自动填充
        if not comment or str(comment).strip() == "":
            comment = "无评语!"
        data['modelList[0].py'] = comment
        # 评价项目
        for idx, item in enumerate(evaluation_items):
            if not item.get('has_input'):
                continue
            score = frontend_items.get(item['input_name'])
            if score is None:
                continue
            prefix = f"modelList[0].xspjList[0].childXspjList[{idx}]"
            data[f"{prefix}.pjf"] = str(score)
            data[f"{prefix}.pjzbxm_id"] = item.get('pjzbxm_id', '')
            data[f"{prefix}.pfdjdmb_id"] = item.get('pfdjdmb_id', '')
            data[f"{prefix}.zsmbmcb_id"] = item.get('zsmbmcb_id', '')
        # 评价项目ID
        data['modelList[0].xspjList[0].pjzbxm_id'] = evaluation_items[0]['pjzbxm_id'] if evaluation_items else ''
        data['modelList[0].pjzt'] = '1'
        # 构造完整headers
        base_url_str = self.base_url if self.base_url else ''
        referer_url = f"{base_url_str.rstrip('/')}/jwglxt/xspjgl/xspj_cxXspjIndex.html?doType=details&gnmkdm=N401605&layout=default&jxb_id={jxb_id}"
        origin_url = base_url_str.rstrip('/')
        headers = self.headers.copy()
        headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'DNT': '1',
            'Origin': origin_url,
            'Pragma': 'no-cache',
            'Referer': referer_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        })
        print('最终POST数据:', data)
        resp = self.sess.post(action_url, data=data, headers=headers, timeout=self.timeout, verify=False)
        print('正方系统响应:', resp.text[:500])
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('code') == 200 or '成功' in result.get('msg', ''):
                    return {"code": 1000, "msg": "提交成功"}
                else:
                    return {"code": 2333, "msg": result.get('msg', '提交失败，请检查评价内容')}
            except Exception:
                html = resp.text
                if '提交成功' in html or '评价已提交' in html:
                    return {"code": 1000, "msg": "提交成功"}
                elif '评价分数不能为空' in html:
                    return {"code": 2333, "msg": "评价分数不能为空"}
                elif '评语不能超过500字' in html:
                    return {"code": 2333, "msg": "评语不能超过500字"}
                else:
                    return {"code": 2333, "msg": "提交失败，请检查评价内容"}
        return {"code": 2333, "msg": "提交失败"}
