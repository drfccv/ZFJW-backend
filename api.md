# 📖 ZFJW Backend API 接口文档

🎯 **正方教务系统后端API**，基于Flask构建，支持多所高校教务系统数据获取。

## 📋 项目概览

- **服务地址**: `http://localhost:5000` (开发环境)
- **生产地址**: 根据部署环境配置
- **支持学校**: 九江学院、南昌职业大学、南京工业大学、西安邮电大学、浙江农林大学暨阳学院、广东工程职业技术学院（共6所，持续扩展中）
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
- 🏢 **空教室查询** - 校区列表、楼栋列表、空教室查询

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
    "count": 6,
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
      },
      {
        "school_name": "南京工业大学",
        "school_code": "njtech",
        "description": "南京工业大学教务系统",
        "requires_captcha": false
      },
      {
        "school_name": "西安邮电大学",
        "school_code": "xupt",
        "description": "西安邮电大学教务系统",
        "requires_captcha": true
      },
      {
        "school_name": "浙江农林大学暨阳学院",
        "school_code": "zafu",
        "description": "浙江农林大学暨阳学院教务系统",
        "requires_captcha": true
      },
      {
        "school_name": "广东工程职业技术学院",
        "school_code": "gpc",
        "description": "广东工程职业技术学院教务系统",
        "requires_captcha": true
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
- `南京工业大学`
- `西安邮电大学`
- `浙江农林大学暨阳学院`
- `广东工程职业技术学院`

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
- `school_name`: 学校名称（必填，支持"九江学院"、"南昌职业大学"、"南京工业大学"、"西安邮电大学"、"浙江农林大学暨阳学院"、"广东工程职业技术学院"）
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

## 🏢 10. 空教室查询接口

### POST `/api/campus_list`
**功能**: 获取学校所有校区列表

**请求参数**:
```json
{
  "cookies": "登录返回的cookies对象",
  "school_name": "九江学院",
  "year": "2025",  // 学年，如2024表示2024-2025学年
  "term": "2"       // 学期，1=第一学期，2=第二学期
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取校区列表成功",
  "data": {
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
      },
      {
        "campus_id": "3",
        "campus_name": "紫薇园",
        "is_default": false
      }
    ],
    "year": "2025",
    "term": "2"
  }
}
```

**字段说明**:
- `campus_id`: 校区唯一标识（用于后续查询）
- `campus_name`: 校区名称
- `is_default`: 是否为默认校区

**使用场景**: 在查询空教室前，先获取校区列表供用户选择

---

### POST `/api/building_list`
**功能**: 获取指定校区的楼栋列表和时间段列表

**请求参数**:
```json
{
  "cookies": "登录返回的cookies对象",
  "school_name": "九江学院",
  "year": "2025",
  "term": "2",
  "campus_id": "1"  // 从campus_list接口获取的校区ID
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "获取楼栋列表成功",
  "data": {
    "buildings": [
      {
        "building_id": "01",
        "building_name": "逸夫楼"
      },
      {
        "building_id": "02",
        "building_name": "立信楼"
      },
      {
        "building_id": "03",
        "building_name": "竞知楼"
      }
    ],
    "time_slots": [
      {
        "slot_id": "1",
        "slot_name": "第1-2节"
      },
      {
        "slot_id": "2",
        "slot_name": "第3-4节"
      },
      {
        "slot_id": "3",
        "slot_name": "第5-6节"
      },
      {
        "slot_id": "4",
        "slot_name": "第7-8节"
      },
      {
        "slot_id": "5",
        "slot_name": "第9-10节"
      }
    ],
    "campus_id": "1",
    "year": "2025",
    "term": "2"
  }
}
```

**字段说明**:
- `building_id`: 楼栋唯一标识（用于筛选）
- `building_name`: 楼栋名称
- `slot_id`: 时间段标识（查询时以数组形式传入）
- `slot_name`: 时间段名称（如"第1-2节"）

**使用场景**: 获取楼栋和时间段信息，供用户筛选空教室

---

### POST `/api/classroom`
**功能**: 查询空教室列表

**请求参数**:
```json
{
  "cookies": "登录返回的cookies对象",
  "school_name": "九江学院",
  "year": "2025",
  "term": "2",
  "weeks": [1, 2],           // 周次数组，如[1,2]表示第1-2周
  "day_of_weeks": 1,         // 星期几，1=周一，2=周二...7=周日
  "time_slots": [1, 2],      // 时间段数组，对应building_list返回的slot_id
  "campus_id": "1",          // 可选，校区ID（不传则查询所有校区）
  "building": "01"           // 可选，楼栋ID（不传则查询所有楼栋）
}
```

**响应示例**:
```json
{
  "code": 1000,
  "msg": "查询空教室成功",
  "data": {
    "classrooms": [
      {
        "code": "101001102",
        "name": "西102",
        "campus": "主校区",
        "type": "多媒体",
        "capacity": 114,
        "exam_capacity": 57,
        "building_code": "12",
        "floor": "1",
        "borrow_type": "教学场地",
        "remark": null,
        "manager": "张老师",
        "department": "艺术学院",
        "class_name": null,
        "sub_type": "智慧教室",
        "area": "120",
        "custody_dept": "教务处"
      },
      {
        "code": "101001103",
        "name": "西103",
        "campus": "主校区",
        "type": "多媒体",
        "capacity": 114,
        "exam_capacity": 57,
        "building_code": "12",
        "floor": "1",
        "borrow_type": null,
        "remark": null,
        "manager": null,
        "department": "艺术学院",
        "class_name": null,
        "sub_type": null,
        "area": null,
        "custody_dept": null
      }
    ],
    "total": 559,
    "query_info": {
      "year": "2025",
      "term": "2",
      "weeks": [1, 2],
      "day_of_weeks": 1,
      "time_slots": [1, 2],
      "campus_id": "1",
      "building": "01"
    }
  }
}
```

**字段说明**:
- `code`: 场地编号（教务系统唯一标识）
- `name`: 教室名称
- `campus`: 所属校区
- `type`: 场地类别（多媒体、普通教室、实验室等）
- `capacity`: 座位数
- `exam_capacity`: 考试座位数
- `building_code`: 楼号编码
- `floor`: 楼层号
- `borrow_type`: 场地借用类型
- `remark`: 场地备注信息
- `manager`: 场地管理员
- `department`: 使用部门
- `class_name`: 使用班级
- `sub_type`: 场地二级类别
- `area`: 建筑面积（平方米）
- `custody_dept`: 托管部门
- `total`: 符合条件的教室总数

**使用场景**: 
1. 学生查找自习教室
2. 教师预约空教室
3. 社团活动场地查询
4. 考试教室安排参考

**查询示例**:

1. **查询第1周周一第1-2节所有空教室**:
```json
{
  "year": "2025",
  "term": "2",
  "weeks": [1],
  "day_of_weeks": 1,
  "time_slots": [1]
}
```

2. **查询主校区立信楼第3周周三第5-6节空教室**:
```json
{
  "year": "2025",
  "term": "2",
  "weeks": [3],
  "day_of_weeks": 3,
  "time_slots": [3],
  "campus_id": "1",
  "building": "02"
}
```

3. **查询第1-8周周末所有时段空教室**:
```json
{
  "year": "2025",
  "term": "2",
  "weeks": [1, 2, 3, 4, 5, 6, 7, 8],
  "day_of_weeks": 6,  // 或 7 表示周日
  "time_slots": [1, 2, 3, 4, 5]
}
```

**错误处理**:
```json
{
  "code": 2004,
  "msg": "缺少必需参数: weeks",
  "data": null
}
```

**注意事项**:
1. 时间参数使用位掩码算法编码，支持多周、多时段同时查询
2. 查询结果已排除已被占用的教室
3. 某些字段可能为 `null`，表示该教室无此项信息
4. 建议先调用 `campus_list` 和 `building_list` 获取可用选项
5. 大范围查询（如整学期所有教室）可能耗时较长，建议合理设置查询条件

---

## 🔧 开发说明

- **框架**: Flask + Python
- **跨域**: 已配置CORS支持
- **SSL**: 已禁用SSL警告处理
- **配置**: 支持多学校配置管理
- **日志**: 包含详细的错误日志输出
