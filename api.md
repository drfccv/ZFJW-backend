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

### 6. 详细成绩查询接口

#### POST `/api/grade_detail`
查询学生详细成绩（含平时分、期末分等成绩细节）

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "year": "2024",
  "term": "1"
}
```

**参数说明**:
- `cookies`: 登录后获取的认证信息（必填）
- `school_name`: 学校名称，支持"九江学院"、"南昌职业大学"（可选，与base_url二选一）
- `base_url`: 学校教务系统地址（可选，与school_name二选一）
- `year`: 学年，如2024（必填）
- `term`: 学期，1-第一学期，2-第二学期，0-整个学年（可选，默认为0）

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取详细成绩成功",
  "data": {
    "items": [
      {
        "kcmc": "课程名称",
        "kch_id": "课程代码",
        "xf": "学分",
        "xmcj": "项目成绩",
        "xmblmc": "项目类别名称（如：总评、平时、期末等）",
        "kkbmmc": "开课部门名称",
        "jxbmc": "教学班名称"
      }
    ],
    "总条数": 10,
    "查询结果": "成功"
  }
}
```

**特别说明**:
- 本接口返回原始响应数据，包含平时成绩、期末成绩、总评成绩等详细信息
- 同一门课程可能有多条记录，分别对应不同的成绩项目（平时、期末、总评等）
- 具体字段内容根据学校教务系统的实际响应而定

---

### 7. 考试安排接口

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
