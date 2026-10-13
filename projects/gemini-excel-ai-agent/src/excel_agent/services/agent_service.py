from excel_agent.builders.prompt_builder import PromptBuilder
from excel_agent.core.decorators import measure_execution_time
from excel_agent.core.logging import app_logger
from excel_agent.pipelines.context import PipelineContext
from excel_agent.pipelines.runner import PipelineRunner
from excel_agent.pipelines.steps.execute_search_step import ExecuteSearchStep
from excel_agent.pipelines.steps.format_response_step import FormatResponseStep
from excel_agent.pipelines.steps.parse_command_step import ParseCommandStep
from excel_agent.schemas.agent import (
    ChatRequest,
    ChatResponse,
    SlashCommandRequest,
    SlashCommandResponse,
)
from excel_agent.schemas.search import SearchRequest
from excel_agent.services.db_service import MockDatabaseService
from excel_agent.services.excel_service import ExcelService
from excel_agent.strategies.llm_strategy import AzureOpenAILLMStrategy


class AgentService:
    """
    Dịch vụ điều phối AI Agent (Agno AgentOS / Azure OpenAI gpt-5-mini).
    Chịu trách nhiệm xử lý ReAct Loop, Slash Commands và luôn trả về Pydantic v2 models.
    """

    def __init__(
        self,
        db_service: MockDatabaseService,
        excel_service: ExcelService,
        prompt_builder: PromptBuilder | None = None,
    ):
        self.db_service = db_service
        self.excel_service = excel_service
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_strategy = AzureOpenAILLMStrategy()

        # Cấu hình Pipeline xử lý yêu cầu
        self.pipeline = PipelineRunner(
            [
                ParseCommandStep(),
                ExecuteSearchStep(self.db_service),
                FormatResponseStep(),
            ]
        )

    @measure_execution_time(action_name="Xử lý tin nhắn Agent")
    async def process_chat_message(self, request: ChatRequest) -> ChatResponse:
        """
        Xử lý tin nhắn hội thoại hoặc yêu cầu thao tác từ Excel Taskpane.
        """
        app_logger.bind(session_id=request.session_id).info(
            f"Nhận tin nhắn từ sheet '{request.active_sheet_name}': {request.message}"
        )

        # 1. Khởi tạo Pipeline Context
        context = PipelineContext(
            session_id=request.session_id,
            raw_input=request.message,
            active_sheet_name=request.active_sheet_name,
            table_headers=request.table_headers,
            row_count=request.row_count,
        )

        # 2. Chạy Pipeline (Parse command, Search DB, Format action)
        updated_ctx = await self.pipeline.run(context)

        # 3. Nếu là hội thoại thông thường (không phải lệnh search ra kết quả trực tiếp),
        # gọi LLM để sinh lời phản hồi phong phú
        if not updated_ctx.search_items and not updated_ctx.is_slash_command:
            prompt_vars = {
                "active_sheet_name": request.active_sheet_name,
                "table_headers": ", ".join(request.table_headers)
                if request.table_headers
                else "Mã hàng, Tên sản phẩm, Đơn giá",
                "row_count": request.row_count,
                "user_query": request.message,
            }
            assembled = self.prompt_builder.load_and_assemble("excel_agent.yml", prompt_vars)
            llm_result = await self.llm_strategy.generate_response(
                prompt=assembled.user_prompt,
                system_prompt=assembled.full_instruction,
            )
            updated_ctx.final_reply_text = llm_result.content

        # 4. Trả về Pydantic v2 ChatResponse
        return ChatResponse(
            reply_text=updated_ctx.final_reply_text,
            session_id=request.session_id,
            suggested_action=updated_ctx.suggested_action,
            preview_diff=updated_ctx.preview_diff,
            products_found=updated_ctx.search_items,
        )

    @measure_execution_time(action_name="Xử lý Slash Command /search")
    async def process_slash_command(self, request: SlashCommandRequest) -> SlashCommandResponse:
        """
        Xử lý riêng cho lệnh tắt Slash Command (ví dụ: '/search Áo thun').
        """
        cmd_text = request.command_text.strip()
        if not cmd_text.startswith("/"):
            cmd_text = f"/{cmd_text}"

        parts = cmd_text[1:].split(maxsplit=1)
        command_name = parts[0].lower()
        query_param = parts[1].strip() if len(parts) > 1 else ""

        if command_name == "search":
            search_req = SearchRequest(query=query_param, limit=5)
            search_res = self.db_service.search_products(search_req)

            reply_msg = (
                f"Đã thực hiện `/search` cho từ khóa **'{query_param}'**. "
                f"Tìm thấy **{search_res.total_found}** sản phẩm phù hợp trong Mock Database."
            )

            return SlashCommandResponse(
                command_type="search",
                raw_query=query_param,
                reply_text=reply_msg,
                items=search_res.items,
            )

        elif command_name == "help":
            help_msg = (
                "**Lệnh Slash Command khả dụng:**\n"
                "- `/search <tên/mã>`: Tra cứu cơ sở dữ liệu doanh nghiệp\n"
                "- `/help`: Xem trợ giúp lệnh"
            )
            return SlashCommandResponse(
                command_type="help",
                raw_query=query_param,
                reply_text=help_msg,
                items=[],
            )

        else:
            return SlashCommandResponse(
                command_type="unknown",
                raw_query=query_param,
                reply_text=f"Lệnh `/{command_name}` không tồn tại. Gõ `/help` để xem danh sách lệnh.",
                items=[],
            )
