"""Generate the small, fully synthetic G1.1K workbook fixture."""

from pathlib import Path

from openpyxl import Workbook


OUTPUT = Path(__file__).parent / "fixtures" / "g11k_synthetic_assets.xlsx"
ASSETS = (
    ("Máy tiện CNC mẫu A", "Máy giả lập, năm 2024", "cái", 2, 120_000_000),
    ("Máy phay CNC mẫu B", "Máy giả lập, năm 2023", "cái", 1, 180_000_000),
    ("Máy nén khí mẫu C", "Thiết bị giả lập 15 kW", "cái", 3, 25_000_000),
    ("Băng tải mẫu D", "Dây chuyền giả lập 6 m", "bộ", 1, 65_000_000),
    ("Robot hàn mẫu E", "Thiết bị giả lập 6 trục", "cái", 2, 210_000_000),
    ("Máy đo mẫu F", "Thiết bị giả lập độ chính xác cao", "cái", 4, 12_000_000),
    ("Tủ điện mẫu G", "Thiết bị giả lập 380 V", "bộ", 2, 18_000_000),
    ("Bơm công nghiệp mẫu H", "Thiết bị giả lập 20 m³/h", "cái", 3, 17_000_000),
    ("Máy phát điện mẫu I", "Thiết bị giả lập 100 kVA", "cái", 1, 145_000_000),
    ("Xe nâng mẫu J", "Thiết bị giả lập 2,5 tấn", "cái", 2, 95_000_000),
    ("Lò sấy mẫu K", "Thiết bị giả lập 80 °C", "bộ", 1, 72_000_000),
    ("Máy đóng gói mẫu L", "Thiết bị giả lập 40 kiện/phút", "cái", 1, 110_000_000),
)


def main() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Danh muc tai san"
    sheet.append(("STT", "Tên tài sản", "Đặc điểm", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền"))
    for index, (name, description, unit, quantity, unit_price) in enumerate(ASSETS, 1):
        sheet.append((index, name, description, unit, quantity, unit_price, quantity * unit_price))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
