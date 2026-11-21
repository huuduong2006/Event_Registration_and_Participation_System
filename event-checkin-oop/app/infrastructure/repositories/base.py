class Repository:
    """Lớp nền: giữ kết nối của UnitOfWork hiện tại và `app` để bind đối tượng domain khi nạp."""

    def __init__(self, conn, app=None):
        self.conn = conn
        self.app = app

    def _bind(self, obj):
        return obj.bind(self.app) if (obj is not None and self.app is not None and hasattr(obj, "bind")) else obj

    def _one(self, sql, args=()):
        return self.conn.execute(sql, args).fetchone()

    def _all(self, sql, args=()):
        return self.conn.execute(sql, args).fetchall()
