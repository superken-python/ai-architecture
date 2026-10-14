from excel_agent.pipelines.context import PipelineContext
from excel_agent.pipelines.steps.parse_command_step import PipelineStep
from excel_agent.schemas.excel import (
    ColumnValueDTO,
    InsertRowRequest,
    PreviewDiffCard,
    PreviewDiffItem,
)


class FormatResponseStep(PipelineStep):
    """
    Bước 3: Tổng hợp phản hồi, sinh thẻ xem trước Preview Diff Card nếu có sản phẩm cần chèn.
    """

    async def execute(self, context: PipelineContext) -> PipelineContext:
        target_row = context.row_count + 1 if context.row_count > 0 else 2

        # 1. Trường hợp có kết quả tìm kiếm sản phẩm
        if context.search_items:
            first_item = context.search_items[0]
            context.final_reply_text = (
                f"Đã tìm thấy **{len(context.search_items)}** mục trong cơ sở dữ liệu doanh nghiệp.\n"
                f"- Mã hàng: `{first_item.sku}`\n"
                f"- Tên: **{first_item.name}**\n"
                f"- Giá: **{first_item.unit_price:,.0f} đ** | Tồn kho: **{first_item.stock_quantity}**\n\n"
                f"Bạn có thể bấm **'Xác nhận chèn vào Excel'** ở thẻ Preview bên dưới để ghi dữ liệu."
            )

            # Tạo InsertRowRequest tương thích cấu trúc tiêu đề cột
            row_values = [
                ColumnValueDTO(column_name="Mã hàng", value=first_item.sku),
                ColumnValueDTO(column_name="Tên sản phẩm", value=first_item.name),
                ColumnValueDTO(column_name="Danh mục", value=first_item.category),
                ColumnValueDTO(column_name="Số lượng", value=1),
                ColumnValueDTO(column_name="Đơn giá", value=first_item.unit_price),
                ColumnValueDTO(
                    column_name="Thành tiền", value=first_item.unit_price, formula=f"=D{target_row}*E{target_row}"
                ),
            ]

            context.suggested_action = InsertRowRequest(
                sheet_name=context.active_sheet_name,
                target_row_index=target_row,
                row_values=row_values,
                highlight_inserted_row=True,
            )

            # Tạo Preview Diff Card
            context.preview_diff = PreviewDiffCard(
                action_type="INSERT_ROW",
                sheet_name=context.active_sheet_name,
                target_row=target_row,
                summary=f"Chèn dòng mới cho sản phẩm {first_item.name} ({first_item.sku})",
                diff_items=[
                    PreviewDiffItem(column_name=val.column_name, new_value=str(val.value), is_new_row=True)
                    for val in row_values
                ],
                can_apply=True,
            )

        elif context.is_slash_command and context.command_name == "help":
            context.final_reply_text = (
                "**DANH SÁCH LỆNH TẮT HỖ TRỢ:**\n"
                "- `/search <từ khóa>`: Tra cứu sản phẩm trong Mock Database (ví dụ: `/search Áo thun`)\n"
                "- `/insert <tên>`: Đề xuất chèn nhanh dòng mới vào Excel\n"
                "- `/help`: Xem hướng dẫn sử dụng\n"
                "- Hoặc bạn có thể gõ hội thoại tự nhiên: *'Tìm mã SP-002 và chèn vào bảng giúp tôi'*."
            )

        elif not context.final_reply_text:
            context.final_reply_text = (
                f"Đã nhận yêu cầu: '{context.raw_input}'. "
                f"Tôi đang sẵn sàng hỗ trợ thao tác trên worksheet **{context.active_sheet_name}**."
            )

        return context
