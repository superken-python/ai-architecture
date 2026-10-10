import os

from jinja2 import Environment, FileSystemLoader

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger


class PromptLoader:
    def __init__(self, prompts_dir: str):
        self.prompts_dir = prompts_dir
        if os.path.exists(prompts_dir):
            self.env = Environment(loader=FileSystemLoader(prompts_dir))
        else:
            self.env = None

    def render(self, template_path: str, **kwargs) -> str:
        if self.env:
            try:
                tmpl = self.env.get_template(template_path)
                return tmpl.render(**kwargs).strip()
            except Exception as e:
                logger.warning(f"Failed to render template {template_path}: {e}")
        # Default fallback
        src = kwargs.get("source_lang", "any")
        tgt = kwargs.get("target_lang", "any")
        txt = kwargs.get("text", "")
        return f"Translate from {src} to {tgt}: {txt}"


def get_prompt_loader() -> PromptLoader:
    p_path = os.path.abspath(settings.PROMPTS_DIR)
    if not os.path.exists(p_path):
        p_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../prompts"))
    return PromptLoader(p_path)
