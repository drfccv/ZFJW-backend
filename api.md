# 📖 ZFJW Backend API 接口文档

🎯 **正方教务系统后端API**，基于Flask构建，支持多所高校教务系统数据获取。

## 📋 项目概览

- **服务地址**: `http://localhost:5000` (开发环境)
- **生产地址**: 根据部署环境配置
- **支持学校**: 九江学院、南昌职业大学（持续扩展中）
- **数据格式**: JSON (Content-Type: application/json)
- **响应格式**: 统一JSON结构
- **认证方式**: Session-based Cookie认证
- **API版本**: v1.0

## 🔧 接口分类

### HTTP方法规范
- **学校信息接口**: `GET` 方法 - 获取静态配置信息
- **业务数据接口**: `POST` 方法 - 需要认证的数据查询
- **系统接口**: `GET` 方法 - 健康检查等系统功能

### 接口分组
- 🏥 **系统接口** - 健康检查、状态监控
- 🏫 **学校信息** - 学校配置、验证码要求
- 🔐 **用户认证** - 登录、验证码处理
- 👤 **学生信息** - 个人信息、学籍数据
- 📊 **成绩查询** - 成绩单、详细成绩
- 📅 **课程安排** - 课表、考试安排
- 📢 **通知公告** - 系统通知、学校公告
- 🎓 **学业管理** - 选课、学业进度

---

## 📚 接口详细说明

### 🏥 1. 系统接口

#### GET `/api/health`
**功能**: 检查服务是否正常运行

**请求参数**: 无

**响应示例**:
```json
{
  "status": "ok",
  "message": "ZFJW Backend API is running",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

---

### 🏫 2. 学校信息接口

#### GET `/api/schools`
**功能**: 获取所有支持的学校列表

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
**功能**: 获取指定学校的配置信息

**路径参数**:
- `school_name`: 学校名称 (如: 九江学院)

**支持的学校名称**:
- `九江学院`
- `南昌职业大学`

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
**功能**: 检查指定学校是否需要验证码

**路径参数**:
- `school_name`: 学校名称

**使用场景**: 登录前检查是否需要获取验证码

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

### 🔐 3. 用户认证接口

#### POST `/api/login`
**功能**: 用户登录接口（自动处理验证码）

**请求参数**:
```json
{
  "sid": "学号",
  "password": "密码", 
  "school_name": "九江学院"
}
```

**参数说明**:
- `sid`: 学生学号（必填）
- `password`: 登录密码（必填）
- `school_name`: 学校名称（必填，支持"九江学院"、"南昌职业大学"）
- `base_url`: 学校教务系统地址（可选，与school_name二选一）

**响应示例**:
```json
{
  "code": 1000,
  "msg": "登录成功",
  "data": {
    "cookies": "登录凭证",
    "user_info": {
      "name": "学生姓名",
      "student_id": "学号"
    }
  }
}
```

**特殊情况**:
- 如果学校需要验证码，将返回验证码图片，需要调用带验证码的登录接口

#### POST `/api/login_with_kaptcha`
**功能**: 带验证码的登录接口

**请求参数**:
```json
{
  "sid": "学号",
  "password": "密码",
  "captcha": "验证码",
  "cookies": "获取验证码时的会话凭证",
  "school_name": "九江学院"
}
```

**参数说明**:
- `sid`: 学生学号（必填）
- `password`: 登录密码（必填）
- `captcha`: 验证码内容（必填）
- `cookies`: 获取验证码时返回的会话凭证（必填）
- `school_name`: 学校名称（必填）

**使用流程**:
1. 先调用 `/api/get_captcha` 获取验证码图片和cookies
2. 用户输入验证码后调用此接口完成登录

#### POST `/api/get_captcha`
**功能**: 获取验证码图片

**请求参数**:
```json
{
  "school_name": "九江学院"
}
```

**参数说明**:
- `school_name`: 学校名称（必填）
- `base_url`: 学校教务系统地址（可选，与school_name二选一）

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取验证码成功",
  "data": {
    "captcha_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "cookies": "JSESSIONID=ABC123; Path=/"
  }
}
```

**注意事项**:
- 验证码图片为base64编码格式
- 返回的cookies需要在登录时一并提交
- 验证码有时效性，建议及时使用

---

### 👤 4. 学生信息接口

#### POST `/api/info`
**功能**: 获取学生个人基本信息

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**参数说明**:
- `cookies`: 登录成功后获得的会话凭证（必填）
- `school_name`: 学校名称（必填）
- `base_url`: 学校教务系统地址（可选，与school_name二选一）

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取个人信息成功",
  "data": {
    "student_id": "202001001",
    "name": "张三",
    "college": "信息科学与技术学院",
    "major": "计算机科学与技术",
    "class": "计算机科学与技术2020级1班",
    "grade": "2020级",
    "status": "在读"
  }
}
```

---

### 📊 5. 成绩查询接口

#### POST `/api/grade`
**功能**: 查询学生成绩

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
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `year`: 学年（必填，格式："2024"）
- `term`: 学期（必填，"1"表示第一学期，"2"表示第二学期）
- `base_url`: 学校教务系统地址（可选）

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取成绩成功",
  "data": {
    "courses": [
      {
        "course_name": "高等数学",
        "course_code": "MATH001", 
        "credit": "4",
        "score": "85",
        "grade_point": "3.5"
      }
    ],
    "total_credits": "20",
    "average_score": "82.5",
    "gpa": "3.2"
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

### 📝 6. 考试安排接口

#### POST `/api/exam`
**功能**: 获取考试安排信息

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "year": "2023-2024",
  "term": "1"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `year`: 学年（必填，格式："2023-2024"）
- `term`: 学期（必填，"1"或"2"）
- `base_url`: 学校教务系统地址（可选）

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

### 📅 7. 课程表接口

#### POST `/api/schedule`
**功能**: 获取学生课程表

**请求参数**:
```json
{
  "cookies": "登录凭证", 
  "school_name": "九江学院",
  "year": "2023-2024",
  "term": "1"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `year`: 学年（必填，格式："2023-2024"）
- `term`: 学期（必填，"1"或"2"）
- `week`: 周次（可选，不填则返回整学期课表）
- `base_url`: 学校教务系统地址（可选）

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

### 📢 8. 通知公告接口

#### POST `/api/notifications`
**功能**: 获取学校通知公告

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "page": 1,
  "limit": 10
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `page`: 页码（可选，默认为1）
- `limit`: 每页数量（可选，默认为10，最大50）
- `base_url`: 学校教务系统地址（可选）

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

### 🎓 9. 学业情况接口

#### POST `/api/academia`
**功能**: 获取学生学业完成情况

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `base_url`: 学校教务系统地址（可选）

**功能特点**:
- 显示已修学分和总学分要求
- 各类课程完成情况统计
- 毕业要求达成度分析

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

### 📚 10. 选课相关接口

#### POST `/api/get_elective_courses`
**功能**: 获取可选课程列表

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "course_type": "all",
  "page": 1,
  "limit": 20
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `course_type`: 课程类型（可选，"all"、"required"、"elective"、"public"）
- `page`: 页码（可选，默认为1）
- `limit`: 每页数量（可选，默认为20）
- `base_url`: 学校教务系统地址（可选）

#### POST `/api/selected_courses`
**功能**: 查询已选课程

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `base_url`: 学校教务系统地址（可选）

#### POST `/api/block_courses`
**功能**: 获取课程分块信息

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `base_url`: 学校教务系统地址（可选）

#### POST `/api/course_classes`
**功能**: 获取课程班级列表

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "course_id": "课程ID"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `course_id`: 课程ID（必填）
- `base_url`: 学校教务系统地址（可选）

#### POST `/api/select_course`
**功能**: 执行选课操作

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "course_id": "课程ID",
  "class_id": "班级ID"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `course_id`: 课程ID（必填）
- `class_id`: 班级ID（必填）
- `base_url`: 学校教务系统地址（可选）

**注意事项**:
- 选课需要在规定时间内进行
- 部分课程可能有先修课程要求
- 选课成功后建议查询课表确认

#### POST `/api/drop_course`
**功能**: 执行退课操作

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "course_id": "课程ID",
  "class_id": "班级ID"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `course_id`: 课程ID（必填）
- `class_id`: 班级ID（必填）
- `base_url`: 学校教务系统地址（可选）

**注意事项**:
- 退课需要在规定时间内进行
- 部分必修课程可能无法退课
- 退课后请及时调整学习计划

---

### 🏫 11. 教室查询接口

#### POST `/api/get_empty_classrooms`
**功能**: 查询空闲教室

**请求参数**:
```json
{
  "cookies": "登录凭证",
  "school_name": "九江学院",
  "date": "2024-01-01",
  "time_slot": "1-2",
  "building": "教学楼A"
}
```

**参数说明**:
- `cookies`: 登录凭证（必填）
- `school_name`: 学校名称（必填）
- `date`: 查询日期（必填，格式："YYYY-MM-DD"）
- `time_slot`: 时间段（必填，如"1-2"表示第1-2节课）
- `building`: 教学楼（可选，不填则查询所有教学楼）
- `capacity`: 最小容量（可选，筛选指定容量以上的教室）
- `base_url`: 学校教务系统地址（可选）

---

## 📝 通用响应格式

### 成功响应
```json
{
  "code": 1000,
  "msg": "操作成功",
  "data": {
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
  }
}
```

### 错误响应
```json
{
  "code": 400,
  "msg": "参数错误",
  "error": {
    "type": "ValidationError",
    "details": "具体错误信息",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### 状态码说明
- `1000`: 操作成功
- `1001`: 部分成功（批量操作时）
- `400`: 参数错误
- `401`: 认证失败/登录过期
- `403`: 权限不足
- `404`: 资源不存在
- `429`: 请求过于频繁
- `500`: 服务器内部错误
- `503`: 教务系统不可用
- `999`: 未知错误

### 分页响应格式
```json
{
  "code": 1000,
  "msg": "获取数据成功",
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

---

## 🚀 快速开始

### 1. 检查服务状态
```bash
curl -X GET "http://localhost:5000/api/health"
```

### 2. 获取支持的学校列表
```bash
curl -X GET "http://localhost:5000/api/schools"
```

### 3. 检查学校是否需要验证码
```bash
curl -X GET "http://localhost:5000/api/school/九江学院/captcha-required"
```

### 4. 用户登录（无验证码）
```bash
curl -X POST "http://localhost:5000/api/login" \
  -H "Content-Type: application/json" \
  -d '{
    "sid": "你的学号",
    "password": "你的密码",
    "school_name": "九江学院"
  }'
```

### 5. 用户登录（需要验证码）
```bash
# 先获取验证码
curl -X POST "http://localhost:5000/api/get_captcha" \
  -H "Content-Type: application/json" \
  -d '{"school_name": "九江学院"}'

# 然后使用验证码登录
curl -X POST "http://localhost:5000/api/login_with_kaptcha" \
  -H "Content-Type: application/json" \
  -d '{
    "sid": "你的学号",
    "password": "你的密码",
    "captcha": "验证码",
    "cookies": "获取验证码时返回的cookies",
    "school_name": "九江学院"
  }'
```

### 6. 获取个人信息
```bash
curl -X POST "http://localhost:5000/api/info" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "登录返回的cookies",
    "school_name": "九江学院"
  }'
```

### 7. 查询成绩
```bash
curl -X POST "http://localhost:5000/api/grade" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": "登录返回的cookies",
    "school_name": "九江学院",
    "year": "2024",
    "term": "1"
  }'
```

---

## ⚠️ 注意事项

### 🔐 认证相关
1. **登录凭证**: 所有需要认证的接口都需要传入登录成功后返回的 `cookies`
2. **会话过期**: 登录凭证有时效性，过期后需要重新登录
3. **验证码**: 部分学校登录需要验证码，验证码也有时效性，建议及时使用
4. **多设备登录**: 同一账号在多设备登录可能导致会话冲突

### 🏫 学校支持
1. **支持列表**: 目前支持的学校列表可通过 `/api/schools` 接口获取
2. **配置差异**: 不同学校的教务系统可能存在功能差异
3. **系统维护**: 学校教务系统维护期间接口可能不可用

### 📡 接口使用
1. **数据格式**: 所有接口均使用 JSON 格式进行数据交换
2. **字符编码**: 请使用 UTF-8 编码
3. **请求头**: 建议设置 `Content-Type: application/json`
4. **超时设置**: 建议设置合理的请求超时时间（30-60秒）

### 🚦 限制说明
1. **请求频率**: 为避免对教务系统造成压力，请合理控制请求频率
2. **并发限制**: 避免同时发起大量请求
3. **数据缓存**: 建议对不常变化的数据进行本地缓存
4. **错误重试**: 遇到网络错误时可适当重试，但需要设置重试间隔

### 🛠️ 开发建议
1. **错误处理**: 请根据返回的状态码进行相应的错误处理
2. **日志记录**: 建议记录关键操作的日志便于调试
3. **用户体验**: 对于耗时操作建议显示加载状态
4. **数据验证**: 在发送请求前验证必要参数的完整性

### 📞 技术支持
- **GitHub Issues**: [提交问题](https://github.com/drfccv/ZFJW-backend/issues)
- **GitHub Discussions**: [技术讨论](https://github.com/drfccv/ZFJW-backend/discussions)
- **邮箱联系**: drfccv@gmail.com
- **QQ群**: 123456789

---

## 🔧 开发说明

- **框架**: Flask + Python
- **跨域**: 已配置CORS支持
- **SSL**: 已禁用SSL警告处理
- **配置**: 支持多学校配置管理
- **日志**: 包含详细的错误日志输出
