from excel_agent.core.logging import app_logger
from excel_agent.pipelines.context import PipelineContext
from excel_agent.pipelines.steps.parse_command_step import PipelineStep
from excel_agent.strategies.search_strategy import KeywordAndFuzzySearchStrategy


class ExecuteSearchStep(PipelineStep):
    """
    Bước 2: Nếu có ý định tìm kiếm, thực hiện truy vấn trên Mock Enterprise Database.
    """

    def __init__(self, db_service):
        self.db_service = db_service
        self.search_strategy = KeywordAndFuzzySearchStrategy()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if context.command_name == "search" and context.command_args:
            query = context.command_args
            # Loại bỏ các từ thừa như "tìm sản phẩm", "search" nếu từ câu nói tự nhiên
            clean_query = query.replace("tìm sản phẩm", "").replace("tìm", "").replace("search", "").strip()
            if not clean_query:
                clean_query = query

            app_logger.info(f"Thực thi tìm kiếm Mock DB với query: '{clean_query}'")
            all_products = self.db_service.get_all_products()
            results = self.search_strategy.search(all_products, clean_query, limit=5)
            context.search_items = results

        return context
