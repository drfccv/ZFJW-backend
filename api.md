# ZFJW Backend API 接口文档

🎯 **高校教务系统后端API**，基于Flask构建，支持多所高校教务系统数据获取。

## 📋 项目概览

- **服务地址**: `http://localhost:5000` (开发环境)
- **支持学校**: 九江学院、南昌职业大学
- **数据格式**: JSON (Content-Type: application/json)
- **响应格式**: 统一JSON结构

## 🔧 接口分类

### HTTP方法规范
- **学校信息接口**: `GET` 方法
- **业务数据接口**: `POST` 方法

---

## 📚 接口列表

### 1. 系统健康检查

#### GET `/api/health`
检查服务是否正常运行

**响应示例**:
```json
{
  "status": "ok",
  "message": "ZFJW Backend API is running"
}
```

---

### 2. 学校信息接口

#### GET `/api/schools`
获取所有支持的学校列表

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取学校列表成功",
  "data": {
    "count": 2,
    "schools": [
      {
        "school_name": "九江学院",
        "school_code": "jju",
        "description": "九江学院教务系统",
        "requires_captcha": true
      },
      {
        "school_name": "南昌职业大学", 
        "school_code": "nvu",
        "description": "南昌职业大学教务系统",
        "requires_captcha": false
      }
    ]
  }
}
```

#### GET `/api/school/<school_name>`
获取指定学校的配置信息

**路径参数**:
- `school_name`: 学校名称 (如: 九江学院)

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取学校配置成功",
  "data": {
    "base_url": "https://zhjw1.jju.edu.cn",
    "school_name": "九江学院",
    "school_code": "jju",
    "requires_captcha": true,
    "description": "九江学院教务系统"
  }
}
```

#### GET `/api/school/<school_name>/captcha-required`
检查指定学校是否需要验证码

**路径参数**:
- `school_name`: 学校名称

**响应示例**:
```json
{
  "code": 1000,
  "msg": "检查验证码需求成功",
  "data": {
    "school_name": "九江学院",
    "requires_captcha": true
  }
}
```

---

### 3. 用户认证接口

#### POST `/api/login`
用户登录接口

**请求参数**:
```json
{
  "sid": "学号",
  "password": "密码", 
  "school_name": "九江学院"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "登录成功",
  "data": {
    "cookies": "登录凭证",
    "user_info": "用户基本信息"
  }
}
```

#### POST `/api/login_with_kaptcha`
带验证码的登录接口

**请求参数**:
```json
{
  "sid": "学号",
  "password": "密码",
  "captcha": "验证码",
  "school_name": "九江学院"
}
```

#### POST `/api/get_captcha`
获取验证码图片

**请求参数**:
```json
{
  "school_name": "九江学院"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取验证码成功",
  "data": {
    "captcha_image": "base64编码的图片数据",
    "cookies": "会话凭证"
  }
}
```

---

### 4. 学生信息接口

#### POST `/api/info`
获取学生个人信息

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取个人信息成功",
  "data": {
    "student_id": "学号",
    "name": "姓名",
    "college": "学院",
    "major": "专业",
    "class": "班级"
  }
}
```

---

### 5. 成绩查询接口

#### POST `/api/grade`
查询学生成绩

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "year": "2024",
  "term": "1"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取成绩成功",
  "data": {
    "courses": [
      {
        "course_name": "课程名称",
        "course_code": "课程代码", 
        "credit": "学分",
        "score": "成绩",
        "grade_point": "绩点"
      }
    ]
  }
}
```

---

### 6. 考试安排接口

#### POST `/api/exam`
查询考试安排

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取考试安排成功",
  "data": {
    "exams": [
      {
        "course_name": "课程名称",
        "exam_time": "考试时间",
        "exam_location": "考试地点",
        "seat_number": "座位号"
      }
    ]
  }
}
```

---

### 7. 课程表接口

#### POST `/api/schedule`
获取课程表

**请求参数**:
```json
{
  "cookies": "登录凭证", 
  "school_name": "九江学院",
  "year": "2024",
  "term": "1"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取课程表成功",
  "data": {
    "schedule": [
      {
        "course_name": "课程名称",
        "teacher": "教师",
        "classroom": "教室",
        "week": "周次",
        "day": "星期",
        "time": "节次"
      }
    ]
  }
}
```

#### POST `/api/schedule_pdf`
获取课程表PDF

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "year": "2024", 
  "term": "1"
}
```

---

### 8. 通知公告接口

#### POST `/api/notifications`
获取通知公告

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取通知成功",
  "data": {
    "notifications": [
      {
        "title": "通知标题",
        "content": "通知内容", 
        "publish_time": "发布时间",
        "department": "发布部门"
      }
    ]
  }
}
```

---

### 9. 学业情况接口

#### POST `/api/academia`
获取学业完成情况

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取学业情况成功",
  "data": {
    "total_credits": "总学分",
    "completed_credits": "已完成学分",
    "remaining_credits": "剩余学分",
    "gpa": "平均绩点"
  }
}
```

---

### 10. 选课相关接口

#### POST `/api/selected_courses`
查询已选课程

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

#### POST `/api/block_courses` 
获取课程分块信息

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

#### POST `/api/course_classes`
获取课程班级列表

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "course_id": "课程ID"
}
```

#### POST `/api/select_course`
选择课程

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "course_id": "课程ID",
  "class_id": "班级ID"
}
```

#### POST `/api/drop_course`
退选课程

**请求参数**:
```json
{
  "cookies": "登录凭证", 
  "school_name": "九江学院",
  "course_id": "课程ID"
}
```

---

### 11. 教学评价接口

#### 说明
本系统支持正方教务系统的教学质量评价功能，所有评价相关URL均通过 schools_config.json 配置，无硬编码。接口调用流程如下：
1. 通过 `/api/evaluate_menu` 获取可评价课程列表（POST请求，返回JSON格式）。
2. 通过 `/api/evaluate_detail` 获取某门课程的评价详情（需要jxb_id参数）。
3. 通过 `/api/evaluate_save` 保存评价内容（可多次保存，未提交前可修改）。
4. 通过 `/api/evaluate_submit` 提交评价（不可撤回）。

#### POST `/api/evaluate_menu`
获取可评价课程列表

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```
**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取评价菜单成功",
  "data": {
    "courses": [
      {
        "course_id": "D9AE3A910643B14BE0530BECC1DA0713",
        "course_name": "大学生创新创业基础",
        "teacher": "黄细洋",
        "class_name": "(2024-2025-2)-6171110011-61",
        "classroom": "文友楼404",
        "time": "星期一第1-2节{1-8周}",
        "college": "管理学院",
        "status": "未评",
        "jxb_id": "273C08F0CB93EE59E0630BECC1DACDF8",
        "evaluate_url": "https://zhjw1.jju.edu.cn/jwglxt/xspjgl/xspj_cxXspjIndex.html?..."
      }
    ],
    "total": 8,
    "current_page": 1,
    "total_pages": 1
  }
}
```

#### POST `/api/evaluate_detail`
获取某门课程的评价详情

**说明**:
- 该接口会返回课程的评价详情，包括评价项目列表
- 根据 `is_evaluated` 字段判断课程是否已评价：
  - `is_evaluated: false` - 未评价状态，`evaluation_items` 中包含输入框信息
  - `is_evaluated: true` - 已评价状态，`evaluation_items` 中显示已评价的分数
- 已评价的课程无法再次评价

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "jxb_id": "273C08F0CB93EE59E0630BECC1DACDF8",
  "school_name": "九江学院"
}
```
**响应示例**:

**未评价状态**:
```json
{
  "code": 1000,
  "msg": "获取评价详情成功",
  "data": {
    "action": "/jwglxt/xspjgl/xspj_cxXspjDisplay.html",
    "course_name": "大学生创新创业基础",
    "teacher_name": "黄细洋",
    "jxb_id": "273C08F0CB93EE59E0630BECC1DACDF8",
    "kch_id": "D9AE3A910643B14BE0530BECC1DA0713",
    "is_evaluated": false,
    "evaluation_items": [
      {
        "content": "教学态度端正，教学准备充分，授课精神饱满、严谨认真。",
        "input_name": "input_name_1",
        "min_score": 30,
        "max_score": 100,
        "placeholder": "打分范围:30-100",
        "current_value": "",
        "has_input": true,
        "pjzbxm_id": "385E7A0A98CAE8EFE0630AECC1DA9F1E"
      }
    ],
    "comment_name": "py",
    "comment_max_length": 500
  }
}
```

**已评价状态**:
```json
{
  "code": 1000,
  "msg": "获取评价详情成功",
  "data": {
    "action": "/jwglxt/xspjgl/xspj_cxXspjDisplay.html",
    "course_name": "大学生创新创业基础",
    "teacher_name": "黄细洋",
    "jxb_id": "273C08F0CB93EE59E0630BECC1DACDF8",
    "kch_id": "D9AE3A910643B14BE0530BECC1DA0713",
    "is_evaluated": true,
    "evaluation_items": [
      {
        "content": "教学态度端正，教学准备充分，授课精神饱满、严谨认真。",
        "score": "98",
        "has_input": false,
        "pjzbxm_id": "385E7A0A98CAE8EFE0630AECC1DA9F1E"
      }
    ],
    "comment_name": "py",
    "comment_max_length": 500
  }
}
```

#### POST `/api/evaluate_save`
保存评价内容

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "action_url": "/jwglxt/xspjgl/xspj_cxXspjDisplay.html",
  "jxb_id": "273C08F0CB93EE59E0630BECC1DACDF8",
  "kch_id": "D9AE3A910643B14BE0530BECC1DA0713",
  "evaluation_data": {
    "items": [
      {
        "input_name": "input_name_1",
        "score": 85
      }
    ]
  },
  "comment": "老师讲课很认真，内容充实"
}
```
**响应示例**:
```json
{
  "code": 1000,
  "msg": "保存成功"
}
```

#### POST `/api/evaluate_submit`
提交评价

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "jxb_id": "273C08F0CB93EE59E0630BECC1DACDF8",
  "kch_id": "D9AE3A910643B14BE0530BECC1DA0713",
  "evaluation_data": {
    "items": [
      { "input_name": "input_name_1", "score": 85 },
      { "input_name": "input_name_2", "score": 90 }
    ]
  },
  "comment": "老师讲课很认真，内容充实"
}
```
> ⚠️ `action_url` 由后端自动查找，无需前端传递。前端只需传分数、评语等内容，后端会自动组装所有必填参数并严格按官方格式提交。

**响应示例**:
```json
{
  "code": 1000,
  "msg": "提交成功"
}
```

---

## 📝 通用响应格式

### 成功响应
```json
{
  "code": 1000,
  "msg": "操作成功",
  "data": {}
}
```

### 错误响应
```json
{
  "code": 400,
  "msg": "参数错误"
}
```

### 状态码说明
- `1000`: 操作成功
- `400`: 参数错误
- `401`: 认证失败
- `404`: 资源不存在
- `999`: 服务器内部错误

---

## 🚀 快速开始

1. **启动服务**
   ```bash
   python app.py
   ```

2. **健康检查**
   ```bash
   curl http://localhost:5000/api/health
   ```

3. **获取学校列表**
   ```bash
   curl http://localhost:5000/api/schools
   ```

4. **用户登录**
   ```bash
   curl -X POST http://localhost:5000/api/login \
     -H "Content-Type: application/json" \
     -d '{"sid":"学号","password":"密码","school_name":"九江学院"}'
   ```

---

## ⚠️ 注意事项

1. **验证码处理**: 部分学校需要验证码，请先调用验证码检查接口
2. **会话管理**: 登录后获得的cookies需要在后续请求中携带
3. **学校配置**: 不同学校的参数可能有差异，请参考学校配置接口
4. **错误处理**: 请根据返回的状态码进行相应的错误处理
5. **请求频率**: 避免过于频繁的请求，以免被教务系统限制

---

## 🔧 开发说明

- **框架**: Flask + Python
- **跨域**: 已配置CORS支持
- **SSL**: 已禁用SSL警告处理
- **配置**: 支持多学校配置管理
- **日志**: 包含详细的错误日志输出
