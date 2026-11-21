"""Lớp nền cho các đối tượng domain cần gọi tới dịch vụ.

Các lớp trong PDF có phương thức như Ticket.sendEmailWithTicket() hay Administrator.createEvent()
– chúng cần DB/email. Để domain không phụ thuộc trực tiếp vào hạ tầng, đối tượng được "gắn"
(bind) với container `Application` khi được nạp từ repository, và uỷ quyền cho service tương ứng.
Dữ liệu và quy tắc nghiệp vụ thuần tuý (kiểm tra, tính toán) vẫn nằm ngay trong lớp domain.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # chỉ để gợi ý kiểu, tránh import vòng
    from ..application import Application


class Bindable:
    _app: "Application | None" = None

    def bind(self, app: "Application"):
        self._app = app
        return self

    @property
    def app(self) -> "Application":
        if self._app is None:
            raise RuntimeError(f"{type(self).__name__} chưa được bind() với Application "
                               "(hãy nạp đối tượng qua repository/service).")
        return self._app
