"""
push_store.py — SQLite 数据管理器
管理绑定、订阅和成绩快照等数据
"""
from typing import Optional
import sqlite3
import os
import json
import time
import traceback


class PushStore:
    """推送相关数据的 SQLite 存储管理器"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化存储管理器

        Args:
            db_path: 数据库文件路径，默认使用本文件所在目录下的 data/push_data.db
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "data", "push_data.db")
        self.db_path = db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def init_db(self):
        """建表（如果不存在）"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bindings (
                    openid TEXT PRIMARY KEY,
                    school_name TEXT NOT NULL,
                    sid TEXT NOT NULL,
                    cookies TEXT,
                    bind_time INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    openid TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'accept',
                    subscribe_time INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grade_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openid TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    term INTEGER NOT NULL,
                    data_hash TEXT,
                    grades TEXT,
                    update_time INTEGER NOT NULL,
                    UNIQUE(openid, year, term)
                )
            """)

            conn.commit()
            conn.close()
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] init_db 出错: {e}")

    def save_binding(self, openid: str, school_name: str, sid: str,
                     cookies: Optional[dict] = None):
        """
        保存或更新绑定

        Args:
            openid: 微信 openid
            school_name: 学校名称
            sid: 学号
            cookies: 教务系统 cookies（dict，自动 JSON 序列化存储）
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now = int(time.time())
            cookies_json = json.dumps(cookies, ensure_ascii=False) if cookies else None
            cursor.execute("""
                INSERT INTO bindings (openid, school_name, sid, cookies, bind_time)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(openid) DO UPDATE SET
                    school_name = excluded.school_name,
                    sid = excluded.sid,
                    cookies = COALESCE(excluded.cookies, bindings.cookies),
                    bind_time = excluded.bind_time
            """, (openid, school_name, sid, cookies_json, now))
            conn.commit()
            conn.close()
            print(f"[PushStore] 保存绑定成功: openid={openid}, school={school_name}, sid={sid}")
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] save_binding 出错: {e}")

    def get_binding(self, openid: str):
        """
        查询绑定

        Args:
            openid: 微信 openid

        Returns:
            dict 或 None（cookies 字段已反序列化为 dict）
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT openid, school_name, sid, cookies, bind_time FROM bindings WHERE openid = ?",
                (openid,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                result = dict(row)
                # 反序列化 cookies
                if result.get("cookies"):
                    try:
                        result["cookies"] = json.loads(result["cookies"])
                    except (json.JSONDecodeError, TypeError):
                        result["cookies"] = {}
                else:
                    result["cookies"] = {}
                return result
            return None
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] get_binding 出错: {e}")
            return None

    def delete_binding(self, openid: str):
        """
        删除绑定

        Args:
            openid: 微信 openid
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bindings WHERE openid = ?", (openid,))
            conn.commit()
            conn.close()
            print(f"[PushStore] 删除绑定成功: openid={openid}")
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] delete_binding 出错: {e}")

    def save_subscription(self, openid: str, template_id: str, status: str = "accept"):
        """
        保存或更新订阅

        Args:
            openid: 微信 openid
            template_id: 模板 ID
            status: 订阅状态，默认 'accept'
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now = int(time.time())
            cursor.execute("""
                INSERT INTO subscriptions (openid, template_id, status, subscribe_time)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(openid) DO UPDATE SET
                    template_id = excluded.template_id,
                    status = excluded.status,
                    subscribe_time = excluded.subscribe_time
            """, (openid, template_id, status, now))
            conn.commit()
            conn.close()
            print(f"[PushStore] 保存订阅成功: openid={openid}, template_id={template_id}, status={status}")
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] save_subscription 出错: {e}")

    def get_subscription(self, openid: str):
        """
        查询单个订阅

        Args:
            openid: 微信 openid

        Returns:
            dict 或 None
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT openid, template_id, status, subscribe_time FROM subscriptions WHERE openid = ?",
                (openid,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] get_subscription 出错: {e}")
            return None

    def get_all_active_subscriptions(self):
        """
        查询所有 status='accept' 的订阅

        Returns:
            list[dict]: 每条包含 openid, template_id
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT openid, template_id FROM subscriptions WHERE status = 'accept'"
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] get_all_active_subscriptions 出错: {e}")
            return []

    def delete_subscription(self, openid: str):
        """
        删除订阅

        Args:
            openid: 微信 openid
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE openid = ?", (openid,))
            conn.commit()
            conn.close()
            print(f"[PushStore] 删除订阅成功: openid={openid}")
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] delete_subscription 出错: {e}")

    def save_grade_snapshot(self, openid: str, year: int, term: int,
                            data_hash: str, grades: str):
        """
        保存成绩快照

        Args:
            openid: 微信 openid
            year: 学年
            term: 学期
            data_hash: 数据哈希值
            grades: JSON 序列化的成绩数据
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            now = int(time.time())
            cursor.execute("""
                INSERT INTO grade_snapshots (openid, year, term, data_hash, grades, update_time)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(openid, year, term) DO UPDATE SET
                    data_hash = excluded.data_hash,
                    grades = excluded.grades,
                    update_time = excluded.update_time
            """, (openid, year, term, data_hash, grades, now))
            conn.commit()
            conn.close()
            print(f"[PushStore] 保存成绩快照成功: openid={openid}, year={year}, term={term}")
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] save_grade_snapshot 出错: {e}")

    def get_grade_snapshot(self, openid: str, year: int, term: int):
        """
        查询成绩快照

        Args:
            openid: 微信 openid
            year: 学年
            term: 学期

        Returns:
            dict 或 None
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, openid, year, term, data_hash, grades, update_time
                   FROM grade_snapshots
                   WHERE openid = ? AND year = ? AND term = ?""",
                (openid, year, term)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] get_grade_snapshot 出错: {e}")
            return None

    def get_all_grade_snapshots_by_openid(self, openid: str):
        """
        查询某个用户所有学期的快照

        Args:
            openid: 微信 openid

        Returns:
            list[dict]
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, openid, year, term, data_hash, grades, update_time
                   FROM grade_snapshots
                   WHERE openid = ?
                   ORDER BY year DESC, term DESC""",
                (openid,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            traceback.print_exc()
            print(f"[PushStore] get_all_grade_snapshots_by_openid 出错: {e}")
            return []
