from dataclasses import dataclass

@dataclass(frozen=True)
class ExcelImportLimits:
    max_upload_bytes: int = 10 * 1024 * 1024
    max_request_bytes: int = 12 * 1024 * 1024
    read_chunk_size: int = 64 * 1024
    max_zip_entries: int = 2048
    max_uncompressed_zip_bytes: int = 100 * 1024 * 1024
    max_header_search_rows: int = 100
    max_data_rows: int = 5000
    max_physical_rows: int = 5100
    max_columns: int = 100
    max_cell_chars: int = 10000
    max_row_chars: int = 100000

    @property
    def limit_version(self) -> str:
        return f"v1-rows{self.max_data_rows}-cols{self.max_columns}"

DEFAULT_LIMITS = ExcelImportLimits()

ACCEPTED_EXTENSIONS = frozenset({".xlsx"})

REQUIRED_ZIP_PARTS = frozenset({
    "[Content_Types].xml",
    "xl/workbook.xml",
})

FORBIDDEN_ZIP_PARTS = frozenset({
    "xl/vbaProject.bin",
})

EXTERNAL_LINK_PATHS = frozenset({
    "xl/externalLinks/",
})

COLUMN_ALIASES = {
    "proposed_asset_name": ["asset_name", "ten_tai_san", "tên_tài_sản", "ten_tai_san", "tên_tài_sản", "name"],
    "proposed_description": ["description", "mo_ta", "mô_tả", "specification", "thong_so", "thông_số"],
    "proposed_quantity": ["quantity", "so_luong", "số_lượng", "qty"],
    "proposed_unit": ["unit", "don_vi", "đơn_vị"],
    "proposed_raw_price": ["raw_price", "gia_goc", "giá_gốc", "cost", "price"],
    "proposed_currency": ["currency", "tien_te", "tiền_tệ"],
    "proposed_appraised_unit_price": ["appraised_unit_price", "gia_tham_dinh", "giá_thẩm_định", "appraised_price"],
}
