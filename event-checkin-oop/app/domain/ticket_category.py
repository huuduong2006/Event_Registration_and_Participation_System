"""TicketCategory (Hạng vé)."""
from dataclasses import dataclass

from ..errors import ValidationError
from ..ids import CATEGORY, new_id
from .validators import clean_int, clean_money, clean_name


@dataclass
class TicketCategory:
    ticket_type_id: str                  
    event_id: str                        
    type_name: str                      
    price: float                         # VND
    quantity_limit: int
    sold_count: int = 0                  # (dẫn xuất) số vé đã bán – repository nạp kèm

    @classmethod
    def create(cls, event_id: str, type_name, price, quantity_limit) -> "TicketCategory":
        return cls(new_id(CATEGORY), event_id,
                   clean_name(type_name, "Tên loại vé", 1, 40),
                   clean_money(price), clean_int(quantity_limit, "Số lượng vé", 1))

    def update_pricing(self, new_price) -> None:
        """Điều chỉnh giá vé."""
        self.price = clean_money(new_price)

    def update_details(self, type_name, price, quantity_limit) -> None:
        qty = clean_int(quantity_limit, "Số lượng vé", 1)
        if qty < self.sold_count:
            raise ValidationError(f"Đã bán {self.sold_count} vé, số lượng không thể nhỏ hơn", "CONFLICT")
        self.type_name = clean_name(type_name, "Tên loại vé", 1, 40)
        self.update_pricing(price)
        self.quantity_limit = qty

    @property
    def remaining(self) -> int:
        return max(0, self.quantity_limit - self.sold_count)

    def check_availability(self) -> bool:
        """Hạng vé còn mở bán hay không."""
        return self.sold_count < self.quantity_limit
