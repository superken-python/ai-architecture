from excel_agent.core.logging import app_logger
from excel_agent.pipelines.context import PipelineContext
from excel_agent.pipelines.steps.parse_command_step import PipelineStep


class PipelineRunner:
    """
    Trình điều phối chuỗi bước (Pipeline Pattern) để xử lý logic đa giai đoạn.
    """

    def __init__(self, steps: list[PipelineStep]):
        self.steps = steps

    async def run(self, context: PipelineContext) -> PipelineContext:
        app_logger.info(f"Bắt đầu chạy Pipeline với {len(self.steps)} bước...")
        current_ctx = context

        for idx, step in enumerate(self.steps, start=1):
            step_name = step.__class__.__name__
            app_logger.debug(f"[Bước {idx}/{len(self.steps)}] Thực thi: {step_name}")
            current_ctx = await step.execute(current_ctx)

        app_logger.info("Pipeline đã hoàn tất thành công.")
        return current_ctx
