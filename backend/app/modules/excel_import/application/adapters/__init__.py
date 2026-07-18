from app.modules.excel_import.application.adapters.xls_adapter import XlsWorkbookAdapter
from app.modules.excel_import.application.adapters.xlsx_adapter import XlsxWorkbookAdapter
from app.modules.excel_import.domain.source_artifact import (
    SOURCE_ACCEPTED_EXTENSIONS,
    XLS_OLE_SIGNATURE,
    XLSX_ZIP_SIGNATURE,
)
from app.modules.excel_import.domain.workbook_adapter import AdapterError, WorkbookFormat

__all__ = [
    "XlsWorkbookAdapter",
    "XlsxWorkbookAdapter",
    "detect_format_and_adapter",
    "AdapterError",
]


def detect_format_and_adapter(path: str, filename: str, limits=None):
    """Return (format, adapter) after extension+signature checks."""
    ext = ""
    if "." in filename:
        ext = filename[filename.rfind(".") :].lower()
    if ext not in SOURCE_ACCEPTED_EXTENSIONS:
        raise AdapterError(
            400,
            "unsupported_extension",
            "Định dạng tệp không được hỗ trợ. Chỉ chấp nhận tệp .xls hoặc .xlsx.",
        )
    with open(path, "rb") as f:
        head = f.read(8)
    if ext == ".xlsx":
        if not head.startswith(XLSX_ZIP_SIGNATURE):
            raise AdapterError(
                400,
                "signature_mismatch",
                "Phần mở rộng .xlsx không khớp chữ ký nội dung tệp.",
            )
        return WorkbookFormat.XLSX, XlsxWorkbookAdapter(limits=limits)
    if not head.startswith(XLS_OLE_SIGNATURE):
        raise AdapterError(
            400,
            "signature_mismatch",
            "Phần mở rộng .xls không khớp chữ ký nội dung tệp.",
        )
    return WorkbookFormat.XLS, XlsWorkbookAdapter(limits=limits)
